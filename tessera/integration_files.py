"""Experimental filesystem transactions for explicitly reviewed setup plans.

Only synthetic fixtures validate this adapter. Each file replacement is atomic;
config + ownership are NOT a crash-atomic multi-file transaction. Cooperating
TESSERA writers use an exclusive lock. Client processes do not honor that lock,
so close the client before using this API. Raw rollback bytes stay in memory.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
import stat
import tempfile
from typing import Optional

from .integration_setup import (
    DocumentState, IntegrationError, SetupPlan, _read, apply_plan, ownership_path,
)


@dataclass(frozen=True)
class FileSnapshot:
    data: Optional[bytes] = field(repr=False)
    mode: Optional[int]


def _snapshot(path):
    data = _read(path)
    if data is None:
        return FileSnapshot(None, None)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise IntegrationError("only single-link regular configuration files are supported")
    return FileSnapshot(data, stat.S_IMODE(info.st_mode))


@dataclass(frozen=True)
class FilePlan:
    """Explicit paths bound to the exact snapshots already reviewed in memory."""

    plan: SetupPlan
    config_path: Path
    other_config_path: Path
    before_config: FileSnapshot = field(repr=False)
    before_owner: FileSnapshot = field(repr=False)
    other_config: FileSnapshot = field(repr=False)
    other_owner: FileSnapshot = field(repr=False)

    @property
    def owner_path(self):
        return ownership_path(self.config_path, self.plan.request.runtime, self.plan.request.scope)

    @property
    def other_owner_path(self):
        scope = "user" if self.plan.request.scope == "project" else "project"
        return ownership_path(self.other_config_path, self.plan.request.runtime, scope)


def bind_file_plan(plan, config_path, other_config_path):
    """Bind explicit caller-owned paths; never discover a user's real home here."""
    target, other = Path(config_path), Path(other_config_path)
    if not target.is_absolute() or not other.is_absolute():
        raise IntegrationError("file plans require absolute paths")
    target, other = Path(os.path.abspath(target)), Path(os.path.abspath(other))
    if target == other:
        raise IntegrationError("file plans require distinct absolute target and other-scope paths")
    owner = ownership_path(target, plan.request.runtime, plan.request.scope)
    other_scope = "user" if plan.request.scope == "project" else "project"
    other_owner = ownership_path(other, plan.request.runtime, other_scope)
    if len({target, other, owner, other_owner}) != 4:
        raise IntegrationError("configuration and ownership paths must not overlap")
    snapshots = [_snapshot(path) for path in (target, owner, other, other_owner)]
    if DocumentState(snapshots[0].data, snapshots[1].data) != plan.before:
        raise IntegrationError("stale file plan: target changed before binding")
    if not plan.request.remove and DocumentState(snapshots[2].data, snapshots[3].data) != plan.other_scope:
        raise IntegrationError("stale file plan: other scope changed before binding")
    return FilePlan(plan, target, other, *snapshots)


@dataclass(frozen=True)
class FileReceipt:
    file_plan: FilePlan
    after_config: FileSnapshot = field(repr=False)
    after_owner: FileSnapshot = field(repr=False)
    created_directories: tuple = ()
    extra_changes: tuple = field(default=(), repr=False)


class FileTransactionError(IntegrationError):
    """Caught failure, with explicit recovery result and no source contents."""

    def __init__(self, message, *, recovery_complete):
        super().__init__(message)
        self.recovery_complete = recovery_complete


def _expect(path, snapshot):
    if _snapshot(path) != snapshot:
        raise IntegrationError("stale file plan: bytes or permissions changed")


