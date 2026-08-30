"""Canonical Metadata Model and Normalization for TESSERA.

Fulfills F2 (Canonical Metadata Model), F3 (Document Classification),
F4 (Parser without Frontmatter), F5 (Stable Identity), and F7 (Explicit Relations).
"""

from dataclasses import dataclass, field, asdict
import datetime
import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import yaml


@dataclass
class IdentityMetadata:
    id: str
    name: str


@dataclass
class ClassificationMetadata:
    drawer: str  # facts | preferences | insights
    kind: str    # e.g. factual, preference, procedural_anchor
    document_type: str  # memory | harness_instructions | skill_instructions | project_context | decision_record | experiment_record | report | reference


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
    format: str  # markdown | text
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
    origin: str  # explicit | inferred | generated


@dataclass
class CanonicalMetadata:
    schema_version: int = 1
    identity: IdentityMetadata = field(default_factory=lambda: IdentityMetadata("", ""))
    classification: ClassificationMetadata = field(default_factory=lambda: ClassificationMetadata("facts", "factual", "memory"))
    scope: ScopeMetadata = field(default_factory=ScopeMetadata)
    source: SourceMetadata = field(default_factory=lambda: SourceMetadata("", "", "markdown"))
    temporal: TemporalMetadata = field(default_factory=TemporalMetadata)
    quality: QualityMetadata = field(default_factory=QualityMetadata)
    relations: List[RelationMetadata] = field(default_factory=list)
    metadata_origin: Dict[str, str] = field(default_factory=dict)  # field_name -> explicit | inferred | default
    
    # Reserved optional fields
    state_key: Optional[str] = None
    superseded_at: Optional[str] = None
    utility: Optional[float] = None
    
    # Preserve other fields from original frontmatter
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert canonical metadata to a clean nested dictionary structure."""
        return asdict(self)


def compute_sha256(text: str) -> str:
    """Computes the SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_and_normalize(raw_text: str, filepath: str, storage_dir: str) -> CanonicalMetadata:
    """
    Parses raw text (with or without frontmatter) and builds a fully normalized
    CanonicalMetadata model deterministically. Fulfills F4, F5, F7.
    """
    # 1. Parse markdown frontmatter if present
    frontmatter, body = _split_markdown(raw_text)
    
    # Get relative path for stable hash and ID generation
    rel_path = os.path.relpath(filepath, storage_dir)
    rel_path_posix = rel_path.replace(os.sep, "/")
    filename = os.path.basename(filepath)
    filename_lower = filename.lower()
    
    # Hashes (F6 / F5)
    doc_hash = compute_sha256(raw_text)
    body_hash = compute_sha256(body)
    
    # Stable Document ID (F5)
    doc_id = f"doc_{compute_sha256(rel_path_posix)[:12]}"
    
    # Initialize origin tracking dictionary
    origin: Dict[str, str] = {}
    
    # A. IDENTITY (F5)
    # Rules: Explicit ID -> frontmatter ID -> inferred ID from file layout.
    explicit_id = frontmatter.get("id") or frontmatter.get("memory_id")
    if explicit_id:
        mem_id = str(explicit_id).strip()
        origin["id"] = "explicit"
    else:
        # Infer stable ID based on relative path structure (F5)
        # e.g., learnings/openai-tts -> learnings/openai-tts
        slug = os.path.splitext(rel_path_posix)[0]
        # Clean up any potential double slashes or leading dots
        slug = re.sub(r'^\.+/', '', slug)
        slug = re.sub(r'/+', '/', slug)
        mem_id = slug
        origin["id"] = "inferred"
        
    explicit_name = frontmatter.get("name") or frontmatter.get("title")
    if explicit_name:
        name = str(explicit_name).strip()
        origin["name"] = "explicit"
    else:
        # Base name without extension
        name = os.path.splitext(filename)[0]
        origin["name"] = "inferred"
        
    identity = IdentityMetadata(id=mem_id, name=name)
    
    # B. CLASSIFICATION (F3)
    # Document Type Inference
    explicit_doc_type = frontmatter.get("document_type")
    if explicit_doc_type:
        doc_type = str(explicit_doc_type).strip()
        origin["document_type"] = "explicit"
    else:
        if filename_lower in ("claude.md", "gemini.md", "copilot-instructions.md"):
            doc_type = "harness_instructions"
        elif filename_lower == "skill.md" or filename_lower.startswith("sk_"):
            doc_type = "skill_instructions"
        elif "decision" in filename_lower or filename_lower.startswith("adr"):
            doc_type = "decision_record"
        elif "experiment" in filename_lower:
            doc_type = "experiment_record"
        elif "report" in filename_lower:
            doc_type = "report"
        elif filename_lower == "readme.md":
            doc_type = "project_context"
        else:
            doc_type = "memory"
        origin["document_type"] = "inferred"
        
    # Kind (F3)
    explicit_kind = frontmatter.get("kind") or frontmatter.get("node_type") or frontmatter.get("memory_type") or frontmatter.get("type")
    if explicit_kind:
        kind = str(explicit_kind).strip()
        origin["kind"] = "explicit"
    else:
        if doc_type == "skill_instructions":
            kind = "procedural_anchor"
        elif doc_type == "harness_instructions":
            kind = "preference"
        else:
            kind = "factual"
        origin["kind"] = "inferred"
        
    # Semantic Drawer (F3 / Facts, Preferences, Insights)
    explicit_drawer = frontmatter.get("drawer")
    if explicit_drawer and str(explicit_drawer).strip() in ("facts", "preferences", "insights"):
        drawer = str(explicit_drawer).strip()
        origin["drawer"] = "explicit"
    else:
        # Resolve drawer based on kind
        if kind == "procedural_anchor":
            drawer = "insights"
        elif kind == "preference":
            drawer = "preferences"
        else:
            drawer = "facts"
        origin["drawer"] = "inferred"
        
    classification = ClassificationMetadata(drawer=drawer, kind=kind, document_type=doc_type)
    
    # C. SCOPE (F3)
    explicit_scope_level = None
    explicit_scope_path = None
    explicit_scope_harness = None
    
    if isinstance(frontmatter.get("scope"), dict):
        scope_dict = frontmatter["scope"]
        explicit_scope_level = scope_dict.get("level")
        explicit_scope_path = scope_dict.get("path")
        explicit_scope_harness = scope_dict.get("harness")
    elif isinstance(frontmatter.get("scope"), str):
        # Flattened scope string
        explicit_scope_path = frontmatter["scope"]
        
    if explicit_scope_level:
        level = str(explicit_scope_level)
        origin["scope.level"] = "explicit"
    else:
        level = "project" if rel_path_posix.count("/") == 0 else "folder"
        origin["scope.level"] = "default"
        
    if explicit_scope_path:
        path = str(explicit_scope_path)
        origin["scope.path"] = "explicit"
    else:
        # Default to root or directory pattern
        if level == "project":
            path = "./**"
        else:
            path = f"./{os.path.dirname(rel_path_posix)}/**"
        origin["scope.path"] = "default"
        
    explicit_harness = explicit_scope_harness or frontmatter.get("harness")
    if explicit_harness:
        harness = str(explicit_harness)
        origin["scope.harness"] = "explicit"
    else:
        if filename_lower == "claude.md":
            harness = "claude"
        elif filename_lower == "gemini.md":
            harness = "gemini"
        elif filename_lower == "copilot-instructions.md":
            harness = "copilot"
        else:
            harness = None
        origin["scope.harness"] = harness and "inferred" or "default"
        
    scope = ScopeMetadata(level=level, path=path, harness=harness)
    
    # D. SOURCE (F4 / F6)
    lines_count = len(raw_text.splitlines())
    span = SourceSpan(start_line=1, end_line=lines_count if lines_count > 0 else 1)
    
    # Format
    file_format = "markdown" if filename_lower.endswith((".md", ".markdown")) else "text"
    
    source = SourceMetadata(
        document_id=doc_id,
        path=rel_path_posix,
        format=file_format,
        span=span,
        document_hash=doc_hash,
        content_hash=body_hash
    )
    origin["source.document_id"] = "inferred"
    origin["source.path"] = "explicit"
    origin["source.format"] = "inferred"
    origin["source.span"] = "inferred"
    origin["source.document_hash"] = "inferred"
    origin["source.content_hash"] = "inferred"
    
    # E. TEMPORAL
    observed_at = frontmatter.get("observed_at")
    if observed_at:
        observed_at = str(observed_at)
        origin["temporal.observed_at"] = "explicit"
    else:
        origin["temporal.observed_at"] = "default"
        
    valid_from = frontmatter.get("valid_from")
    if valid_from:
        valid_from = str(valid_from)
        origin["temporal.valid_from"] = "explicit"
    else:
        origin["temporal.valid_from"] = "default"
        
    valid_until = frontmatter.get("valid_until")
    if valid_until:
        valid_until = str(valid_until)
        origin["temporal.valid_until"] = "explicit"
    else:
        origin["temporal.valid_until"] = "default"
        
    recorded_at = frontmatter.get("recorded_at") or frontmatter.get("created_at") or frontmatter.get("date")
    if recorded_at:
        recorded_at = str(recorded_at)
        origin["temporal.recorded_at"] = "explicit"
    else:
        origin["temporal.recorded_at"] = "default"
        
    # Always set current index time
    indexed_at = datetime.datetime.now().isoformat()
    origin["temporal.indexed_at"] = "inferred"
    
    temporal = TemporalMetadata(
        observed_at=observed_at,
        valid_from=valid_from,
        valid_until=valid_until,
        recorded_at=recorded_at,
        indexed_at=indexed_at
    )
    
    # F. QUALITY
    confidence = frontmatter.get("confidence")
    if confidence is not None:
        origin["quality.confidence"] = "explicit"
    else:
        confidence = "high"
        origin["quality.confidence"] = "default"
        
    authority = frontmatter.get("authority")
    if authority is not None:
        origin["quality.authority"] = "explicit"
    else:
        origin["quality.authority"] = "default"
        
    quality = QualityMetadata(confidence=confidence, authority=authority)
    
    # G. RELATIONS (F7 - Explicit Relations first)
    relations: List[RelationMetadata] = []
    
    # 1. Relations from frontmatter Connections
    # Parse connections
    active_conns = frontmatter.get("active_connections") or frontmatter.get("connections") or []
    for conn in active_conns:
        if isinstance(conn, dict):
            target = conn.get("target_memory_id") or conn.get("target")
            rel_type = conn.get("relation_type") or conn.get("type") or "related_to"
            if target:
                relations.append(RelationMetadata(type=str(rel_type), target=str(target), origin="explicit"))
        elif isinstance(conn, str) and ":" in conn:
            # Format "target:type"
            target, rel_type = conn.split(":", 1)
            relations.append(RelationMetadata(type=rel_type, target=target, origin="explicit"))
            
    # Frontmatter related_to
    related_to = frontmatter.get("related_to")
    if related_to:
        if isinstance(related_to, list):
            for target in related_to:
                relations.append(RelationMetadata(type="related_to", target=str(target), origin="explicit"))
        elif isinstance(related_to, str):
            relations.append(RelationMetadata(type="related_to", target=related_to, origin="explicit"))
            
    # 2. Relations from Body [[wikilinks]] (F7)
    wikilink_pattern = re.compile(r"\[\[([a-zA-Z0-9_\-/]+)\]\]")
    for match in wikilink_pattern.finditer(body):
        target = match.group(1)
        relations.append(RelationMetadata(type="related_to", target=target, origin="explicit"))
        
    # Standard markdown links pointing to local markdown files
    md_link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")
    for match in md_link_pattern.finditer(body):
        target_path = match.group(1)
        # Normalize relative path to target ID
        # e.g., ../learnings/foo.md -> learnings/foo
        target_clean = target_path.replace(".md", "")
        # Remove relative dot segments
        target_clean = re.sub(r'^\.+/', '', target_clean)
        target_clean = re.sub(r'/+', '/', target_clean)
        relations.append(RelationMetadata(type="related_to", target=target_clean, origin="explicit"))
        
    # H. RESERVED OPTIONAL FIELDS
    state_key = frontmatter.get("state_key")
    superseded_at = frontmatter.get("superseded_at")
    utility = frontmatter.get("utility")
    if utility is not None:
        try:
            utility = float(utility)
        except ValueError:
            utility = None
            
    return CanonicalMetadata(
        schema_version=1,
        identity=identity,
        classification=classification,
        scope=scope,
        source=source,
        temporal=temporal,
        quality=quality,
        relations=relations,
        metadata_origin=origin,
        state_key=state_key,
        superseded_at=superseded_at,
        utility=utility,
        raw_frontmatter=frontmatter
    )


def _split_markdown(raw_text: str) -> Tuple[Dict[str, Any], str]:
    """Splits markdown into (frontmatter dictionary, body text)."""
    text = raw_text.strip()
    if not text.startswith("---"):
        return {}, raw_text

    parts = text.split("---", 2)
    if len(parts) >= 3:
        frontmatter_raw = parts[1]
        body = parts[2]
        try:
            frontmatter = yaml.safe_load(frontmatter_raw)
            if isinstance(frontmatter, dict):
                return frontmatter, body
        except Exception:
            pass
    return {}, raw_text
