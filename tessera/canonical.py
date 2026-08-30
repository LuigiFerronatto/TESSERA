"""Canonical Metadata Model and normalization for TESSERA.

The source document remains the source of truth. This module provides a
rebuildable, deterministic normalization layer for Markdown/TXT documents,
including legacy/foreign frontmatter shapes used by existing projects.
"""

from dataclasses import asdict, dataclass, field
import datetime
import hashlib
import os
import posixpath
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml


DRAWERS = {"facts", "preferences", "insights"}
NON_MEMORY_TYPES = {
    "harness_instructions",
    "skill_instructions",
    "project_context",
    "decision_record",
    "experiment_record",
    "report",
    "reference",
}


@dataclass
class IdentityMetadata:
    id: str
    name: str


@dataclass
class ClassificationMetadata:
    drawer: Optional[str]
    kind: str
    document_type: str


@dataclass
class ScopeMetadata:
    level: Optional[str] = None
    path: Optional[str] = None
    harness: Optional[str] = None


@dataclass
class SourceSpan:
    start_line: Optional[int] = None
    end_line: Optional[int] = None


@dataclass
class SourceMetadata:
    document_id: str
    path: str
    format: str
    span: SourceSpan = field(default_factory=SourceSpan)
    document_hash: str = ""
    content_hash: str = ""


@dataclass
class TemporalMetadata:
    observed_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    recorded_at: Optional[str] = None
    indexed_at: str = ""


@dataclass
class QualityMetadata:
    confidence: Optional[Any] = None
    authority: Optional[Any] = None


@dataclass
class RelationMetadata:
    type: str
    target: str
    origin: str


@dataclass
class CanonicalMetadata:
    schema_version: int = 1
    identity: IdentityMetadata = field(default_factory=lambda: IdentityMetadata("", ""))
    classification: ClassificationMetadata = field(
        default_factory=lambda: ClassificationMetadata("facts", "factual", "memory")
    )
    scope: ScopeMetadata = field(default_factory=ScopeMetadata)
    source: SourceMetadata = field(default_factory=lambda: SourceMetadata("", "", "markdown"))
    temporal: TemporalMetadata = field(default_factory=TemporalMetadata)
    quality: QualityMetadata = field(default_factory=QualityMetadata)
    relations: List[RelationMetadata] = field(default_factory=list)
    metadata_origin: Dict[str, str] = field(default_factory=dict)
    state_key: Optional[str] = None
    superseded_at: Optional[str] = None
    utility: Optional[float] = None
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_content_equivalent(self, other: "CanonicalMetadata") -> bool:
        return isinstance(other, CanonicalMetadata) and self.source.content_hash == other.source.content_hash

    def is_semantically_equivalent(self, other: "CanonicalMetadata") -> bool:
        if not isinstance(other, CanonicalMetadata):
            return False
        if self.identity != other.identity or not self.is_content_equivalent(other):
            return False
        if self.classification != other.classification or self.scope != other.scope:
            return False
        if (
            self.temporal.observed_at,
            self.temporal.valid_from,
            self.temporal.valid_until,
            self.temporal.recorded_at,
        ) != (
            other.temporal.observed_at,
            other.temporal.valid_from,
            other.temporal.valid_until,
            other.temporal.recorded_at,
        ):
            return False
        if self.quality != other.quality:
            return False
        if sorted((r.type, r.target, r.origin) for r in self.relations) != sorted(
            (r.type, r.target, r.origin) for r in other.relations
        ):
            return False
        if (self.state_key, self.superseded_at, self.utility) != (
            other.state_key,
            other.superseded_at,
            other.utility,
        ):
            return False
        # Retrieval consumes tags/entities, including values supplied by legacy
        # nested metadata. Compare the effective values, not only top-level YAML.
        return _effective_tags(self.raw_frontmatter) == _effective_tags(other.raw_frontmatter) and _effective_entities(
            self.raw_frontmatter
        ) == _effective_entities(other.raw_frontmatter)

    def is_index_equivalent(self, other: "CanonicalMetadata") -> bool:
        if not isinstance(other, CanonicalMetadata) or not self.is_semantically_equivalent(other):
            return False
        return (
            self.source.document_id,
            self.source.path,
            self.source.format,
            self.source.document_hash,
        ) == (
            other.source.document_id,
            other.source.path,
            other.source.format,
            other.source.document_hash,
        )


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _nested_metadata(frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    value = frontmatter.get("metadata")
    return value if isinstance(value, dict) else {}


def _first(frontmatter: Dict[str, Any], *keys: str) -> Any:
    """Top-level canonical/native values win; nested metadata is compatibility fallback."""
    nested = _nested_metadata(frontmatter)
    for key in keys:
        value = frontmatter.get(key)
        if value is not None:
            return value
    for key in keys:
        value = nested.get(key)
        if value is not None:
            return value
    return None


def _normalize_kind(value: Any) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "fact": "factual",
        "facts": "factual",
        "factual": "factual",
        "preference": "preference",
        "preferences": "preference",
        "learning": "procedural_anchor",
        "insight": "procedural_anchor",
        "insights": "procedural_anchor",
        "procedure": "procedural_anchor",
        "procedural": "procedural_anchor",
        "procedural_anchor": "procedural_anchor",
        "instruction": "instruction",
        "instructions": "instruction",
    }
    return mapping.get(raw, raw)


