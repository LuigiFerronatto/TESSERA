"""Regression coverage for canonical compatibility and auditable parsing."""

import os
import tempfile

import pytest

from tessera import TesseraEngine
from tessera.canonical import parse_and_normalize


@pytest.mark.parametrize(
    ("filename", "expected_type", "expected_kind", "expected_drawer"),
    [
        ("AGENTS.md", "harness_instructions", "instruction", None),
        ("CLAUDE.md", "harness_instructions", "instruction", None),
        ("GEMINI.md", "harness_instructions", "instruction", None),
        ("memory-retrieval.SKILL.md", "skill_instructions", "instruction", None),
        ("SKILL.md", "skill_instructions", "instruction", None),
    ],
)
def test_instruction_filename_classification(filename, expected_type, expected_kind, expected_drawer):
    meta = parse_and_normalize("# Instructions\nFollow these rules.", f"/storage/{filename}", "/storage")
    assert meta.classification.document_type == expected_type
    assert meta.classification.kind == expected_kind
    assert meta.classification.drawer is expected_drawer


def test_agents_md_is_harness_agnostic():
    meta = parse_and_normalize("# Agent rules", "/storage/AGENTS.md", "/storage")
    assert meta.scope.harness is None
    assert meta.scope.path == "./**"


def test_nested_foreign_metadata_type_maps_to_canonical_kind_and_drawer():
    raw = """---
metadata:
  type: learning
  category: memory
  phase: foundation
  topic: retrieval
---
A retrieval lesson.
"""
    meta = parse_and_normalize(raw, "/storage/learnings/retrieval.md", "/storage")
    assert meta.classification.kind == "procedural_anchor"
    assert meta.classification.drawer == "insights"


def test_nested_foreign_metadata_related_to_becomes_graph_relation():
    raw = """---
metadata:
  type: learning
  related_to:
    - lao/charter
    - lao/memory-structure
---
A learning connected to two canonical memories.
"""
    meta = parse_and_normalize(raw, "/storage/learning.md", "/storage")
    targets = {(rel.type, rel.target) for rel in meta.relations}
    assert ("related_to", "lao/charter") in targets
    assert ("related_to", "lao/memory-structure") in targets


def test_top_level_native_metadata_wins_over_nested_foreign_metadata():
    raw = """---
kind: factual
related_to:
  - canonical/target
metadata:
  type: learning
  related_to:
    - legacy/target
---
Native values must win when explicitly supplied.
"""
    meta = parse_and_normalize(raw, "/storage/note.md", "/storage")
    assert meta.classification.kind == "factual"
    assert meta.classification.drawer == "facts"
    targets = {rel.target for rel in meta.relations}
    assert "canonical/target" in targets
    assert "legacy/target" not in targets


def test_malformed_yaml_frontmatter_fails_auditably():
    raw = """---
id: lao/test
metadata: [broken
---
Body.
"""
    with pytest.raises(ValueError, match="Malformed YAML frontmatter"):
        parse_and_normalize(raw, "/storage/note.md", "/storage")


def test_unclosed_frontmatter_fails_auditably():
    raw = """---
id: lao/test
Body accidentally starts without closing YAML delimiter.
"""
    with pytest.raises(ValueError, match="no closing delimiter"):
        parse_and_normalize(raw, "/storage/note.md", "/storage")


def test_engine_preserves_nested_foreign_related_to_edge():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "charter.md"), "w", encoding="utf-8") as f:
            f.write("---\nid: lao/charter\n---\nLAO charter.")
        with open(os.path.join(tmp, "learning.md"), "w", encoding="utf-8") as f:
            f.write(
                "---\nid: lao/learning\nmetadata:\n  type: learning\n  related_to:\n    - lao/charter\n---\nLearning body."
            )

        engine = TesseraEngine(storage_dir=tmp)
        engine.build_index(use_cache=False)

        assert engine.graph.nodes["lao/learning"]["node_type"] == "procedural_anchor"
        assert engine.graph.has_edge("lao/learning", "lao/charter")
