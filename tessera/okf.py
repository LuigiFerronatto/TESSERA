"""Experimental, offline OKF exchange plans; never persist or execute imports.

The existing CanonicalMetadata remains authoritative. This opt-in boundary is
not imported by Engine, CLI, MCP, discovery or the native parser.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, fields
from datetime import datetime
import json
import math
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlsplit

import yaml

from . import canonical as canonical_types
from .canonical import (
    CanonicalMetadata, ClassificationMetadata, IdentityMetadata, QualityMetadata,
    RelationMetadata, ScopeMetadata, SourceMetadata, SourceSpan, TemporalMetadata,
    compute_sha256, parse_and_normalize,
)

SPEC_REVISION = "ad30107c31c06aec8a7d5636e0d1058118604e6f"
SPEC_URL = f"https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/{SPEC_REVISION}/SPEC.md"
PROFILE = "tessera-canonical-v1"
EXTENSION = "tessera_exchange"
MAX_FILE_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 16 * MAX_FILE_BYTES
MAX_ENTRIES = 1000
RESERVED = {"index.md", "log.md"}
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\s]+)\)")


class ExchangeError(ValueError):
    """An explicit safety, ambiguity or supported-profile boundary."""


class SafetyError(ExchangeError):
    """A bundle path would cross the supported safety boundary."""


class _Loader(yaml.SafeLoader):
    pass


# Do not let YAML 1.1 coerce authored timestamps or on/off/yes/no strings.
_Loader.yaml_implicit_resolvers = {
    char: [(tag, rx) for tag, rx in rules if tag not in {
        "tag:yaml.org,2002:timestamp", "tag:yaml.org,2002:bool"
    }]
    for char, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$"), list("tTfF"))


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ExchangeError("Frontmatter requires unique string keys")
        result[key] = loader.construct_object(value_node)
    return result


_Loader.add_constructor("tag:yaml.org,2002:map", _mapping)


def _json_value(value, depth=0):
    if depth > 40:
        raise ExchangeError("Metadata nesting exceeds 40 levels")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            _json_value(item, depth + 1)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _json_value(item, depth + 1)
        return
    raise ExchangeError("Only finite JSON-compatible metadata is supported by exchange plans")


def _parse(raw: str, *, required=True) -> Tuple[Dict[str, Any], str]:
    if "\x00" in raw:
        raise ExchangeError("NUL/binary content is unsupported")
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        if required:
            raise ExchangeError("Concept has no YAML frontmatter")
        return {}, raw
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ExchangeError("Unterminated YAML frontmatter")
    fm = "".join(lines[1:end])
    # Reject aliases before construction: unknown values are inert, not an
    # opportunity for exponential expansion, recursive objects or custom tags.
    for count, token in enumerate(yaml.scan(fm)):
        if count > 50000 or isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)):
            raise ExchangeError("YAML aliases/anchors or oversized metadata require review")
    obj = yaml.load(fm, Loader=_Loader)
    if not isinstance(obj, dict):
        raise ExchangeError("Frontmatter must be a mapping")
    _json_value(obj)
    return obj, "".join(lines[end + 1:])


def _dump(fm, body):
    return "---\n" + yaml.safe_dump(fm, sort_keys=True, allow_unicode=True) + "---\n" + body


def _safe_path(path: str) -> str:
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise SafetyError("Unsafe bundle path")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or path != pure.as_posix() or ":" in pure.parts[0]:
        raise SafetyError("Unsafe bundle path")
    return path


def _link_path(current: str, target: str) -> Optional[str]:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None  # External URLs and anchors are inert; never fetched.
    decoded = unquote(parsed.path)
    base = "" if decoded.startswith("/") else posixpath.dirname(current)
    normalized = posixpath.normpath(posixpath.join(base, decoded.lstrip("/")))
    return _safe_path(normalized)


def _scan(root: Path):
    if root.is_symlink() or not root.is_dir():
        raise ExchangeError("Bundle must be a real directory, not a symlink")
    # Reject symlink ancestors as well as children. No path from the bundle is
    # followed outside the selected physical root, including directories.
    if any(p.is_symlink() for p in root.absolute().parents):
        raise ExchangeError("Bundle ancestors must not be symlinks")
    docs, skipped, errors = {}, [], []
    count = total = 0
    for directory, dirs, files_ in os.walk(root, followlinks=False):
        dirs.sort()
        for name in list(dirs):
            count += 1
            path = Path(directory) / name
            if path.is_symlink():
                errors.append({"path": path.relative_to(root).as_posix(), "code": "symlink"})
                dirs.remove(name)
        for name in sorted(files_):
            count += 1
            if count > MAX_ENTRIES:
                raise ExchangeError("Bundle entry limit exceeded")
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            _safe_path(relative)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                errors.append({"path": relative, "code": "not_regular_file"})
                continue
            if path.suffix != ".md":
                skipped.append({"path": relative, "reason": "non_markdown_not_read"})
                continue
            if info.st_size > MAX_FILE_BYTES:
                errors.append({"path": relative, "code": "file_size_limit"})
                continue
            total += info.st_size
            if total > MAX_BUNDLE_BYTES:
                raise ExchangeError("Bundle byte limit exceeded")
            # O_NOFOLLOW closes the final-component race; changing directory
            # trees during a plan is unsupported, as documented.
            try:
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
                with os.fdopen(fd, "rb") as handle:
                    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                        raise ExchangeError("Source changed to a special file")
                    data = handle.read(MAX_FILE_BYTES + 1)
                if len(data) > MAX_FILE_BYTES:
                    raise ExchangeError("Source grew beyond the file size limit")
                docs[relative] = data.decode("utf-8")
            except (OSError, UnicodeError, ExchangeError) as exc:
                errors.append({"path": relative, "code": "unreadable_source", "detail": str(exc)})
        if count > MAX_ENTRIES:
            raise ExchangeError("Bundle entry limit exceeded")
    return docs, skipped, errors


def _supported_links(body):
    # Keep the exchange prototype honest about its bounded Markdown subset.
    # Examples in fenced/inline code do not assert concept relationships.
    prose = []
    fence = None
    for line in body.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            prose.append(line)
    text = re.sub(r"(`+).*?\1", "", "".join(prose))
    if re.search(r"(?<!!)\[(?!\^)[^\]\n]+\][ \t]*\[(?!\^)[^\]\n]*\]", text):
        raise ExchangeError("Reference-style links require a full Markdown adapter")
    for target in re.findall(r"(?<!!)\[[^\]\n]+\]\(([^)\n]*)\)", text):
        if not target or any(c.isspace() for c in target) or any(c in target for c in "()<>"):
            raise ExchangeError("Complex Markdown links require a full Markdown adapter")
    return LINK.findall(text)


def _offset_timestamp(value):
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def _optional_diagnostics(fm):
    warnings = []
    def timestamp(path, value):
        if value is not None and not _offset_timestamp(value):
            warnings.append({"code": "timestamp_requires_offset", "field": path})
    timestamp("stale_after", fm.get("stale_after"))
    for family in ("generated", "verified"):
        values = fm.get(family, [])
        values = values if isinstance(values, list) else [values]
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("by"), str):
                warnings.append({"code": "malformed_actor_event", "field": family})
            else:
                timestamp(family + ".at", value.get("at"))
    for source in fm.get("sources", []) if isinstance(fm.get("sources", []), list) else []:
        if isinstance(source, dict):
            timestamp("sources.last_modified", source.get("last_modified"))
            for bound, value in (source.get("usage_window") or {}).items() if isinstance(source.get("usage_window"), dict) else []:
                timestamp("sources.usage_window." + bound, value)
    if isinstance(fm.get("usage_window"), dict):
        for bound, value in fm["usage_window"].items():
            timestamp("usage_window." + bound, value)
    if fm.get("status", "stable") not in ("draft", "stable", "deprecated"):
        warnings.append({"code": "unknown_status", "field": "status"})
    if any(k in fm for k in ("executor", "attester", "computation", "runtime")):
        warnings.append({"code": "attestation_not_executed", "field": "computation"})
    return warnings


def knowledge_signals(frontmatter):
    """Advisory source claims only, never authority/access-control grants."""
    fm = frontmatter or {}
    verified = fm.get("verified", [])
    verified = [verified] if isinstance(verified, dict) else verified
    events = [event for event in verified if isinstance(event, dict)] if isinstance(verified, list) else []
    valid = [event for event in events if isinstance(event.get("by"), str) and _offset_timestamp(event.get("at"))]
    tier = "unverified"
    if valid:
        tier = "human-reviewed" if any(e["by"].startswith("human:") for e in valid) else "machine-confirmed"
    return {"verified": events, "trust_tier": tier, "status": fm.get("status", "stable"),
            "stale_after": fm.get("stale_after"), "attestation": "NOT_EXECUTED",
            "trust_is_authenticated": False}


def _canonical_payload(canonical):
    payload = canonical.to_dict()
    payload["temporal"]["indexed_at"] = ""  # rebuildable runtime state, not source semantics
    _json_value(payload)
    return payload


def _restore(payload):
    """Restore only this exact profile, never instantiate arbitrary classes."""
    if not isinstance(payload, dict) or (type(payload.get("schema_version")) is not int or payload["schema_version"] != 1):
        raise ExchangeError("Unsupported canonical extension schema")
    expected = {f.name for f in fields(CanonicalMetadata)}
    # The independently optional lineage extension omits an absent value from
    # legacy canonical JSON. All original profile fields remain mandatory and
    # unknown fields remain rejected rather than silently dropped.
    optional = {f.name for f in fields(CanonicalMetadata)
                if f.name == "lineage" and f.default is None}
    if set(payload) - expected or expected - set(payload) - optional:
        raise ExchangeError("Canonical extension fields differ from the v1 contract")
    value = copy.deepcopy(payload)
    types = {"identity": IdentityMetadata, "classification": ClassificationMetadata,
             "scope": ScopeMetadata, "temporal": TemporalMetadata, "quality": QualityMetadata}
    try:
        for name, cls in types.items():
            if not isinstance(value[name], dict) or set(value[name]) != {f.name for f in fields(cls)}:
                raise ExchangeError(f"Malformed canonical {name}")
            value[name] = cls(**value[name])
        value["source"]["span"] = SourceSpan(**value["source"]["span"])
        value["source"] = SourceMetadata(**value["source"])
        value["relations"] = [RelationMetadata(**item) for item in value["relations"]]
        if value.get("lineage") is not None:
            lineage_type = getattr(canonical_types, "LineageMetadata", None)
            lineage = value["lineage"]
            if (lineage_type is None or not isinstance(lineage, dict)
                    or set(lineage) != {f.name for f in fields(lineage_type)}
                    or not isinstance(lineage.get("source_episode_id"), str)
                    or not lineage["source_episode_id"]
                    or not isinstance(lineage.get("supporting_turns"), list)
                    or any(type(p) is not int or p < 1 for p in lineage["supporting_turns"])
                    or (lineage.get("temporal_position") is not None
                        and type(lineage["temporal_position"]) is not int)
                    or (lineage.get("episode_source") is not None
                        and not isinstance(lineage["episode_source"], dict))
                    or not isinstance(lineage.get("source_evidence"), list)
                    or any(not isinstance(record, dict) for record in lineage["source_evidence"])):
                raise ExchangeError("Malformed canonical lineage")
            value["lineage"] = lineage_type(**lineage)
        canonical = CanonicalMetadata(**value)
    except (TypeError, KeyError) as exc:
        raise ExchangeError("Malformed canonical extension") from exc
    if not isinstance(canonical.identity.id, str) or not canonical.identity.id.strip():
        raise ExchangeError("Canonical ID must be a non-empty string")
    if not isinstance(canonical.identity.name, str):
        raise ExchangeError("Canonical name must be a string")
    if canonical.classification.drawer not in {None, "facts", "preferences", "insights"}:
        raise ExchangeError("Unknown canonical drawer")
    if not isinstance(canonical.raw_frontmatter, dict) or not isinstance(canonical.metadata_origin, dict):
        raise ExchangeError("Canonical raw metadata and origins must be mappings")
    if not all(isinstance(v, str) for v in canonical.metadata_origin.values()):
        raise ExchangeError("Canonical metadata origins must be strings")
    required_strings = [canonical.classification.kind, canonical.classification.document_type,
                        canonical.source.document_id, canonical.source.path, canonical.source.format,
                        canonical.source.document_hash, canonical.source.content_hash, canonical.temporal.indexed_at]
    optional_strings = [canonical.scope.level, canonical.scope.path, canonical.scope.harness,
                        canonical.temporal.observed_at, canonical.temporal.recorded_at,
                        canonical.temporal.valid_from, canonical.temporal.valid_until,
                        canonical.state_key, canonical.superseded_at]
    if not all(isinstance(v, str) for v in required_strings) or not all(v is None or isinstance(v, str) for v in optional_strings):
        raise ExchangeError("Malformed canonical string fields")
    if canonical.utility is not None and (type(canonical.utility) not in (int, float) or not math.isfinite(canonical.utility)):
        raise ExchangeError("Canonical utility must be a finite number")
    for line in (canonical.source.span.start_line, canonical.source.span.end_line):
        if line is not None and (type(line) is not int or line < 1):
            raise ExchangeError("Canonical source spans use positive line numbers")
    for relation in canonical.relations:
        if not all(isinstance(v, str) and v for v in (relation.type, relation.target, relation.origin)):
            raise ExchangeError("Malformed canonical relation")
    return canonical


@dataclass
class ExchangeRecord:
    canonical: CanonicalMetadata
    body: str
    path: str
    external_frontmatter: Optional[Dict[str, Any]] = None
    extension_extra: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {"path": self.path, "canonical": _canonical_payload(self.canonical),
                "body": self.body, "external_frontmatter": self.external_frontmatter,
                "extension_extra": self.extension_extra or {},
                "okf_signals": knowledge_signals(self.external_frontmatter)}


@dataclass
class ImportPlan:
    records: List[ExchangeRecord]
    report: Dict[str, Any]
    auxiliary: Dict[str, str]

    def to_dict(self):
        return {"report": self.report, "records": [r.to_dict() for r in self.records],
                "auxiliary": self.auxiliary}


def plan_import(bundle, *, namespace: str) -> ImportPlan:
    """Read a bounded local bundle into canonical candidates without writes.

    An accepted candidate is parseable, NOT admitted to a user's memory store.
    Diagnostics distinguish spec conformance, supported mapping and safety.
    """
    if not isinstance(namespace, str) or not namespace.strip():
        raise ExchangeError("An explicit stable bundle namespace is required")
    raw_docs, skipped, safety = _scan(Path(bundle))
    records, diagnostics, auxiliary = [], [], {}
    external_valid = True
    external_incomplete = bool(safety)
    seen = 0
    for path, raw in sorted(raw_docs.items()):
        if PurePosixPath(path).name in RESERVED:
            auxiliary[path] = raw
            # Reserved files do not become memories. Validate the structural
            # MUSTs, while leaving prose and listing completeness advisory.
            try:
                fm, body = _parse(raw, required=False)
                if PurePosixPath(path).name == "index.md":
                    if fm and (path != "index.md" or set(fm) != {"okf_version"}):
                        raise ExchangeError("Only root index.md may carry okf_version frontmatter")
                    if not re.search(r"^#+ .+", body, re.M):
                        raise ExchangeError("Index requires a section heading")
                else:
                    if fm:
                        raise ExchangeError("Log files have no frontmatter")
                    for heading in re.findall(r"^## (.+)$", body, re.M):
                        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", heading):
                            raise ExchangeError("Log date headings must be YYYY-MM-DD")
                        datetime.strptime(heading, "%Y-%m-%d")
            except (ValueError, yaml.YAMLError, RecursionError) as exc:
                external_valid = False
                diagnostics.append({"path": path, "code": "invalid_reserved_document", "detail": str(exc)})
            continue
        seen += 1
        try:
            fm, body = _parse(raw)
            if not isinstance(fm.get("type"), str) or not fm["type"].strip():
                raise ExchangeError("type must be a non-empty string")
        except (ValueError, yaml.YAMLError, RecursionError) as exc:
            external_valid = False
            diagnostics.append({"path": path, "code": "invalid_concept", "detail": str(exc)})
            continue
        diagnostics.extend({"path": path, **item} for item in _optional_diagnostics(fm))
        try:
            extra = {}
            if EXTENSION in fm:
                extension = fm[EXTENSION]
                if not isinstance(extension, dict) or extension.get("profile") != PROFILE:
                    raise ExchangeError("Unrecognized tessera_exchange namespace; preserved but not interpreted")
                canonical = _restore(extension.get("canonical"))
                outer = {k: v for k, v in fm.items() if k != EXTENSION}
                if extension.get("external_frontmatter_hash") != compute_sha256(json.dumps(outer, sort_keys=True, ensure_ascii=False)):
                    raise ExchangeError("Extension metadata hash mismatch; changed outer fields require review")
                if canonical.source.content_hash != compute_sha256(body):
                    raise ExchangeError("Extension body hash mismatch; stale metadata requires review")
                extra = {k: v for k, v in extension.items() if k not in {"profile", "canonical", "external_frontmatter_hash"}}
            else:
                resource = fm.get("resource")
                if not isinstance(resource, str) or not resource.strip():
                    raise ExchangeError("No stable identity evidence: supply a reviewed tessera_exchange ID")
                identity = "okf_" + compute_sha256(namespace + "\0" + resource)[:32]
                title = fm.get("title", PurePosixPath(path).stem)
                if not isinstance(title, str):
                    raise ExchangeError("Non-string title cannot be mapped losslessly")
                tags = fm.get("tags", [])
                if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                    raise ExchangeError("Non-string tags cannot be mapped losslessly")
                canonical = CanonicalMetadata(
                    identity=IdentityMetadata(identity, title),
                    classification=ClassificationMetadata("facts", "factual", "memory"),
                    scope=ScopeMetadata("project", "./**"),
                    source=SourceMetadata("okf_doc_" + compute_sha256(identity)[:32], path, "markdown",
                                          SourceSpan(1, max(1, len(raw.splitlines()))), compute_sha256(raw), compute_sha256(body)),
                    raw_frontmatter={"tags": tags, "okf": copy.deepcopy(fm)},
                    metadata_origin={"id": "adapter:namespace+resource", "name": "explicit" if "title" in fm else "inferred",
                                     "classification": "adapter:generic_concept", "source": "adapter:source_bytes"},
                )
            path_values = [fm.get("resource"), fm.get("computation")]
            for key in ("executor", "attester"):
                if isinstance(fm.get(key), dict):
                    path_values.append(fm[key].get("resource"))
            if isinstance(fm.get("sources"), list):
                path_values.extend(v.get("resource") for v in fm["sources"] if isinstance(v, dict))
            for target in _supported_links(body) + [v for v in path_values if isinstance(v, str)]:
                _link_path(path, target)  # diagnose traversal, never follow it
            records.append(ExchangeRecord(canonical, body, path,
                                          {k: v for k, v in fm.items() if k != EXTENSION}, extra))
        except (ValueError, TypeError, AttributeError) as exc:
            if isinstance(exc, SafetyError):
                safety.append({"path": path, "code": "unsafe_path_reference"})
            diagnostics.append({"path": path, "code": "mapping_requires_review", "detail": str(exc)})
    # Resolve only explicit Markdown links, retaining broken targets as inert
    # provenance. Core ranking and link parsing are never changed.
    by_path = {r.path: r for r in records}
    ids = {}
    for record in records:
        ids.setdefault(record.canonical.identity.id, []).append(record.path)
    duplicates = {key for key, paths in ids.items() if len(paths) > 1}
    for record in records:
        if record.canonical.identity.id in duplicates:
            diagnostics.append({"path": record.path, "code": "ambiguous_identity", "detail": "Multiple concepts share identity evidence"})
        elif EXTENSION not in _parse(raw_docs[record.path])[0]:
            targets = set()
            for target in _supported_links(record.body):
                resolved = _link_path(record.path, target)
                if resolved in by_path and by_path[resolved].canonical.identity.id not in duplicates:
                    targets.add(by_path[resolved].canonical.identity.id)
                elif resolved:
                    diagnostics.append({"path": record.path, "code": "unresolved_link", "target": target})
            record.canonical.relations = [RelationMetadata("related_to", target, "explicit:okf_link") for target in sorted(targets)]
    records = [r for r in records if r.canonical.identity.id not in duplicates]
    report = {"profile": PROFILE, "spec_version": "0.2", "spec_revision": SPEC_REVISION,
              "spec_url": SPEC_URL, "namespace": namespace, "concepts_seen": seen,
              "accepted_candidates": len(records), "review_required": seen - len(records),
              "external_format": ("INCOMPLETE" if external_incomplete else "PASS") if external_valid else "FAIL",
              "external_validation_scope": "local pinned-spec structural checks; not upstream certification",
              "mapping": "PASS" if len(records) == seen and external_valid and not safety else "REVIEW",
              "security": "PASS" if not safety else "FAIL", "security_diagnostics": safety,
              "diagnostics": diagnostics, "skipped": skipped, "lossy_fields": [],
              "persistence": "NOT_PERFORMED; admission/write integration remains required",
              "execution": "DISABLED", "network": "DISABLED", "decision": "ITERATE"}
    return ImportPlan(records, report, auxiliary)


def native_preview(record: ExchangeRecord) -> str:
    """Review-only Markdown projection, never an admission/write operation."""
    c = record.canonical
    fm = copy.deepcopy(c.raw_frontmatter)
    fm.update({"id": c.identity.id, "name": c.identity.name, "drawer": c.classification.drawer,
               "kind": c.classification.kind, "document_type": c.classification.document_type,
               "scope": {"level": c.scope.level, "path": c.scope.path, "harness": c.scope.harness},
               "confidence": c.quality.confidence, "authority": c.quality.authority,
               "state_key": c.state_key, "superseded_at": c.superseded_at, "utility": c.utility,
               "active_connections": [{"target_memory_id": r.target, "relation_type": r.type} for r in c.relations],
               "okf_exchange_provenance": {"source": _canonical_payload(c)["source"], "spec_revision": SPEC_REVISION}})
    for key in ("observed_at", "valid_from", "valid_until", "recorded_at"):
        fm[key] = getattr(c.temporal, key)
    return _dump(fm, record.body)


def export_records(records, *, auxiliary=None):
    """Return a deterministic path -> text export plan, without writing files."""
    files_, identities = {}, set()
    for record in sorted(records, key=lambda item: item.path):
        path = _safe_path(record.path)
        if not path.endswith(".md") or PurePosixPath(path).name in RESERVED or path in files_:
            raise ExchangeError("Export concept path is reserved, duplicated or not Markdown")
        canonical = _canonical_payload(record.canonical)
        _restore(canonical)
        if canonical["identity"]["id"] in identities:
            raise ExchangeError("Duplicate canonical identity")
        identities.add(canonical["identity"]["id"])
        if canonical["source"]["content_hash"] != compute_sha256(record.body):
            raise ExchangeError("Body differs from canonical content hash")
        fm = copy.deepcopy(record.external_frontmatter) if record.external_frontmatter is not None else {
            "type": "TESSERA Memory", "title": record.canonical.identity.name}
        if EXTENSION in fm:
            raise ExchangeError("Cannot overwrite an unknown exchange namespace")
        if not isinstance(fm.get("type"), str) or not fm["type"].strip():
            raise ExchangeError("Export requires non-empty type")
        fm[EXTENSION] = {**(record.extension_extra or {}), "profile": PROFILE, "canonical": canonical,
                         "external_frontmatter_hash": compute_sha256(json.dumps(fm, sort_keys=True, ensure_ascii=False))}
        files_[path] = _dump(fm, record.body)
    for path, text in sorted((auxiliary or {}).items()):
        _safe_path(path)
        if PurePosixPath(path).name not in RESERVED or path in files_:
            raise ExchangeError("Invalid auxiliary export path")
        files_[path] = text
    return {"files": dict(sorted(files_.items())), "report": {
        "profile": PROFILE, "spec_revision": SPEC_REVISION, "concepts_written": len(identities),
        "native_fields": ["type", "title", "original OKF frontmatter and body"],
        "extended_fields": ["canonical metadata", "typed relations and origin", "source/evidence hashes", "temporal validity"],
        "derived_fields_omitted": ["temporal.indexed_at"], "lossy_fields": [],
        "file_hashes": {p: compute_sha256(t) for p, t in sorted(files_.items())},
        "validation": "LOCAL_STRUCTURAL_CHECKS; re-import required", "decision": "ITERATE",
        "persistence": "NOT_PERFORMED", "execution": "DISABLED", "network": "DISABLED"}}


def plan_native_export(directory):
    """Explicitly selected native Markdown only; no config/store discovery."""
    root = Path(directory)
    docs, skipped, safety = _scan(root)
    if safety:
        raise ExchangeError("Unsafe/unreadable native inputs: " + json.dumps(safety))
    records = []
    for path, raw in sorted(docs.items()):
        if PurePosixPath(path).name in RESERVED:
            raise ExchangeError("Native index.md/log.md requires an explicit non-reserved export path")
        _, body = _parse(raw, required=False)
        canonical = parse_and_normalize(raw, str(root / path), str(root))
        canonical.temporal.indexed_at = ""
        records.append(ExchangeRecord(canonical, body, path))
    result = export_records(records)
    result["report"]["skipped"] = skipped
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experimental offline OKF plans; no import persistence or execution")
    parser.add_argument("command", choices=("validate", "plan", "export-native"))
    parser.add_argument("directory")
    parser.add_argument("--namespace", help="Stable user-selected bundle identity namespace")
    args = parser.parse_args(argv)
    try:
        if args.command == "export-native":
            payload = plan_native_export(args.directory)
            code = 0
        else:
            if args.command == "plan" and not args.namespace:
                raise ExchangeError("plan requires an explicit --namespace")
            plan = plan_import(args.directory, namespace=args.namespace or "validation-only")
            payload = plan.report if args.command == "validate" else plan.to_dict()
            code = 0 if plan.report["mapping"] == "PASS" else 2
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return code
    except (ValueError, OSError, yaml.YAMLError, RecursionError) as exc:
        print(json.dumps({"error": str(exc), "decision": "ITERATE", "persistence": "NOT_PERFORMED"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
