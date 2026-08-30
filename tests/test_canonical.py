"""Unit tests for the Canonical Metadata Model and Normalization (TESSERA Foundation v0.1)."""

import os
import tempfile
import pytest
import datetime
from tessera import TesseraEngine
from tessera.canonical import parse_and_normalize, CanonicalMetadata
from tessera.conflict import ConflictResolver


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


def test_harness_instructions_not_classified_as_preference():
    """Verify CLAUDE.md does not get drawer='preferences' and has kind='instruction'."""
    raw_text = """# CLAUDE Guidelines
This is a standard text without YAML frontmatter.
"""
    meta = parse_and_normalize(raw_text, "/storage/CLAUDE.md", "/storage")
    
    assert meta.identity.id == "CLAUDE"
    assert meta.identity.name == "CLAUDE"
    assert meta.classification.document_type == "harness_instructions"
    assert meta.classification.kind == "instruction"
    assert meta.classification.drawer is None  # F3: Non-memories have None drawer
    
    assert meta.scope.level == "project"
    assert meta.scope.path == "./**"
    assert meta.scope.harness == "claude"


def test_missing_confidence_is_none():
    """Verify that missing confidence and quality metrics remain None, never guessed."""
    raw_text = """# Standard text
Hello world
"""
    meta = parse_and_normalize(raw_text, "/storage/general.md", "/storage")
    assert meta.quality.confidence is None
    assert meta.quality.authority is None
    assert meta.metadata_origin["quality.confidence"] == "default"


def test_metadata_origin_system_assignment():
    """Verify system-assigned origins on observed physical file parameters."""
    raw_text = """# Some content"""
    meta = parse_and_normalize(raw_text, "/storage/test.md", "/storage")
    
    assert meta.metadata_origin["source.path"] == "system"
    assert meta.metadata_origin["source.document_hash"] == "system"
    assert meta.metadata_origin["source.content_hash"] == "system"
    assert meta.metadata_origin["temporal.indexed_at"] == "system"


def test_relative_links_resolution():
    """Verify local links in body resolve relative to the source directory, deduplicating when needed."""
    raw_text = """# Index Document
See [Bar Guideline](../bar/guideline.md) and [[wikilink]].
And another duplicate [Bar Guideline](../bar/guideline.md) to ensure deduplication.
"""
    meta = parse_and_normalize(raw_text, "/storage/docs/foo/a.md", "/storage")
    
    # Target path: docs/foo/../bar/guideline.md -> docs/bar/guideline
    targets = [r.target for r in meta.relations]
    assert "docs/bar/guideline" in targets
    assert "wikilink" in targets
    
    # Length of relations should be exactly 2 because of deduplication (F7)
    assert len(meta.relations) == 2