def _effective_tags(frontmatter: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    raw_tags = _first(frontmatter, "tags")
    if isinstance(raw_tags, str):
        tags.extend(t.strip() for t in raw_tags.split(",") if t.strip())
    elif isinstance(raw_tags, list):
        tags.extend(str(t).strip() for t in raw_tags if str(t).strip())

    nested = _nested_metadata(frontmatter)
    # Preserve the old foreign-frontmatter behavior where useful categorical
    # metadata became searchable facets/tags.
    for key in ("category", "phase", "topic"):
        value = nested.get(key)
        if isinstance(value, str) and value.strip():
            tags.append(value.strip())
        elif isinstance(value, list):
            tags.extend(str(v).strip() for v in value if str(v).strip())
    return sorted(set(tags))


def _effective_entities(frontmatter: Dict[str, Any]) -> List[str]:
    raw = _first(frontmatter, "entities")
    values: List[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("name"):
                values.append(str(item["name"]).strip())
            elif isinstance(item, str) and item.strip():
                values.append(item.strip())
    return sorted(set(values))


def _split_markdown(raw_text: str) -> Tuple[Dict[str, Any], str]:
    """Split YAML frontmatter from body without silently discarding malformed YAML.

    Documents without a frontmatter opener remain valid. If a frontmatter block
    is explicitly present but malformed, raise ValueError: silently treating it
    as absent can change identity, drawer and graph relations.
    """
    # Preserve original body bytes/text as much as possible; do not strip the
    # entire document before locating delimiters.
    lines = raw_text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, raw_text

    closing = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            closing = idx
            break
    if closing is None:
        raise ValueError("Malformed YAML frontmatter: opening '---' has no closing delimiter")

    frontmatter_raw = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    try:
        parsed = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML frontmatter: {exc}") from exc
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError("Malformed YAML frontmatter: root must be a mapping")
    return parsed, body


def _infer_document_type(filename_lower: str) -> str:
    harness_files = {
        "claude.md",
        "agents.md",
        "gemini.md",
        "copilot-instructions.md",
    }
    if filename_lower in harness_files:
        return "harness_instructions"
    if (
        filename_lower == "skill.md"
        or filename_lower.endswith(".skill.md")
        or filename_lower.startswith("sk_")
    ):
        return "skill_instructions"
    if "decision" in filename_lower or filename_lower.startswith("adr"):
        return "decision_record"
    if "experiment" in filename_lower:
        return "experiment_record"
    if "report" in filename_lower:
        return "report"
    if filename_lower == "readme.md":
        return "project_context"
    return "memory"


def parse_and_normalize(
    raw_text: str,
    filepath: str,
    storage_dir: str,
    persistent_id: Optional[str] = None,
    persistent_doc_id: Optional[str] = None,
) -> CanonicalMetadata:
    frontmatter, body = _split_markdown(raw_text)
    nested = _nested_metadata(frontmatter)

    rel_path = os.path.relpath(filepath, storage_dir)
    rel_path_posix = rel_path.replace(os.sep, "/")
    filename = os.path.basename(filepath)
    filename_lower = filename.lower()
    doc_hash = compute_sha256(raw_text)
    body_hash = compute_sha256(body)
    doc_id = persistent_doc_id or f"doc_{compute_sha256(rel_path_posix)[:12]}"
    origin: Dict[str, str] = {}

    explicit_id = frontmatter.get("id") or frontmatter.get("memory_id")
    nested_id = nested.get("id") or nested.get("memory_id")
    if explicit_id is not None:
        mem_id = str(explicit_id).strip()
        origin["id"] = "explicit"
    elif nested_id is not None:
        mem_id = str(nested_id).strip()
        origin["id"] = "explicit"
    elif persistent_id:
        mem_id = persistent_id
        origin["id"] = "system"
    else:
        mem_id = re.sub(r"/+", "/", os.path.splitext(rel_path_posix)[0]).lstrip("./")
        origin["id"] = "inferred"

    explicit_name = _first(frontmatter, "name", "title")
    if explicit_name:
        name = str(explicit_name).strip()
        origin["name"] = "explicit"
    else:
        name = os.path.splitext(filename)[0]
        origin["name"] = "inferred"
    identity = IdentityMetadata(mem_id, name)

    explicit_doc_type = _first(frontmatter, "document_type")
    if explicit_doc_type:
        doc_type = str(explicit_doc_type).strip()
        origin["document_type"] = "explicit"
    else:
        doc_type = _infer_document_type(filename_lower)
        origin["document_type"] = "inferred"

    raw_kind = _first(frontmatter, "kind", "node_type", "memory_type", "type")
    normalized_kind = _normalize_kind(raw_kind)
    if normalized_kind:
        kind = normalized_kind
        origin["kind"] = "explicit"
    else:
        kind = "instruction" if doc_type in {"harness_instructions", "skill_instructions"} else "factual"
        origin["kind"] = "inferred"

    explicit_drawer = _first(frontmatter, "drawer")
    if explicit_drawer and str(explicit_drawer).strip() in DRAWERS:
        drawer: Optional[str] = str(explicit_drawer).strip()
        origin["drawer"] = "explicit"
    elif doc_type in NON_MEMORY_TYPES:
        drawer = None
        origin["drawer"] = "default"
    elif kind == "procedural_anchor":
        drawer = "insights"
        origin["drawer"] = "inferred"
    elif kind == "preference":
        drawer = "preferences"
        origin["drawer"] = "inferred"
    else:
        drawer = "facts"
        origin["drawer"] = "inferred"
    classification = ClassificationMetadata(drawer, kind, doc_type)

    scope_value = frontmatter.get("scope")
    nested_scope = nested.get("scope")
    scope_obj = scope_value if isinstance(scope_value, dict) else nested_scope if isinstance(nested_scope, dict) else {}
    explicit_scope_level = scope_obj.get("level")
    explicit_scope_path = scope_obj.get("path")
    if not explicit_scope_path:
        if isinstance(scope_value, str):
            explicit_scope_path = scope_value
        elif isinstance(nested_scope, str):
            explicit_scope_path = nested_scope
    explicit_scope_harness = scope_obj.get("harness")

    if explicit_scope_level:
        level = str(explicit_scope_level)
        origin["scope.level"] = "explicit"
    else:
        level = "project" if "/" not in rel_path_posix else "folder"
        origin["scope.level"] = "default"
    if explicit_scope_path:
        scope_path = str(explicit_scope_path)
        origin["scope.path"] = "explicit"
    else:
        scope_path = "./**" if level == "project" else f"./{posixpath.dirname(rel_path_posix)}/**"
        origin["scope.path"] = "default"

    explicit_harness = explicit_scope_harness or _first(frontmatter, "harness")
    if explicit_harness:
        harness = str(explicit_harness)
        origin["scope.harness"] = "explicit"
    else:
        harness_map = {
            "claude.md": "claude",
            "gemini.md": "gemini",
            "copilot-instructions.md": "copilot",
        }
        # AGENTS.md is intentionally harness-agnostic: it is normative agent
        # instruction knowledge but not tied to a single vendor/runtime.
        harness = harness_map.get(filename_lower)
        origin["scope.harness"] = "inferred" if harness else "default"
    scope = ScopeMetadata(level, scope_path, harness)

    source = SourceMetadata(
        document_id=doc_id,
        path=rel_path_posix,
        format="markdown" if filename_lower.endswith((".md", ".markdown")) else "text",
        span=SourceSpan(1, max(1, len(raw_text.splitlines()))),
        document_hash=doc_hash,
        content_hash=body_hash,
    )
    for key in (
        "source.document_id",
        "source.path",
        "source.format",
        "source.span",
        "source.document_hash",
        "source.content_hash",
    ):
        origin[key] = "system"

    def temporal_field(*keys: str) -> Optional[str]:
        value = _first(frontmatter, *keys)
        return str(value) if value is not None else None

    temporal = TemporalMetadata(
        observed_at=temporal_field("observed_at"),
        valid_from=temporal_field("valid_from"),
        valid_until=temporal_field("valid_until"),
        recorded_at=temporal_field("recorded_at", "created_at", "date"),
        indexed_at=datetime.datetime.now().isoformat(),
    )
    for attr in ("observed_at", "valid_from", "valid_until", "recorded_at"):
        origin[f"temporal.{attr}"] = "explicit" if getattr(temporal, attr) is not None else "default"
    origin["temporal.indexed_at"] = "system"

    confidence = _first(frontmatter, "confidence")
    authority = _first(frontmatter, "authority")
    quality = QualityMetadata(confidence, authority)
    origin["quality.confidence"] = "explicit" if confidence is not None else "default"
    origin["quality.authority"] = "explicit" if authority is not None else "default"

    relations: List[RelationMetadata] = []
    seen_relations = set()

    def add_relation(rel_type: str, target_id: str, origin_value: str = "explicit") -> None:
        target_norm = str(target_id).replace("\\", "/").strip()
        if not target_norm:
            return
        if target_norm.startswith(("http://", "https://", "mailto:", "ftp:")):
            return
        if target_norm.startswith(("./", "../")) or "/../" in target_norm or "/./" in target_norm:
            target_norm = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path_posix), target_norm))
        target_norm = re.sub(r"^\.+/", "", target_norm.strip("/"))
        target_norm = re.sub(r"/+", "/", target_norm)
        key = (rel_type, target_norm)
        if key not in seen_relations:
            seen_relations.add(key)
            relations.append(RelationMetadata(rel_type, target_norm, origin_value))

    active = _first(frontmatter, "active_connections", "connections") or []
    if isinstance(active, list):
        for conn in active:
            if isinstance(conn, dict):
                target = conn.get("target_memory_id") or conn.get("target")
                rel_type = conn.get("relation_type") or conn.get("type") or "related_to"
                if target:
                    add_relation(str(rel_type), str(target))
            elif isinstance(conn, str):
                if ":" in conn:
                    target, rel_type = conn.split(":", 1)
                    add_relation(rel_type, target)
                else:
                    add_relation("related_to", conn)

    related_to = _first(frontmatter, "related_to")
    if isinstance(related_to, list):
        for target in related_to:
            if isinstance(target, str) and target.strip():
                add_relation("related_to", target)
    elif isinstance(related_to, str):
        add_relation("related_to", related_to)

    for match in re.finditer(r"\[\[([a-zA-Z0-9_\-/.]+)\]\]", body):
        add_relation("related_to", match.group(1))
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", body):
        link_target = match.group(1).split("#", 1)[0].strip()
        if link_target.lower().endswith((".md", ".markdown")):
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel_path_posix), link_target))
            if resolved.endswith(".markdown"):
                resolved = resolved[: -len(".markdown")]
            elif resolved.endswith(".md"):
                resolved = resolved[:-3]
            add_relation("related_to", resolved)

    utility = _first(frontmatter, "utility")
    if utility is not None:
        try:
            utility = float(utility)
        except (TypeError, ValueError):
            utility = None

    # Preserve exactly what the author supplied. Effective compatibility tags
    # are materialized below by the engine adapter, not written back here.
    canonical = CanonicalMetadata(
        schema_version=1,
        identity=identity,
        classification=classification,
        scope=scope,
        source=source,
        temporal=temporal,
        quality=quality,
        relations=relations,
        metadata_origin=origin,
        state_key=_first(frontmatter, "state_key"),
        superseded_at=_first(frontmatter, "superseded_at"),
        utility=utility,
        raw_frontmatter=frontmatter,
    )
    return canonical


# Public compatibility helpers used by the engine's legacy adapter.
def effective_tags(frontmatter: Dict[str, Any]) -> List[str]:
    return _effective_tags(frontmatter)


def effective_entities(frontmatter: Dict[str, Any]) -> List[str]:
    return _effective_entities(frontmatter)
