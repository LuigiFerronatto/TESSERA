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
import stat
import sys
import tempfile

from .canonical import compute_sha256, effective_tags
from .okf import (
    ExchangeError, EXTENSION, SOURCE_EXTENSION, MAX_BUNDLE_BYTES, MAX_ENTRIES, MAX_FILE_BYTES, PROFILE,
    SPEC_REVISION, _parse, _safe_path, _scan, native_source_document,
    plan_import, load_native_records,
)
from .exchange_profiles import (JSON_FILENAME, PROFILES, parse_canonical_json, project_records, select_records)
from .security import WriteAdmission, WriteGatingEngine, validate_memory_path

TRANSACTION_SCHEMA = 1
MANIFEST = ".tessera-okf-exchange.json"


def _destination(source, output, *, source_file=False):
    source = Path(source).absolute()
    output = Path(output).absolute()
    if not (source.is_file() if source_file else source.is_dir()) or source.is_symlink():
        raise ExchangeError("Source must be an existing real file/directory of the selected format")
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
        if path.endswith(".md"):
            if not validate_memory_path(str(output), path[:-3]).valid:
                raise ExchangeError("Output source path is not portable Markdown")
        elif path not in {JSON_FILENAME, "memories.csv"}:
            raise ExchangeError("Output path is outside the named exchange profiles")
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
        if size > (MAX_FILE_BYTES if path.endswith(".md") else MAX_BUNDLE_BYTES):
            raise ExchangeError("Rendered source exceeds the supported file size")
        total += size
    if folded & directories or total > MAX_BUNDLE_BYTES or len(files) + len(directories) + 1 > MAX_ENTRIES:
        raise ExchangeError("Output path collision or bundle limit exceeded")
    return total


def _read_json_source(source):
    source = Path(source).absolute()
    if any(p.is_symlink() for p in (source, *source.parents)):
        raise ExchangeError("Canonical JSON symlinks are not supported")
    if source.stat().st_size > MAX_BUNDLE_BYTES:
        raise ExchangeError("Canonical JSON exceeds the supported size")
    fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ExchangeError("Canonical JSON source is not a regular file")
        data = handle.read(MAX_BUNDLE_BYTES + 1)
    if len(data) > MAX_BUNDLE_BYTES:
        raise ExchangeError("Canonical JSON source grew beyond the supported size")
    return data.decode("utf-8")


def _tags_for_record(record):
    return effective_tags(record.canonical.raw_frontmatter)


def plan_destination(source, output, *, operation, namespace=None, profile="okf", selection=None):
    """Plan source copies/export into a new tree, with zero write side effects."""
    if operation not in {"convert", "export"} or profile not in PROFILES:
        raise ExchangeError("Unknown exchange operation/profile")
    if operation == "convert" and profile not in {"okf", "canonical-json"}:
        raise ExchangeError("Convert accepts OKF or the versioned canonical JSON profile")
    json_input = operation == "convert" and profile == "canonical-json"
    source, output = _destination(source, output, source_file=json_input)
    if json_input:
        text = _read_json_source(source)
        records, source_manifest = parse_canonical_json(text)
        docs, skipped = {source.name: text}, []
        report = {"profile": profile, "schema_version": 1, "source_manifest": source_manifest,
                  "records_seen": len(records), "validation": "PASS"}
        auxiliary = {}
    else:
        docs, skipped, errors = _scan(source)
        if errors:
            raise ExchangeError("Unsafe source inventory: " + json.dumps(errors, sort_keys=True))
        if operation == "convert":
            imported = plan_import(source, namespace=namespace)
            if imported.report["mapping"] != "PASS":
                raise ExchangeError("Cannot convert a partial or review-required import plan")
            records, report, auxiliary = imported.records, imported.report, imported.auxiliary
        else:
            records, skipped = load_native_records(source)
            report, auxiliary = {}, {}
    if operation == "convert":
        selected, selection_manifest = select_records(records, selection)
        files = {r.path: native_source_document(r) for r in selected}
        excluded = [{"path": p, "reason": "reserved_navigation_not_a_memory"} for p in auxiliary]
        report = {**report, "selection_manifest": selection_manifest}
    else:
        exported = project_records(records, profile=profile, selection=selection)
        files, report = exported["files"], exported["report"]
        selected, selection_manifest = select_records(records, selection)
        excluded = []
    total = _validate_files(files, output)
    gate = WriteGatingEngine()
    record_gates = {r.canonical.identity.id: gate.evaluate(native_source_document(r), _tags_for_record(r)).to_dict() for r in selected}
    all_tags = sorted({tag for record in selected for tag in _tags_for_record(record)})
    gates = {}
    for path, text in sorted(files.items()):
        tags = set(all_tags if not path.endswith(".md") else [])
        if path.endswith(".md"):
            fm, _ = _parse(text)
            tags.update(effective_tags(fm))
            for marker in (EXTENSION, SOURCE_EXTENSION):
                envelope = fm.get(marker, {})
                if isinstance(envelope, dict) and isinstance(envelope.get("canonical"), dict):
                    raw = envelope["canonical"].get("raw_frontmatter", {})
                    if isinstance(raw, dict):
                        tags.update(effective_tags(raw))
        gates[path] = gate.evaluate(text, sorted(tags)).to_dict()
    unapproved_assets = [v for v in skipped if v["path"] != MANIFEST]
    accepted = all(g["admission"] == WriteAdmission.ACCEPT.value for g in [*gates.values(), *record_gates.values()])
    status = "READY" if not unapproved_assets and accepted else "REVIEW"
    hashes = {path: compute_sha256(text) for path, text in sorted(files.items())}
    identity = {
        "schema_version": TRANSACTION_SCHEMA, "operation": operation,
        "source": str(source), "destination": str(output), "namespace": namespace,
        "profile": profile, "canonical_profile": PROFILE, "spec_revision": SPEC_REVISION,
        "selection": selection_manifest["selection"],
        "source_hashes": {p: compute_sha256(t) for p, t in sorted(docs.items())},
        "source_skipped": skipped, "excluded": excluded,
        "file_hashes": hashes, "write_gate": gates, "record_security_gate": record_gates, "status": status,
    }
    plan_id = compute_sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False))
    # Full source/selection detail is available in the private dry-run. Published
    # manifests do not disclose excluded record IDs, selectors or source paths.
    manifest = {"schema_version": TRANSACTION_SCHEMA, "operation": operation, "profile": profile,
                "source_snapshot_hash": compute_sha256(json.dumps(identity["source_hashes"], sort_keys=True)),
                "file_hashes": hashes, "records_selected": len(selected),
                "records_excluded": len(selection_manifest["excluded"]),
                "declared_private_excluded": selection_manifest["declared_private_excluded"],
                "plan_id": plan_id, "role": "standalone_source_exchange",
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


def apply_exchange(source, output, *, operation, expected_plan_id, namespace=None, profile="okf", selection=None):
    """Replan, require exact prior approval, gate all files, then publish once.

    This function never mutates a pre-existing destination or selects a canonical store.
    It does not infer approval from elapsed time or accept a stale plan.
    """
    plan = plan_destination(source, output, operation=operation, namespace=namespace, profile=profile, selection=selection)
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
        checked = plan_destination(source, output, operation=operation, namespace=namespace, profile=profile, selection=selection)
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