def test_stable_identity_rename_and_move_in_engine():
    """Verify rename/move detection: ID stays stable, path changes, content hash remains same."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        # Write a loose markdown file (no explicit ID)
        filepath_old = os.path.join(tmp, "learnings_old.md")
        with open(filepath_old, "w", encoding="utf-8") as f:
            f.write("# Stable identity test\nMy unique content is here.")
            
        engine.build_index()
        
        # Verify initial state
        initial_nodes = [n for n, d in engine.graph.nodes(data=True) if d.get("node_type") == "factual"]
        assert len(initial_nodes) == 1
        original_id = initial_nodes[0]
        
        # Move the file on disk to a new path with a new filename
        filepath_new = os.path.join(tmp, "sub", "learnings_moved.md")
        os.makedirs(os.path.dirname(filepath_new), exist_ok=True)
        os.rename(filepath_old, filepath_new)
        
        # Re-build index (will trigger rename detection through manifest content hashes!)
        engine.build_index(use_cache=False)
        
        # Verify original ID is preserved and stable, but path is updated (F5)
        new_nodes = [n for n, d in engine.graph.nodes(data=True) if d.get("node_type") == "factual"]
        assert len(new_nodes) == 1
        assert new_nodes[0] == original_id
        
        node_data = engine.graph.nodes[original_id]
        assert node_data["filepath"] == filepath_new


def test_stable_source_document_id_on_rename():
    """Verify that source.document_id is stable across rename/move operations."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        filepath_old = os.path.join(tmp, "file_old.md")
        with open(filepath_old, "w", encoding="utf-8") as f:
            f.write("# Document Title\nStable document ID content.")
            
        engine.build_index()
        nodes_v1 = [n for n, d in engine.graph.nodes(data=True)]
        assert len(nodes_v1) == 1
        meta_v1 = engine.graph.nodes[nodes_v1[0]]["canonical_metadata"]
        doc_id_v1 = meta_v1.source.document_id
        
        # Move file on disk
        filepath_new = os.path.join(tmp, "sub", "file_moved.md")
        os.makedirs(os.path.dirname(filepath_new), exist_ok=True)
        os.rename(filepath_old, filepath_new)
        
        engine.build_index(use_cache=False)
        nodes_v2 = [n for n, d in engine.graph.nodes(data=True)]
        assert len(nodes_v2) == 1
        meta_v2 = engine.graph.nodes[nodes_v2[0]]["canonical_metadata"]
        doc_id_v2 = meta_v2.source.document_id
        
        # Document ID must remain 100% stable
        assert doc_id_v1 == doc_id_v2
        assert meta_v2.source.path == "sub/file_moved.md"


def test_duplicate_content_is_not_classified_as_rename():
    """Verify that copy/duplicate files with same content retain separate IDs if original still exists."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        filepath_1 = os.path.join(tmp, "a.md")
        with open(filepath_1, "w", encoding="utf-8") as f:
            f.write("# Identical content\nSame text.")
            
        # Write b.md with EXACT same content, but a.md STILL exists on disk!
        filepath_2 = os.path.join(tmp, "b.md")
        with open(filepath_2, "w", encoding="utf-8") as f:
            f.write("# Identical content\nSame text.")
            
        engine.build_index(use_cache=False)
        nodes = sorted([n for n, d in engine.graph.nodes(data=True) if d.get("node_type") == "factual"])
        
        # Mudar o arquivo para duplicado não deve fundir suas identidades
        assert len(nodes) == 2
        assert nodes[0] == "a"
        assert nodes[1] == "b"


def test_duplicate_explicit_id_collision_failure():
    """Verify that declaring identical explicit IDs in multiple files raises ValueError."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        # Write two files declaring explicit ID "collision/test"
        with open(os.path.join(tmp, "file1.md"), "w", encoding="utf-8") as f:
            f.write("---\nid: collision/test\n---\nHello")
            
        with open(os.path.join(tmp, "file2.md"), "w", encoding="utf-8") as f:
            f.write("---\nid: collision/test\n---\nWorld")
            
        with pytest.raises(ValueError) as exc:
            engine.build_index(use_cache=False)
        assert "Collision de IDs Explícitos Detectada" in str(exc.value)


def test_raw_frontmatter_preservation():
    """Verify that canonical_metadata.raw_frontmatter remains raw and unmutated."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        with open(os.path.join(tmp, "notes.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: Authentic\n---\nBody content.")
            
        engine.build_index()
        
        meta = engine.graph.nodes["notes"]["canonical_metadata"]
        # Injected legacy adapter fields must NOT exist in the truly raw_frontmatter
        assert "id" not in meta.raw_frontmatter
        assert "node_type" not in meta.raw_frontmatter
        assert "drawer" not in meta.raw_frontmatter
        assert "active_connections" not in meta.raw_frontmatter
        assert meta.raw_frontmatter.get("name") == "Authentic"


def test_semantic_equivalence_on_metadata_changes():
    """Verify that changing tags/entities invalidates semantic equivalence, while content hash matches."""
    raw_text_1 = """---
tags: [tag_old]
---
Same body text.
"""
    raw_text_2 = """---
