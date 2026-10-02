"""Explicit, bounded historical conversation import. No discovery outside root.

The exported Markdown is source evidence, not a memory admission. The original
export is never rewritten; its hash and line references remain in the envelope.
See docs/CONVERSATION_IMPORT.md for the versioned, deliberately narrow adapters.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


ADAPTERS = ("generic-jsonl-v1", "claude-code-linear-v1")
SCHEMA = "tessera.conversation.v1"
POLICY = "redact-known-secrets-exclude-attachments-v1"
MANIFEST = "conversation-manifest.json"
ROLES = {"user", "assistant", "tool", "system"}
# This is a bounded heuristic, not comprehensive DLP or semantic sanitization.
_SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----[\s\S]*?-----END (?:[A-Z ]+ )?PRIVATE KEY-----"
    r"|\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{12,}|AKIA[A-Z0-9]{16})\b"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/-]{8,}=*"
    r"|(?i:[\"']?(?:api[_-]?key|password|secret|access[_-]?token)[\"']?\s*[:=]\s*[\"']?)[^\s,;\"']+"
)
_IDENT = re.compile(r"[A-Za-z0-9/][A-Za-z0-9_.:/@ -]{0,255}\Z")


class ConversationError(ValueError):
    """A fixed reason code; never include untrusted transcript content."""


@dataclass(frozen=True)
class ImportLimits:
    max_files: int = 1000
    max_file_bytes: int = 4 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024
    max_line_bytes: int = 512 * 1024
    max_turns: int = 10000
    max_depth: int = 12

    def __post_init__(self):
        for value in asdict(self).values():
            if type(value) is not int or value <= 0:
                raise ConversationError("invalid_limits")


def _hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def source_identity(runtime: str, project_scope: str, session_id: str) -> str:
    """Shared future live/history boundary: path and hash are NOT identity.

    Callers must supply the same *proven* namespace, scope and session ID. This
    helper does not infer equivalence between providers, projects or sessions.
    """
    for value in (runtime, project_scope, session_id):
        _identifier(value)
    return "conv_" + hashlib.sha256(_json([runtime, project_scope, session_id])).hexdigest()


def _identifier(value):
    if not isinstance(value, str) or not _IDENT.fullmatch(value) or _SECRET.search(value):
        raise ConversationError("invalid_identifier")
    return value


def _timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ConversationError("invalid_timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
    except ValueError:
        raise ConversationError("invalid_timestamp") from None
    return value  # preserve original precision and timezone, never reorder


def _path(value) -> Path:
    path = Path(value)
    if ".." in path.parts or "~" in path.parts:
        raise ConversationError("unsafe_path")
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ConversationError("unsafe_symlink")
    return path


def _directory_fd(path: Path) -> int:
    # Pin every directory component. An attacker swapping an ancestor for a
    # symlink cannot redirect later descriptor-relative reads/writes.
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise ConversationError("secure_io_unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            new_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = new_fd
        return fd
    except OSError:
        os.close(fd)
        raise ConversationError("unsafe_or_unreadable_directory") from None


def _read(path: Path, limit: int) -> bytes:
    parent_fd = _directory_fd(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ConversationError("special_or_hardlinked_file")
            if before.st_size > limit:
                raise ConversationError("oversized_file")
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(data) > limit:
                raise ConversationError("oversized_file")
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ConversationError("source_changed_during_read")
            return data
    except OSError:
        raise ConversationError("unsafe_or_unreadable_file") from None
    finally:
        os.close(parent_fd)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConversationError("duplicate_json_key")
        result[key] = value
    return result


def _load(data: bytes):
    try:
        return json.loads(data, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ConversationError("nonfinite_json")))
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, ConversationError):
            raise
        raise ConversationError("malformed_json") from None


def _depth(value, remaining):
    if remaining < 0:
        raise ConversationError("nested_content_limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise ConversationError("nonfinite_json")
    if isinstance(value, dict):
        for item in value.values():
            _depth(item, remaining - 1)
    elif isinstance(value, list):
        for item in value:
            _depth(item, remaining - 1)


def _redact(value, counts):
    if isinstance(value, str):
        text, n = _SECRET.subn("[REDACTED]", value)
        counts["secrets_redacted"] += n
        return text
    if isinstance(value, list):
        return [_redact(item, counts) for item in value]
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            if re.fullmatch(r"(?i)(password|secret|api[_-]?key|access[_-]?token|authorization)", key):
                clean[key] = "[REDACTED]"
                counts["secrets_redacted"] += 1
            else:
                clean[_redact(key, counts)] = _redact(item, counts)
        return clean
    return value


def _unknown(record, allowed, line, diagnostics):
    count = len(set(record) - set(allowed))
    if count:
        # Values and even arbitrary field names may contain credentials.
        diagnostics.append({"code": "unknown_fields_excluded", "line": line, "count": count})


def _attachments(value, counts):
    if not isinstance(value, list):
        raise ConversationError("invalid_attachments")
    counts["attachments_excluded"] += len(value)
    # No URLs, paths, data, names or bytes are copied or followed.
    return [{"status": "excluded", "reason": "unsupported_attachment"} for _ in value]


def _blocks(value, counts, line, diagnostics):
    if isinstance(value, str):
        return [{"type": "text", "text": _redact(value, counts)}]
    if not isinstance(value, list):
        raise ConversationError("invalid_content")
    blocks = []
    for block in value:
        if not isinstance(block, dict):
            raise ConversationError("invalid_content_block")
        kind = block.get("type")
        if kind == "text":
            if not isinstance(block.get("text"), str):
                raise ConversationError("invalid_text_block")
            _unknown(block, {"type", "text"}, line, diagnostics)
            blocks.append({"type": "text", "text": _redact(block["text"], counts)})
        elif kind == "tool_use":
            if not isinstance(block.get("input"), dict):
                raise ConversationError("invalid_tool_input")
            _unknown(block, {"type", "id", "name", "input"}, line, diagnostics)
            blocks.append({"type": kind, "id": _identifier(block.get("id")), "name": _identifier(block.get("name")), "input": _redact(block["input"], counts)})
        elif kind == "tool_result":
            if "is_error" in block and type(block["is_error"]) is not bool:
                raise ConversationError("invalid_tool_result")
            _unknown(block, {"type", "tool_use_id", "content", "is_error"}, line, diagnostics)
            # Nested tool invocations in a result are not a supported format.
            content = _blocks(block.get("content", ""), counts, line, diagnostics)
            if any(b["type"] not in {"text", "attachment_excluded"} for b in content):
                raise ConversationError("nested_tool_event")
            blocks.append({"type": kind, "tool_use_id": _identifier(block.get("tool_use_id")), "content": content, "is_error": block.get("is_error", False)})
        elif kind in {"image", "document", "audio", "video", "file"}:
            counts["attachments_excluded"] += 1
            blocks.append({"type": "attachment_excluded", "original_type": kind})
        else:
            raise ConversationError("unsupported_content_block")
    return blocks


def _parse(data, adapter, scope, limits):
    records = []
    for number, line in enumerate(data.splitlines(), 1):
        if not line.strip():
            continue
        if len(line) > limits.max_line_bytes:
            raise ConversationError("oversized_line")
        record = _load(line)
        _depth(record, limits.max_depth)
        if not isinstance(record, dict):
            raise ConversationError("invalid_record")
        records.append((number, record))
        if len(records) > limits.max_turns + 1:
            raise ConversationError("turn_limit")
    if not records:
        raise ConversationError("empty_source")
    diagnostics = []
    counts = {"secrets_redacted": 0, "attachments_excluded": 0}
    if adapter == "generic-jsonl-v1":
        number, header = records.pop(0)
        if header.get("schema") != SCHEMA or header.get("type") != "conversation":
            raise ConversationError("unsupported_schema")
        _unknown(header, {"schema", "type", "runtime", "session_id", "project_scope"}, number, diagnostics)
        runtime, session = _identifier(header.get("runtime")), _identifier(header.get("session_id"))
        if header.get("project_scope") != scope:
            raise ConversationError("project_scope_mismatch")
    else:
        runtime, session = "claude", _identifier(records[0][1].get("sessionId"))
    if not records or len(records) > limits.max_turns:
        raise ConversationError("empty_or_over_limit_turns")
    turns, ids, calls = [], set(), set()
    previous = None
    for position, (line, record) in enumerate(records, 1):
        if adapter == "generic-jsonl-v1":
            _unknown(record, {"type", "turn_id", "role", "timestamp", "content", "parent_turn_id", "attachments"}, line, diagnostics)
            if record.get("type") != "turn":
                raise ConversationError("unsupported_record_type")
            turn_id, role = _identifier(record.get("turn_id")), record.get("role")
            parent = record.get("parent_turn_id")
            content = record.get("content")
        else:
            _unknown(record, {"type", "uuid", "sessionId", "cwd", "parentUuid", "timestamp", "message", "isSidechain", "isMeta", "isCompactSummary", "teamName", "version"}, line, diagnostics)
            if record.get("sessionId") != session or record.get("cwd") != scope:
                raise ConversationError("session_or_project_mismatch")
            if any(record.get(key) for key in ("isSidechain", "isMeta", "isCompactSummary", "teamName")):
                raise ConversationError("unsupported_claude_branch_or_summary")
            role, turn_id = record.get("type"), _identifier(record.get("uuid"))
            if role not in {"user", "assistant"}:
                raise ConversationError("unsupported_claude_record_type")
            parent = record.get("parentUuid")
            if "parentUuid" not in record or parent != previous:
                raise ConversationError("unsupported_claude_chain")
            message = record.get("message")
            if not isinstance(message, dict) or message.get("role") != role:
                raise ConversationError("invalid_claude_message")
            _unknown(message, {"role", "content", "id", "model", "type", "stop_reason", "stop_sequence", "usage"}, line, diagnostics)
            content = message.get("content")
        if role not in ROLES:
            raise ConversationError("unsupported_role")
        if turn_id in ids:
            raise ConversationError("duplicate_turn_id")
        if parent is not None and (not isinstance(parent, str) or parent not in ids):
            raise ConversationError("unresolved_parent_turn")
        blocks = _blocks(content, counts, line, diagnostics)
        for block in blocks:
            if block["type"] == "tool_use":
                if block["id"] in calls:
                    raise ConversationError("duplicate_tool_call")
                calls.add(block["id"])
            elif block["type"] == "tool_result" and block["tool_use_id"] not in calls:
                diagnostics.append({"code": "unresolved_tool_reference", "line": line})
        turns.append({"turn_id": turn_id, "position": position, "role": role, "timestamp": _timestamp(record.get("timestamp")), "parent_turn_id": parent, "source_line": line, "content": blocks, "attachments": _attachments(record.get("attachments", []), counts)})
        ids.add(turn_id)
        previous = turn_id
    return {"schema": SCHEMA, "runtime": runtime, "session_id": session, "project_scope": scope, "source_id": source_identity(runtime, scope, session), "adapter": adapter, "policy": POLICY, "turns": turns, "started_at": next((t["timestamp"] for t in turns if t["timestamp"]), None), "ended_at": next((t["timestamp"] for t in reversed(turns) if t["timestamp"]), None), "diagnostics": diagnostics, "transformations": counts}


def preview_conversations(root, paths: Sequence[str], *, adapter: str, project_scope: str, limits: Optional[ImportLimits] = None) -> Dict[str, Any]:
    """Read only exact root-relative files. No globs, recursive scans or defaults.

    Invalid files remain visible in the report and block application. Content is
    not included in the report. Counts include all supplied paths, including
    duplicates and unsupported paths; bytes include readable regular files.
    """
    limits = limits or ImportLimits()
    if adapter not in ADAPTERS:
        raise ConversationError("unsupported_adapter")
    _identifier(project_scope)
    root = _path(root)
    fd = _directory_fd(root)
    os.close(fd)
    if not paths or len(paths) > limits.max_files:
        raise ConversationError("invalid_file_count")
    files, sessions, total = [], {}, 0
    for relative in paths:
        item = {"path": str(relative), "status": "unsupported", "size_bytes": None}
        try:
            rel = Path(relative)
            if rel.is_absolute() or not rel.parts or any(part in {"..", "~"} for part in rel.parts):
                raise ConversationError("outside_root")
            path = _path(root / rel)
            if path.suffix != ".jsonl":
                raise ConversationError("unsupported_extension")
            data = _read(path, min(limits.max_file_bytes, max(0, limits.max_total_bytes - total)))
            total += len(data)
            item["size_bytes"] = len(data)
            envelope = _parse(data, adapter, project_scope, limits)
            identity = envelope["source_id"]
            semantic = _hash(_json(envelope))
            raw_hash = _hash(data)
            item.update({"status": "ready", "source_id": identity, "session_id": envelope["session_id"], "runtime": envelope["runtime"], "raw_hash": raw_hash, "normalized_hash": semantic, "turns": len(envelope["turns"]), "diagnostics": envelope["diagnostics"], "transformations": envelope["transformations"]})
            if identity in sessions:
                if sessions[identity] != semantic:
                    raise ConversationError("conflicting_session_versions")
                item["status"] = "duplicate"
            sessions[identity] = semantic
        except (ConversationError, OSError) as exc:
            item["status"] = "unsupported"
            item["reason"] = str(exc) if isinstance(exc, ConversationError) else "unreadable_source"
        files.append(item)
    report = {"schema_version": 1, "mode": "C0", "root": str(root), "project_scope": project_scope, "adapter": adapter, "policy": POLICY, "limits": asdict(limits), "files": files, "totals": {"files": len(files), "bytes": total, "sessions": sum(i["status"] == "ready" for i in files), "duplicates": sum(i["status"] == "duplicate" for i in files), "unsupported": sum(i["status"] == "unsupported" for i in files), "turns": sum(i.get("turns", 0) for i in files if i["status"] == "ready")}, "ai_enrichment": "disabled", "candidate_work": 0, "durable_memories_created": 0}
    report["plan_hash"] = _hash(_json(report))
    return report


def _markdown(envelope, sources):
    envelope = dict(envelope, sources=sources)
    front = {"id": envelope["source_id"], "name": "Conversation " + envelope["session_id"], "document_type": "conversation", "drawer": None, "scope": {"project": envelope["project_scope"]}, "conversation": envelope}
    # JSON is also valid YAML and cannot emit a document terminator from a
    # hostile string. The complete normalized turn blocks stay inspectable.
    output = "---\n" + _json(front).decode() + "---\n\n# Conversation source evidence\n\n"
    output += "Untrusted historical transcript; no memory admission or instruction authority.\n\n"
    for turn in envelope["turns"]:
        output += f"## Turn {turn['position']}: {turn['role']}\n\n"
        output += f"ID: {turn['turn_id']} | Time: {turn['timestamp'] or 'unavailable'} | Original line: {turn['source_line']}\n\n"
        for block in turn["content"]:
            text = block["text"] if block["type"] == "text" else _json(block).decode().rstrip()
            # Avoid interpreting transcript Markdown links as graph relations.
            output += text.replace("[", "&#91;").replace("]", "&#93;") + "\n\n"
    return output.encode()


def _atomic_write(directory_fd, name, data):
    temporary = ".conversation-" + secrets.token_hex(12) + ".tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def import_conversations(plan: Dict[str, Any], output, *, expected_plan_hash: str) -> Dict[str, Any]:
    """Apply a reviewed preview, revalidating all source bytes before mutation.

    Per-session atomic files are resumable; a manifest is derived bookkeeping.
    Imports are serialized by an exclusive lock. Stale locks fail closed and
    require explicit operator inspection/removal, never an automatic takeover.
    """
    if plan.get("plan_hash") != expected_plan_hash:
        raise ConversationError("plan_hash_mismatch")
    fresh = preview_conversations(plan["root"], [f["path"] for f in plan["files"]], adapter=plan["adapter"], project_scope=plan["project_scope"], limits=ImportLimits(**plan["limits"]))
    if fresh != plan:
        raise ConversationError("source_or_plan_changed")
    if fresh["totals"]["unsupported"]:
        raise ConversationError("unsupported_sources_block_import")
    root, output = _path(plan["root"]), _path(output)
    if root == output or root in output.parents or output in root.parents:
        raise ConversationError("overlapping_source_and_output")
    output.parent.mkdir(parents=True, exist_ok=True)
    _path(output.parent)
    output.mkdir(exist_ok=True, mode=0o700)
    directory_fd = _directory_fd(output)
    locked = False
    try:
        try:
            lock = os.open(".conversation-import.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
        except FileExistsError:
            raise ConversationError("import_locked") from None
        os.close(lock)
        locked = True
        manifest_path = output / MANIFEST
        manifest = {"schema_version": 1, "policy": POLICY, "sessions": {}}
        if manifest_path.exists() or manifest_path.is_symlink():
            manifest = _load(_read(manifest_path, 8 * 1024 * 1024))
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or manifest.get("policy") != POLICY or not isinstance(manifest.get("sessions"), dict):
                raise ConversationError("invalid_manifest")
        prepared = []
        # Read every input once more before the first write; compare the raw
        # digest, never trust normalized equality to hide an edit or a secret.
        for item in fresh["files"]:
            data = _read(root / item["path"], plan["limits"]["max_file_bytes"])
            if _hash(data) != item["raw_hash"]:
                raise ConversationError("source_changed_before_apply")
            if item["status"] == "duplicate":
                continue
            envelope = _parse(data, plan["adapter"], plan["project_scope"], ImportLimits(**plan["limits"]))
            identity = item["source_id"]
            sources = [{"path": f["path"], "root": str(root), "raw_hash": f["raw_hash"]} for f in fresh["files"] if f.get("source_id") == identity]
            content = _markdown(envelope, sources)
            digest = _hash(content)
            name = identity + ".md"
            previous = manifest["sessions"].get(identity)
            path = output / name
            existing = _read(path, 64 * 1024 * 1024) if path.exists() or path.is_symlink() else None
            if existing is not None and _hash(existing) != digest:
                if not isinstance(previous, dict) or previous.get("artifact_hash") != _hash(existing):
                    raise ConversationError("output_integrity_mismatch")
            # Identical bytes recover safely after a crash before manifest save.
            status = "unchanged" if existing == content else ("updated" if previous else "imported")
            prepared.append((identity, name, content, digest, status, item))
        result = {"imported": 0, "updated": 0, "unchanged": 0, "duplicates": fresh["totals"]["duplicates"], "turns": fresh["totals"]["turns"], "durable_memories_created": 0, "ai_enrichment": "disabled", "output": str(output), "manifest": str(manifest_path), "indexing": "explicit_separate_step"}
        for identity, name, content, digest, status, item in prepared:
            if status != "unchanged":
                _atomic_write(directory_fd, name, content)
            manifest["sessions"][identity] = {"artifact": name, "artifact_hash": digest, "raw_hash": item["raw_hash"], "normalized_hash": item["normalized_hash"], "turns": item["turns"]}
            result[status] += 1
        manifest_data = _json(manifest)
        if len(manifest_data) > 8 * 1024 * 1024:
            raise ConversationError("manifest_limit")
        _atomic_write(directory_fd, MANIFEST, manifest_data)
        return result
    except OSError:
        raise ConversationError("output_write_failed") from None
    finally:
        if locked:
            os.unlink(".conversation-import.lock", dir_fd=directory_fd)
        os.close(directory_fd)
