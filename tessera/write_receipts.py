"""Content-free, local single-write receipts. Canonical source stays authoritative."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stderr
from dataclasses import asdict, dataclass, replace
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import threading
from typing import Any, Dict, Optional

from .security import WriteAdmission, WriteResult, validate_memory_path
from .source_formats import split_source

RECEIPT_SCHEMA_VERSION = 1
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_OPERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_LOCKS: Dict[str, Any] = {}
_LOCKS_GUARD = threading.Lock()


@dataclass(frozen=True)
class WriteReceipt:
    operation_id: str
    memory_id: str
    persisted: bool = False
    source_revision: Optional[str] = None
    indexed: str = "pending"
    evidence_ledger: str = "pending"
    hooks: tuple = ()
    errors: tuple = ()
    source_state: str = "unwritten"
    schema_version: int = RECEIPT_SCHEMA_VERSION
    hooks_status: str = "not_applicable"

    def __post_init__(self):
        validate_operation_id(self.operation_id)
        if not isinstance(self.memory_id, str) or type(self.persisted) is not bool:
            raise ValueError("invalid write receipt identity/persistence")
        if self.schema_version != RECEIPT_SCHEMA_VERSION:
            raise ValueError("unsupported write receipt schema")
        if self.source_revision is not None and not _HASH.fullmatch(self.source_revision):
            raise ValueError("invalid source revision fingerprint")
        if self.source_state not in {"unwritten", "current", "superseded", "missing"}:
            raise ValueError("invalid source state")
        if self.hooks or self.hooks_status != "not_applicable":
            raise ValueError("post-write hooks are not implemented")
        if not all(isinstance(error, str) for error in self.errors):
            raise ValueError("invalid receipt errors")
        for status in (self.indexed, self.evidence_ledger):
            if status not in {"complete", "pending", "failed", "not_applicable"}:
                raise ValueError("invalid write receipt component status")
        if not self.persisted and "complete" in (self.indexed, self.evidence_ledger):
            raise ValueError("unpersisted write cannot have applied components")
        if self.persisted and not self.source_revision:
            raise ValueError("persisted write requires a source revision")

    @property
    def repair_required(self):
        return (self.persisted and any(status in {"pending", "failed"}
                for status in (self.indexed, self.evidence_ledger))) or bool(
                    set(self.errors) & {"receipt_store_failed", "receipt_missing"})

    def to_dict(self):
        result = asdict(self)
        result.update(hooks=list(self.hooks), errors=list(self.errors),
                      repair_required=self.repair_required,
                      retry_required=not self.persisted and self.source_revision is not None)
        return result

    @classmethod
    def from_dict(cls, value):
        data = dict(value)
        data.pop("repair_required", None)
        data.pop("retry_required", None)
        data["errors"] = tuple(data.get("errors", ()))
        data["hooks"] = tuple(data.get("hooks", ()))
        if data.get("schema_version") != RECEIPT_SCHEMA_VERSION:
            raise ValueError("unsupported write receipt schema")
        return cls(**data)


def validate_operation_id(operation_id):
    if not isinstance(operation_id, str) or not _OPERATION.fullmatch(operation_id):
        raise ValueError("operation_id must be 1-128 portable ASCII identifier characters")
    return operation_id


def _hash(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _root(engine):
    root = Path(engine.storage_dir) / ".tessera_operations"
    if root.is_symlink():
        raise ValueError("operation journal cannot be a symlink")
    return root


def _record_path(engine, operation_id):
    validate_operation_id(operation_id)
    # IDs are never interpreted as paths, including case-insensitive filesystems.
    return _root(engine) / (hashlib.sha256(operation_id.encode()).hexdigest() + ".json")


def _fsync_dir(path):
    # Windows does not offer directory fsync through this API. POSIX callers
    # receive a truthful error if the durability barrier cannot be completed.
    if os.name != "nt":
        descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _atomic_json(path, data):
    if path.is_symlink():
        raise ValueError("operation journal record cannot be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_dir(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _locked(engine):
    root = _root(engine)
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault(str(root), threading.RLock())
    with lock:
        root.mkdir(parents=True, exist_ok=True)
        _fsync_dir(root.parent)
        path = root / "store.lock"
        if path.is_symlink():
            raise ValueError("operation lock cannot be a symlink")
        with path.open("a+b") as handle:
            if os.name == "nt":  # pragma: no cover - Windows CI/platform path
                import msvcrt
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":  # pragma: no cover
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _load(engine, operation_id):
    path = _record_path(engine, operation_id)
    if path.is_symlink():
        raise ValueError("operation journal record cannot be a symlink")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        receipt = WriteReceipt.from_dict(data["receipt"])
        if receipt.operation_id != operation_id or not _HASH.fullmatch(data["request_hash"]):
            raise ValueError
        return data
    except (OSError, ValueError, TypeError, KeyError):
        raise ValueError("operation journal is corrupt; inspect and repair before retrying") from None


def _save(engine, record, receipt):
    record["receipt"] = receipt.to_dict()
    _atomic_json(_record_path(engine, receipt.operation_id), record)
    return receipt


def _checkpoint(engine, record, receipt):
    try:
        return _save(engine, record, receipt)
    except (OSError, ValueError):
        return replace(receipt, errors=tuple(sorted(set(receipt.errors) | {"receipt_store_failed"})))


def _source(engine, memory_id):
    checked = validate_memory_path(engine.storage_dir, memory_id)
    if not checked.valid or checked.destination is None:
        return None, None
    try:
        raw = checked.destination.read_bytes()
        metadata, _ = split_source(raw.decode("utf-8"), path=str(checked.destination))
        return raw, metadata.get("write_operation")
    except (OSError, ValueError, UnicodeError):
        return None, None


def _recover(engine, record):
    receipt = WriteReceipt.from_dict(record["receipt"])
    raw, marker = _source(engine, receipt.memory_id)
    if (raw is not None and isinstance(marker, dict)
            and marker.get("operation_id") == receipt.operation_id
            and marker.get("request_hash") == record["request_hash"]
            and _hash(raw) == receipt.source_revision):
        return replace(receipt, persisted=True, source_state="current")
    if receipt.persisted:
        # A later source edit/delete is never undone to replay an old operation.
        return replace(receipt, source_state="missing" if raw is None else "superseded",
                       indexed="not_applicable", evidence_ledger="not_applicable",
                       errors=("source_revision_unavailable",))
    return receipt


def _projection_files(engine, ledger=False):
    if ledger:
        path = getattr(engine, "evidence_cache_json", None)
        return [Path(path)] if path else []
    return [Path(engine.index_cache_pkl), Path(engine.index_cache_json), Path(engine.manifest_path)]


def _signatures(engine, ledger=False):
    return {path.name: _hash(path.read_bytes()) for path in _projection_files(engine, ledger)}


def _projection_state(engine):
    path = _root(engine) / ".projection-state"
    try:
        if path.is_symlink():
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _record_projection(engine, field_name, signatures, receipt):
    try:
        state = _projection_state(engine)
        state[field_name + "_files"] = signatures
        _atomic_json(_root(engine) / ".projection-state", state)
        return receipt
    except (OSError, ValueError):
        return replace(receipt, errors=tuple(sorted(set(receipt.errors) | {"receipt_store_failed"})))


def _projection_contains(engine, receipt, ledger):
    if ledger:
        path = getattr(engine, "evidence_cache_json", None)
        if not path:
            return False
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        return any(item.get("memory_id") == receipt.memory_id
                   and item.get("source", {}).get("document_hash") == receipt.source_revision.removeprefix("sha256:")
                   for item in value["records"])
    checked = validate_memory_path(engine.storage_dir, receipt.memory_id)
    relative = str(checked.destination.relative_to(Path(engine.storage_dir))).replace(os.sep, "/")
    manifest = json.loads(Path(engine.manifest_path).read_text(encoding="utf-8"))
    graph = json.loads(Path(engine.index_cache_json).read_text(encoding="utf-8"))
    return (manifest.get(relative, {}).get("file_hash") == receipt.source_revision.removeprefix("sha256:")
            and receipt.memory_id in graph["nodes"])


def _inspect(engine, record):
    receipt = _recover(engine, record)
    if not receipt.persisted or receipt.source_state != "current":
        return receipt
    state = _projection_state(engine)
    for field_name, ledger in (("indexed", False), ("evidence_ledger", True)):
        if getattr(receipt, field_name) == "not_applicable":
            continue
        try:
            expected = state.get(field_name + "_files", record.get(field_name + "_files"))
            valid = _signatures(engine, ledger) == expected and _projection_contains(engine, receipt, ledger)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            valid = False
        if valid:
            # Another operation's complete source rebuild may repair this one.
            receipt = replace(receipt, **{field_name: "complete"})
        elif getattr(receipt, field_name) == "complete":
            receipt = replace(receipt, **{field_name: "pending"})
    if receipt.indexed == receipt.evidence_ledger == "complete":
        receipt = replace(receipt, errors=tuple(error for error in receipt.errors
                          if error not in {"index_update_failed", "evidence_update_failed", "persistence_failed"}))
    return receipt


def _rebuild(engine, record, receipt):
    if not receipt.persisted or receipt.source_state != "current":
        return _checkpoint(engine, record, receipt)
    receipt = replace(receipt, indexed="pending", evidence_ledger="pending", errors=())
    receipt = _checkpoint(engine, record, receipt)
    try:
        # A clean source rebuild deliberately bypasses every pickle and stale
        # in-memory cache. Silence legacy parser diagnostics (may contain text).
        with redirect_stderr(io.StringIO()):
            engine._write_receipt_index()
        if engine.processing_warnings:
            raise ValueError("source parsing failed")
        data = engine.graph.nodes.get(receipt.memory_id, {})
        canonical = data.get("canonical_metadata")
        if canonical is None or canonical.source.document_hash != receipt.source_revision.removeprefix("sha256:"):
            raise ValueError("written revision was not indexed")
        engine.save_index()
        # Legacy manifest persistence suppresses I/O errors; verify it explicitly.
        manifest = json.loads(Path(engine.manifest_path).read_text(encoding="utf-8"))
        relative = engine._relative_identity_path(engine.file_registry[receipt.memory_id])
        if manifest.get(relative, {}).get("file_hash") != receipt.source_revision.removeprefix("sha256:"):
            raise ValueError("identity manifest was not persisted")
        record["indexed_files"] = _signatures(engine)
        receipt = replace(receipt, indexed="complete")
        receipt = _record_projection(engine, "indexed", record["indexed_files"], receipt)
        receipt = _checkpoint(engine, record, receipt)
    except Exception:
        return _checkpoint(engine, record, replace(receipt, indexed="failed",
                           evidence_ledger="pending", errors=("index_update_failed",)))
    if not hasattr(engine, "_rebuild_evidence_ledger"):
        return _checkpoint(engine, record, replace(receipt, evidence_ledger="not_applicable"))
    try:
        engine._rebuild_evidence_ledger()
        engine._persist_evidence_summary()
        record["evidence_ledger_files"] = _signatures(engine, True)
        receipt = replace(receipt, evidence_ledger="complete")
        receipt = _record_projection(engine, "evidence_ledger", record["evidence_ledger_files"], receipt)
    except Exception:
        receipt = replace(receipt, evidence_ledger="failed", errors=("evidence_update_failed",))
    return _checkpoint(engine, record, receipt)


def _is_canonical_marker(engine, path, metadata, marker):
    if not isinstance(marker, dict) or not isinstance(marker.get("request_hash"), str):
        return False
    if not _HASH.fullmatch(marker["request_hash"]):
        return False
    checked = validate_memory_path(engine.storage_dir, metadata.get("id"))
    return checked.valid and checked.destination == Path(path).resolve(strict=False)


def _recover_from_source(engine, operation_id, memory_id=None):
    paths = ([validate_memory_path(engine.storage_dir, memory_id).destination]
             if memory_id is not None else engine._iter_source_files(recursive=True))
    for path in paths:
        if path is None:
            continue
        try:
            raw = Path(path).read_bytes()
            metadata, _ = split_source(raw.decode("utf-8"), path=str(path))
            marker = metadata.get("write_operation", {})
            if not _is_canonical_marker(engine, path, metadata, marker):
                continue
            if marker.get("operation_id") != operation_id:
                continue
            receipt = WriteReceipt(operation_id, metadata["id"], True, _hash(raw),
                                   source_state="current", errors=("receipt_missing",))
            return {"request_hash": marker["request_hash"], "receipt": receipt.to_dict()}
        except (OSError, ValueError, KeyError, TypeError, UnicodeError):
            continue
    return None


def _reconcile_pending(engine):
    # Before another protocol writer can replace a source, acknowledge an
    # earlier crash-after-replace operation while its marker is still present.
    for path in sorted(_root(engine).glob("*.json")):
        try:
            if path.is_symlink():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            old = WriteReceipt.from_dict(record["receipt"])
            if not old.persisted:
                recovered = _recover(engine, record)
                if recovered.persisted:
                    _save(engine, record, recovered)
        except (OSError, ValueError, TypeError, KeyError):
            continue


def write_with_receipt(engine, arguments, operation_id):
    try:
        return _write_with_receipt(engine, arguments, operation_id)
    except OSError:
        # Includes inability to establish the local operation lock/journal.
        raw, marker = _source(engine, arguments["mem_id"])
        persisted = isinstance(marker, dict) and marker.get("operation_id") == operation_id
        decision = engine.gating_engine.evaluate(arguments["content"], arguments["tags"])
        receipt = WriteReceipt(operation_id, arguments["mem_id"], persisted,
                               _hash(raw) if persisted else None,
                               errors=("receipt_store_failed",),
                               source_state="current" if persisted else "unwritten")
        destination = validate_memory_path(engine.storage_dir, arguments["mem_id"]).destination
        return WriteResult(receipt.memory_id, str(destination) if persisted else None,
                           persisted, decision, receipt)


def _write_with_receipt(engine, arguments, operation_id):
    validate_operation_id(operation_id)
    # Validate/admit before journal, lock, directory, or source mutation.
    if arguments["persist_format"] != "md":
        return engine._write_memory_note_result(**arguments)
    path = validate_memory_path(engine.storage_dir, arguments["mem_id"])
    decision = (engine.gating_engine.evaluate(arguments["content"], arguments["tags"])
                if path.valid else engine.gating_engine.reject_invalid_memory_id(arguments["content"]))
    receipt = WriteReceipt(operation_id, arguments["mem_id"])
    if decision.admission in {WriteAdmission.REJECT, WriteAdmission.REVIEW}:
        receipt = replace(receipt, indexed="not_applicable", evidence_ledger="not_applicable")
        return WriteResult(arguments["mem_id"], None, False, decision, receipt)
    normalized = dict(arguments)
    normalized["entities"] = [asdict(item) for item in arguments["entities"]]
    normalized["active_connections"] = [asdict(item) for item in (arguments["active_connections"] or [])]
    normalized["provenance_turns"] = arguments["provenance_turns"] or []
    request_hash = _hash(json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode())
    with _locked(engine):
        _reconcile_pending(engine)
        record = _load(engine, operation_id)
        if record is None:
            record = _recover_from_source(engine, operation_id)
        if record is not None:
            if record["request_hash"] != request_hash:
                raise ValueError("operation_id was already used for a different request")
            receipt = _recover(engine, record)
            if receipt.persisted:
                receipt = _inspect(engine, record)
                if receipt.repair_required:
                    receipt = _rebuild(engine, record, receipt)
                else:
                    receipt = _checkpoint(engine, record, receipt)
                return WriteResult(receipt.memory_id, str(path.destination), True, decision, receipt)
        current_raw, _ = _source(engine, receipt.memory_id)
        current_revision = _hash(current_raw) if current_raw is not None else None
        if record is not None and record.get("previous_revision") != current_revision:
            raise ValueError("source changed since the interrupted write; use a new operation_id")
        record = {"request_hash": request_hash, "receipt": receipt.to_dict(),
                  "previous_revision": current_revision}

        def prepared(markdown):
            nonlocal receipt
            receipt = replace(receipt, source_revision=_hash(markdown.encode("utf-8")))
            _save(engine, record, receipt)  # intent must be durable before source replace

        try:
            result = engine._write_memory_note_result(
                **arguments, _write_operation={"schema_version": 1, "operation_id": operation_id,
                                              "request_hash": request_hash}, _before_persist=prepared)
            for directory in (path.destination.parent, *path.destination.parent.parents):
                _fsync_dir(directory)
                if directory == Path(engine.storage_dir):
                    break
            receipt = replace(receipt, persisted=True, source_state="current")
        except Exception:
            # os.replace may have succeeded immediately before a durability or
            # checkpoint failure. Re-read source rather than inferring absence.
            receipt = _recover(engine, record)
            receipt = replace(receipt, errors=("persistence_failed",))
            receipt = _checkpoint(engine, record, receipt)
            return WriteResult(receipt.memory_id, str(path.destination) if receipt.persisted else None,
                               receipt.persisted, decision, receipt)
        receipt = _checkpoint(engine, record, receipt)
        receipt = _rebuild(engine, record, receipt)
        return WriteResult(result.memory_id, result.filepath, True, decision, receipt)


def inspect_write_receipt(engine, operation_id):
    validate_operation_id(operation_id)
    record = _load(engine, operation_id)
    if record is None:
        record = _recover_from_source(engine, operation_id)
    if record is None:
        raise ValueError("operation_id not found")
    return _inspect(engine, record)


def repair_write_receipt(engine, operation_id):
    validate_operation_id(operation_id)
    with _locked(engine):
        try:
            record = _load(engine, operation_id)
        except ValueError:
            record = _recover_from_source(engine, operation_id)
            if record is None:
                raise ValueError("corrupt receipt cannot be recovered from current source") from None
        if record is None:
            record = _recover_from_source(engine, operation_id)
        if record is None:
            raise ValueError("operation_id not found")
        return _rebuild(engine, record, _recover(engine, record))


def inspect_write_receipts(engine):
    """Read-only inventory; corrupt entries remain visible without source text."""
    root = _root(engine)
    result = []
    for path in sorted(root.glob("*.json")):
        try:
            if path.is_symlink():
                raise ValueError
            record = json.loads(path.read_text(encoding="utf-8"))
            result.append(_inspect(engine, record).to_dict())
        except (OSError, ValueError, TypeError, KeyError):
            result.append({"schema_version": 1, "status": "corrupt", "repair_required": True,
                           "errors": ["invalid_write_receipt"]})
    known = {item.get("operation_id") for item in result}
    for source in engine._iter_source_files(recursive=True):
        try:
            raw = Path(source).read_bytes()
            metadata, _ = split_source(raw.decode("utf-8"), path=str(source))
            marker = metadata.get("write_operation", {})
            if not _is_canonical_marker(engine, source, metadata, marker):
                continue
            operation_id = marker.get("operation_id")
            if operation_id and operation_id not in known:
                validate_operation_id(operation_id)
                result.append(WriteReceipt(operation_id, metadata["id"], True, _hash(raw),
                                           source_state="current", errors=("receipt_missing",)).to_dict())
                known.add(operation_id)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            continue
    return result