tags: [tag_new]
---
Same body text.
"""
    meta_1 = parse_and_normalize(raw_text_1, "/storage/note.md", "/storage")
    meta_2 = parse_and_normalize(raw_text_2, "/storage/note.md", "/storage")
    
    # Body is equivalent
    assert meta_1.is_content_equivalent(meta_2)
    # But because tags differ and tags affect retrieval score, they are NOT semantically equivalent
    assert not meta_1.is_semantically_equivalent(meta_2)


def test_stable_identity_edit_retains_id():
    """Verify that editing the content of a file retains the stable ID while updating version hashes."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        filepath = os.path.join(tmp, "note.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Content V1\nSame stable ID")
            
        engine.build_index()
        nodes_v1 = [n for n, d in engine.graph.nodes(data=True) if d.get("node_type") == "factual"]
        assert len(nodes_v1) == 1
        id_v1 = nodes_v1[0]
        hash_v1 = engine.graph.nodes[id_v1]["canonical_metadata"].source.content_hash
        
        # Edit the content on disk
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Content V2\nSame stable ID but modified.")
            
        engine.build_index(use_cache=False)
        nodes_v2 = [n for n, d in engine.graph.nodes(data=True) if d.get("node_type") == "factual"]
        assert len(nodes_v2) == 1
        assert nodes_v2[0] == id_v1  # Stable ID retained
        
        hash_v2 = engine.graph.nodes[id_v1]["canonical_metadata"].source.content_hash
        assert hash_v1 != hash_v2  # Hash changed


def test_harness_instructions_conflict_resolver_exclusion():
    """Verify ConflictResolver ignores non-memory instructions (drawer is None)."""
    memories = [
        {
            "id": "CLAUDE",
            "type": "instruction",
            "frontmatter": {
                "drawer": None,
                "last_updated_at": "2026-08-29T10:00:00Z"
            }
        },
        {
            "id": "CLAUDE_NEWER",
            "type": "instruction",
            "frontmatter": {
                "drawer": None,
                "last_updated_at": "2026-08-30T10:00:00Z"
            }
        }
    ]
    # If they were treated as preferences with same conflict criteria, one of them might be discarded.
    # But since instructions are bypassed, BOTH must survive the resolution.
    resolved = ConflictResolver.resolve_temporal_conflicts(memories)
    assert len(resolved) == 2


def test_repeated_indexing_semantic_equivalence():
    """Verify that repeatedly indexing the same unchanged content maintains semantic equivalence."""
    raw_text = """# Persistent Memory
This is semantic data.
"""
    meta_1 = parse_and_normalize(raw_text, "/storage/mem.md", "/storage")
    
    # Emulate re-indexing a fraction of a second later (different indexed_at)
    meta_2 = parse_and_normalize(raw_text, "/storage/mem.md", "/storage")
    
    assert meta_1.is_semantically_equivalent(meta_2)


def test_integration_canonical_index_query():
    """Verify full integration: source file -> parse_and_normalize -> canonical metadata -> graph/index -> query."""
    with tempfile.TemporaryDirectory() as tmp:
        engine = TesseraEngine(storage_dir=tmp)
        
        # Write some files
        with open(os.path.join(tmp, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write("# CLAUDE Guidelines\nMust follow database setup rules in [[sk_setup_db]].")
            
        with open(os.path.join(tmp, "sk_setup_db.md"), "w", encoding="utf-8") as f:
            f.write("""---
kind: procedural_anchor
---
# Database Setup
Ensure port 5432 is free.
""")
            
        engine.build_index()
        
        # Check node structures in graph (Integrated Canonical Nodes!)
        assert "CLAUDE" in engine.graph
        assert "sk_setup_db" in engine.graph
        
        claude_meta = engine.graph.nodes["CLAUDE"]["canonical_metadata"]
        assert claude_meta.classification.document_type == "harness_instructions"
        assert claude_meta.classification.drawer is None
        
        # Check relations (F7: wikilink parsed on index build and translated to graph edge)
        assert engine.graph.has_edge("CLAUDE", "sk_setup_db")
        
        # Querying
        results = engine.retrieve_context("database guidelines", top_n=2)
        assert len(results) > 0