def _replace(path, expected, desired):
    """Per-file atomic replacement. Recheck immediately before replace/unlink."""
    _expect(path, expected)
    if expected == desired:
        return
    if desired.data is None:
        _expect(path, expected)
        path.unlink()
        return
    descriptor, temporary = tempfile.mkstemp(prefix=".tessera-setup-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.chmod(temporary, desired.mode)
            stream.write(desired.data)
            stream.flush()
            os.fsync(stream.fileno())
        _expect(path, expected)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _create_parents(parent):
    missing = []
    cursor = parent
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    # _read guards the complete path against existing symlink ancestors.
    _read(parent / ".tessera-path-check")
    created = []
    try:
        for directory in reversed(missing):
            directory.mkdir(mode=0o700)
            created.append(directory)
    except OSError:
        _remove_empty(created)
        raise
    return tuple(created)


def _remove_empty(directories):
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except OSError:
            # Never remove a directory after another process added data to it.
            pass


def _transaction(file_plan, changes, *, check_other):
    directories = _create_parents(file_plan.config_path.parent)
    lock = file_plan.owner_path.with_suffix(".lock")
    lock_fd = None
    completed = []
    try:
        try:
            lock_fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise IntegrationError("setup lock exists; inspect another writer or interrupted transaction") from exc
        for path, before, _after in changes:
            _expect(path, before)
        if check_other:
            _expect(file_plan.other_config_path, file_plan.other_config)
            _expect(file_plan.other_owner_path, file_plan.other_owner)
        for path, before, after in changes:
            _replace(path, before, after)
            completed.append((path, before, after))
    except (OSError, IntegrationError) as exc:
        recovered = True
        for path, before, after in reversed(completed):
            try:
                _replace(path, after, before)
            except (OSError, IntegrationError):
                recovered = False
        reason = str(exc) if isinstance(exc, IntegrationError) else "filesystem operation failed"
        result = ("no partial writes remain" if recovered else
                  "concurrent changes preserved; inspect partial state")
        message = f"filesystem transaction refused or failed: {reason}; {result}"
        raise FileTransactionError(message, recovery_complete=recovered) from exc
    finally:
        if lock_fd is not None:
            owned = os.fstat(lock_fd)
            os.close(lock_fd)
            try:
                current = lock.lstat()
                if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                    lock.unlink()
            except FileNotFoundError:
                pass
        if completed != list(changes):
            _remove_empty(directories)
    return directories


def _desired_snapshot(data, before):
    if data is None:
        return FileSnapshot(None, None)
    return FileSnapshot(data, before.mode if before.mode is not None else 0o600)


def apply_file_plan(file_plan, *, extra_changes=(), config_mode=None, owner_mode=None):
    """Explicit filesystem apply, also used by the hash-bound CLI.

    Callers must obtain consent for these exact runtime/access changes. This API
    does not install/start clients, change trust, or copy credentials to backups.
    """
    plan = file_plan.plan
    apply_plan(plan, plan.before, other_scope=plan.other_scope)
    config = _desired_snapshot(plan.after.config, file_plan.before_config)
    owner = _desired_snapshot(plan.after.ownership, file_plan.before_owner)
    if config.data is not None and config_mode is not None:
        config = FileSnapshot(config.data, config_mode)
    if owner.data is not None and owner_mode is not None:
        owner = FileSnapshot(owner.data, owner_mode)
    reserved = {file_plan.config_path, file_plan.owner_path,
                file_plan.other_config_path, file_plan.other_owner_path}
    for path, before, after in extra_changes:
        if path in reserved or path.parent != file_plan.config_path.parent:
            raise IntegrationError("extra receipt paths must be distinct siblings of the config")
        reserved.add(path)
        if not isinstance(before, FileSnapshot) or not isinstance(after, FileSnapshot):
            raise IntegrationError("extra receipt changes require file snapshots")
    if plan.operation == "noop" and not extra_changes:
        _expect(file_plan.config_path, file_plan.before_config)
        _expect(file_plan.owner_path, file_plan.before_owner)
        if not plan.request.remove:
            _expect(file_plan.other_config_path, file_plan.other_config)
            _expect(file_plan.other_owner_path, file_plan.other_owner)
        return FileReceipt(file_plan, config, owner)
    changes = [(file_plan.config_path, file_plan.before_config, config),
               (file_plan.owner_path, file_plan.before_owner, owner)]
    changes.extend(extra_changes)
    directories = _transaction(file_plan, changes, check_other=not plan.request.remove)
    return FileReceipt(file_plan, config, owner, directories, tuple(extra_changes))


def rollback_file_plan(receipt):
    """Restore exact bytes/modes only while the post-apply snapshot still matches."""
    file_plan = receipt.file_plan
    changes = [(file_plan.config_path, receipt.after_config, file_plan.before_config),
               (file_plan.owner_path, receipt.after_owner, file_plan.before_owner)]
    changes.extend((path, after, before) for path, before, after in receipt.extra_changes)
    _transaction(file_plan, changes, check_other=False)
    _remove_empty(receipt.created_directories)
