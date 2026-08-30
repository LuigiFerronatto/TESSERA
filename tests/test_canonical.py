"""Unit tests for the Canonical Metadata Model (TESSERA Foundation v0.1)."""

import os
import pytest
from tessera.canonical import parse_and_normalize, CanonicalMetadata


def test_complete_frontmatter_document():
    raw_text = """---
id: research/voice-ai
name: Voice AI Strategy
document_type: decision_record
kind: procedural_anchor
drawer: insights
scope:
  level: global
  path: "./**"
  harness: claude
recorded_at: "2026-08-20"
confidence: high
authority: 0.9
state_key: "voice.strategy"
utility: 0.95
active_connections:
  - target_memory_id: "research/azure"
    relation_type: "stabilizes_service"
---
# Voice AI Research
This is a voice AI document.
"""
    # Parse and normalize
    meta = parse_and_normalize(raw_text, "/storage/research/voice-ai.md", "/storage")
    
    assert isinstance(meta, CanonicalMetadata)
    assert meta.schema_version == 1
    assert meta.identity.id == "research/voice-ai"
    assert meta.identity.name == "Voice AI Strategy"
    assert meta.classification.drawer == "insights"
    assert meta.classification.kind == "procedural_anchor"
    assert meta.classification.document_type == "decision_record"
    
    assert meta.scope.level == "global"
    assert meta.scope.path == "./**"
    assert meta.scope.harness == "claude"
    
    assert meta.source.path == "research/voice-ai.md"
    assert meta.source.format == "markdown"
    assert meta.source.content_hash != ""
    assert meta.source.document_hash != ""
    
    assert meta.temporal.recorded_at == "2026-08-20"
    assert meta.quality.confidence == "high"
    assert meta.quality.authority == 0.9
    
    # Optional fields
    assert meta.state_key == "voice.strategy"
    assert meta.utility == 0.95
    
    # Relations
    assert len(meta.relations) == 1
    assert meta.relations[0].target == "research/azure"
    assert meta.relations[0].type == "stabilizes_service"
    assert meta.relations[0].origin == "explicit"
    
    # Origins
    assert meta.metadata_origin["id"] == "explicit"
    assert meta.metadata_origin["name"] == "explicit"
    assert meta.metadata_origin["drawer"] == "explicit"
    assert meta.metadata_origin["kind"] == "explicit"
    assert meta.metadata_origin["document_type"] == "explicit"
    assert meta.metadata_origin["scope.level"] == "explicit"


def test_no_frontmatter_document():
    raw_text = """# CLAUDE Guidelines
This is a standard text without YAML frontmatter.
We reference [[learnings/openai-tts]] and [Azure](azure/voice.md).
"""
    meta = parse_and_normalize(raw_text, "/storage/CLAUDE.md", "/storage")
    
    assert meta.identity.id == "CLAUDE"
    assert meta.identity.name == "CLAUDE"
    assert meta.classification.document_type == "harness_instructions"
    assert meta.classification.kind == "preference"
    assert meta.classification.drawer == "preferences"
    
    assert meta.scope.level == "project"
    assert meta.scope.path == "./**"
    assert meta.scope.harness == "claude"
    
    # Relations parsed from body (F7)
    assert len(meta.relations) == 2
    targets = [r.target for r in meta.relations]
    assert "learnings/openai-tts" in targets
    assert "azure/voice" in targets
    
    # Origins
    assert meta.metadata_origin["id"] == "inferred"
    assert meta.metadata_origin["name"] == "inferred"
    assert meta.metadata_origin["drawer"] == "inferred"
    assert meta.metadata_origin["document_type"] == "inferred"
    assert meta.metadata_origin["scope.harness"] == "inferred"


def test_partial_frontmatter_and_fallback():
    raw_text = """---
name: Partial Note
tags: [test, infra]
---
Standard body text.
"""
    meta = parse_and_normalize(raw_text, "/storage/subdir/partial-note.md", "/storage")
    
    assert meta.identity.id == "subdir/partial-note"
    assert meta.identity.name == "Partial Note"
    assert meta.classification.drawer == "facts"
    assert meta.classification.kind == "factual"
    assert meta.classification.document_type == "memory"
    
    assert meta.scope.level == "folder"
    assert meta.scope.path == "./subdir/**"
    assert meta.scope.harness is None
    
    # Origins
    assert meta.metadata_origin["id"] == "inferred"
    assert meta.metadata_origin["name"] == "explicit"
    assert meta.metadata_origin["drawer"] == "inferred"
    assert meta.metadata_origin["scope.level"] == "default"
    assert meta.metadata_origin["scope.path"] == "default"


def test_document_type_inference_rules():
    storage = "/storage"
    
    # SKILL.md
    meta = parse_and_normalize("hello", os.path.join(storage, "SKILL.md"), storage)
    assert meta.classification.document_type == "skill_instructions"
    assert meta.classification.kind == "procedural_anchor"
    assert meta.classification.drawer == "insights"
    
    # adr-001.md
    meta = parse_and_normalize("hello", os.path.join(storage, "adr-001.md"), storage)
    assert meta.classification.document_type == "decision_record"
    
    # README.md
    meta = parse_and_normalize("hello", os.path.join(storage, "README.md"), storage)
    assert meta.classification.document_type == "project_context"
    
    # general.txt
    meta = parse_and_normalize("hello", os.path.join(storage, "general.txt"), storage)
    assert meta.classification.document_type == "memory"
    assert meta.source.format == "text"
