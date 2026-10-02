"""Explicit, destination-bound source conversion/export transactions for OKF.

A new source directory is not a configured store or a semantic admission. All
mutations occur after the existing narrow security gate and reviewed plan hash.
No engine, settings, existing destination, attester or network is invoked.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from .canonical import compute_sha256, effective_tags
from .okf import (
    ExchangeError, EXTENSION, SOURCE_EXTENSION, MAX_BUNDLE_BYTES, MAX_ENTRIES, MAX_FILE_BYTES, PROFILE,
    SPEC_REVISION, _parse, _safe_path, _scan, native_source_document,
    plan_import, plan_native_export,
)
from .security import WriteAdmission, WriteGatingEngine, validate_memory_path

TRANSACTION_SCHEMA = 1
MANIFEST = ".tessera-okf-exchange.json"


def _destination(source, output):
    source = Path(source).absolute()
    output = Path(output).absolute()
    if not source.is_dir() or source.is_symlink():
        raise ExchangeError("Source must be an existing real directory")
    if not output.parent.is_dir():
        raise ExchangeError("Destination parent must already exist")
    if any(p.is_symlink() for p in (source, *source.parents, output, *output.parents)):
        raise ExchangeError("Source/destination symlinks are not supported")
    source, output = source.resolve(), output.parent.resolve() / output.name
    if source == output or source in output.parents or output in source.parents:
        raise ExchangeError("Source and destination must be separate, non-overlapping trees")
    if output.exists() or any(p.name.casefold() == output.name.casefold() for p in output.parent.iterdir()):
        raise ExchangeError("Destination already exists or has a case-fold alias; never overwrite")
    if not validate_memory_path(str(output.parent), output.name).valid:
        raise ExchangeError("Destination name is not portable")
    return source, output


def _validate_files(files, output):
    if not files or len(files) > MAX_ENTRIES:
        raise ExchangeError("Output must contain a bounded, non-empty file set")
    folded, total = set(), 0
    directories = set()
    spelling = {}
    for path, text in files.items():
        _safe_path(path)
        if not path.endswith(".md") or not validate_memory_path(str(output), path[:-3]).valid:
            raise ExchangeError("Output source path is not portable Markdown")
        for prefix in (Path(path), *Path(path).parents):
            original = prefix.as_posix()
            if original == ".":
                continue
            folded_prefix = original.casefold()
            if folded_prefix in spelling and spelling[folded_prefix] != original:
                raise ExchangeError("Case-fold output directory collision")
            spelling[folded_prefix] = original
        key = path.casefold()
        if key in folded:
            raise ExchangeError("Case-fold output collision")
        folded.add(key)
        parents = Path(path).parents
        directories.update(p.as_posix().casefold() for p in parents if p.as_posix() != ".")
        size = len(text.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            raise ExchangeError("Rendered source exceeds the supported file size")
        total += size
    if folded & directories or total > MAX_BUNDLE_BYTES or len(files) + len(directories) + 1 > MAX_ENTRIES:
        raise ExchangeError("Output path collision or bundle limit exceeded")
    return total


def plan_destination(source, output, *, operation, namespace=None):
    """Plan source copies/export into a new tree, with zero write side effects."""
    if operation not in {"convert", "export"}:
        raise ExchangeError("Unknown exchange operation")
    source, output = _destination(source, output)
    docs, skipped, errors = _scan(source)
    if errors:
        raise ExchangeError("Unsafe source inventory: " + json.dumps(errors, sort_keys=True))
    if operation == "convert":
        imported = plan_import(source, namespace=namespace)
        if imported.report["mapping"] != "PASS":
            raise ExchangeError("Cannot convert a partial or review-required import plan")
        files = {r.path: native_source_document(r) for r in imported.records}
        # Reserved index/log navigation remains in the original source. Copying
        # it as native memories would manufacture extra retrievable records.
        excluded = [{"path": p, "reason": "reserved_navigation_not_a_memory"} for p in imported.auxiliary]
        report = imported.report
    else:
        exported = plan_native_export(source)
        files = exported["files"]
        excluded = []
        report = exported["report"]
    total = _validate_files(files, output)
    gate = WriteGatingEngine()
    gates = {}
    for path, text in sorted(files.items()):
        fm, _ = _parse(text)
        # Evaluate the exact emitted bytes, including unknown metadata, so a
        # nested instruction cannot sidestep the existing hostile-pattern gate.
        tags = set(effective_tags(fm))
        for marker in (EXTENSION, SOURCE_EXTENSION):
            envelope = fm.get(marker, {})
            if isinstance(envelope, dict) and isinstance(envelope.get("canonical"), dict):
                raw = envelope["canonical"].get("raw_frontmatter", {})
                if isinstance(raw, dict):
                    tags.update(effective_tags(raw))
        decision = gate.evaluate(text, sorted(tags))
        gates[path] = decision.to_dict()
    unapproved_assets = [v for v in skipped if v["path"] != MANIFEST]
    status = "READY" if not unapproved_assets and all(g["admission"] == WriteAdmission.ACCEPT.value for g in gates.values()) else "REVIEW"
    hashes = {path: compute_sha256(text) for path, text in sorted(files.items())}
    identity = {
        "schema_version": TRANSACTION_SCHEMA, "operation": operation,
        "source": str(source), "destination": str(output), "namespace": namespace,
        "profile": PROFILE, "spec_revision": SPEC_REVISION,
        "source_hashes": {p: compute_sha256(t) for p, t in sorted(docs.items())},
        "source_skipped": skipped, "excluded": excluded,
        "file_hashes": hashes, "write_gate": gates, "status": status,
    }
    plan_id = compute_sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False))
    manifest = {**identity, "plan_id": plan_id, "role": "standalone_source_exchange",
                "semantic_admission": "NOT_PERFORMED", "runtime_registration": "NOT_PERFORMED"}
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if total + len(manifest_text.encode("utf-8")) > MAX_BUNDLE_BYTES:
        raise ExchangeError("Output manifest exceeds the supported bundle size")
    return {**identity, "plan_id": plan_id, "files": {**files, MANIFEST: manifest_text},
            "report": report, "file_count": len(files) + 1,
            "total_bytes": total + len(manifest_text.encode("utf-8")),
            "persistence": "NOT_PERFORMED", "semantic_admission": "NOT_PERFORMED",
            "runtime_registration": "NOT_PERFORMED", "decision": "ITERATE"}


def _publisher():
    """Use Linux atomic no-replace, never a check-then-overwriting rename.

    https://man7.org/linux/man-pages/man2/rename.2.html defines RENAME_NOREPLACE.
    Unsupported platforms/filesystems fail closed; JSON planning is portable.
    """
    if not sys.platform.startswith("linux"):
        raise ExchangeError("Apply requires Linux renameat2 no-replace support; planning remains available")
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise ExchangeError("Atomic no-replace directory publication is unavailable")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    def publish(stage, destination):
        if rename(-100, os.fsencode(stage), -100, os.fsencode(destination), 1) != 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code), str(destination))
    return publish


def _write_file(path, text):
    missing = []
    parent = path.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        data = text.encode("utf-8")
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if path.read_bytes() != data:
        raise ExchangeError("Staged file verification failed")


def apply_exchange(source, output, *, operation, expected_plan_id, namespace=None):
    """Replan, require exact prior approval, gate all files, then publish once.

    This function never mutates a pre-existing destination or canonical store.
    It does not infer approval from elapsed time or accept a stale plan.
    """
    plan = plan_destination(source, output, operation=operation, namespace=namespace)
    if not isinstance(expected_plan_id, str) or plan["plan_id"] != expected_plan_id:
        raise ExchangeError("Plan changed or expected plan_id is missing; review the new plan")
    if plan["status"] != "READY":
        raise ExchangeError("Write gate or unsupported assets require review; no files written")
    publish = _publisher()  # capability check before any temporary directory
    output = Path(plan["destination"])
    stage = Path(tempfile.mkdtemp(prefix=".tessera-okf-", dir=output.parent))
    try:
        for relative, text in sorted(plan["files"].items()):
            _write_file(stage / relative, text)
        # Recheck inputs and output state after staging; no stale source or
        # intervening destination may become a successful apply receipt.
        checked = plan_destination(source, output, operation=operation, namespace=namespace)
        if checked["plan_id"] != plan["plan_id"]:
            raise ExchangeError("Source changed during staging; transaction aborted")
        publish(stage, output)
    except BaseException:
        # Only our private unpublished staging tree is removed. Never clean or
        # repair the requested destination after a competing writer created it.
        if stage.exists():
            shutil.rmtree(stage)
        raise
    return {"status": "APPLIED", "plan_id": plan["plan_id"], "destination": str(output),
            "operation": operation, "file_count": plan["file_count"],
            "file_hashes": {p: compute_sha256(t) for p, t in sorted(plan["files"].items())},
            "persistence": "STANDALONE_SOURCE_FILES", "semantic_admission": "NOT_PERFORMED",
            "runtime_registration": "NOT_PERFORMED", "decision": "ITERATE",
            "durability": "files fsynced; directory crash durability not promised"}
