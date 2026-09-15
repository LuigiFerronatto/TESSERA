"""Acceptance coverage for Issue #70 structural source segmentation."""

import json
import os
import pickle
from pathlib import Path
import subprocess
import sys

from tessera import SEGMENT_NODE_TYPE, TesseraEngine


def _section(title: str, token: str, lines: int = 14) -> str:
    return f"## {title}\n" + "\n".join(
        f"{token} section sentence {index} preserves its surrounding document context."
        for index in range(lines)
    )


def _reference_document() -> str:
    return (
        "---\n"
        "id: docs/segmentation-reference\n"
        "document_type: reference\n"
        "---\n\n"
        "# Segmentation reference\n\n"
        + _section("Alpha", "granite")
        + "\n\n"
        + _section("Beta", "orichalcum")
        + "\n\n"
        + _section("Gamma", "cobalt")
        + "\n"
    )


def _segments(engine: TesseraEngine):
    return {
        node_id: data
        for node_id, data in engine.graph.nodes(data=True)
        if data.get("node_type") == SEGMENT_NODE_TYPE
    }


def test_short_atomic_memory_is_not_fragmented(tmp_path: Path) -> None:
    source = tmp_path / "atomic.md"
    source.write_text(
        "---\nid: memory/atomic\nnode_type: factual\n---\n\n"
        "## Context\nA small atomic fact.\n\n## Outcome\nKeep it together.\n",
        encoding="utf-8",
    )

    engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=False)

    assert not _segments(engine)
    assert set(engine.file_registry) == {"memory/atomic"}
    assert engine.graph.nodes["memory/atomic"]["body"].endswith("Keep it together.")


def test_structured_document_keeps_parent_and_exact_addressable_spans(tmp_path: Path) -> None:
    source = tmp_path / "reference.md"
    raw = _reference_document()
    source.write_text(raw, encoding="utf-8")

    engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=False)
    segments = _segments(engine)

    assert len(segments) >= 3
    assert set(engine.file_registry) == {"docs/segmentation-reference"}
    parent = engine.graph.nodes["docs/segmentation-reference"]
    assert "orichalcum" in parent["body"]
    assert source.read_text(encoding="utf-8") == raw

    raw_lines = raw.splitlines()
    for segment_id, segment in segments.items():
        assert segment["parent_memory_id"] == "docs/segmentation-reference"
        assert segment["document_id"] == parent["canonical_metadata"].source.document_id
        assert segment["document_hash"] == parent["canonical_metadata"].source.document_hash
        start = segment["source_span"]["start_line"]
        end = segment["source_span"]["end_line"]
        assert "\n".join(raw_lines[start - 1 : end]).strip() == segment["body"]
        assert engine.graph.has_edge("docs/segmentation-reference", segment_id)
        assert engine.graph.has_edge(segment_id, "docs/segmentation-reference")
        assert engine.graph["docs/segmentation-reference"][segment_id]["relation_type"] == "has_segment"
        assert engine.graph[segment_id]["docs/segmentation-reference"]["relation_type"] == "segment_of"

    readable = json.loads((tmp_path / ".tessera_index" / "graph.json").read_text())
    recorded_segments = [
        node for node in readable["nodes"].values()
        if node["node_type"] == SEGMENT_NODE_TYPE
    ]
    assert len(recorded_segments) == len(segments)
    assert all(node["document_id"] and node["source_span"] for node in recorded_segments)


def test_segment_hit_returns_parent_with_precise_source_version_evidence(tmp_path: Path) -> None:
    source = tmp_path / "reference.md"
    source.write_text(_reference_document(), encoding="utf-8")
    engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=False)

    result = engine.retrieve_context("orichalcum sentence 9", top_n=1)[0]

    assert result["id"] == "docs/segmentation-reference"
    assert result["type"] == "factual"
    assert all(item["type"] != SEGMENT_NODE_TYPE for item in engine.retrieve_context("orichalcum", top_n=10))
    assert result["evidence_info"]["strategy"] == "structural_segment"
    assert result["evidence_info"]["segment_id"] in _segments(engine)
    assert result["evidence_info"]["heading"] == "Beta"
    assert result["evidence"]["source"]["document_id"] == result["provenance"]["source"]["document_id"]
    assert result["evidence"]["source"]["document_hash"] == result["provenance"]["source"]["document_hash"]
    assert result["evidence"]["span"] == result["evidence_info"]["span"]
    assert result["evidence"]["span"]["start_line"] < result["evidence"]["span"]["end_line"]
    assert len(result["relevant_evidence"]) < len(result["body"])


def test_long_plain_text_uses_deterministic_windows(tmp_path: Path) -> None:
    source = tmp_path / "long-notes.txt"
    raw = "\n\n".join(
        f"Paragraph {index}: plain text topic {index} with durable provenance. " * 3
        for index in range(35)
    )
    source.write_text(raw, encoding="utf-8")

    first = TesseraEngine(str(tmp_path))
    first.build_index(use_cache=False)
    first_ids = sorted(_segments(first))
    assert len(first_ids) >= 2
    assert all(first.graph.nodes[node]["source_format"] == "text" for node in first_ids)

    cached = TesseraEngine(str(tmp_path))
    cached.build_index(use_cache=True)
    assert sorted(_segments(cached)) == first_ids
    assert cached.last_index_stats["mode"] == "cache_hit"
    assert cached.last_index_stats["segments"] == len(first_ids)

    rebuilt = TesseraEngine(str(tmp_path))
    rebuilt.build_index(use_cache=False)
    assert sorted(_segments(rebuilt)) == first_ids


def test_changed_or_deleted_source_removes_stale_segments(tmp_path: Path) -> None:
    source = tmp_path / "reference.md"
    source.write_text(_reference_document(), encoding="utf-8")
    engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=False)
    old_segments = set(_segments(engine))
    old_document_id = engine.graph.nodes["docs/segmentation-reference"]["canonical_metadata"].source.document_id
    assert old_segments

    moved = tmp_path / "moved-reference.md"
    source.rename(moved)
    engine.build_index(use_cache=True)
    assert set(_segments(engine)) == old_segments
    assert engine.last_index_stats["moved"] == 1
    assert all(data["source_path"] == "moved-reference.md" for data in _segments(engine).values())
    assert engine.graph.nodes["docs/segmentation-reference"]["canonical_metadata"].source.document_id == old_document_id

    moved.write_text(_reference_document().replace("orichalcum", "titanium"), encoding="utf-8")
    engine.build_index(use_cache=True)
    new_segments = set(_segments(engine))
    assert new_segments
    assert old_segments - new_segments
    assert not (old_segments - new_segments) & set(engine.node_corpus)

    moved.unlink()
    engine.build_index(use_cache=True)
    assert not _segments(engine)
    assert not engine.file_registry
    assert not any(node.startswith("seg_") for node in engine.node_corpus)


def test_pre_segmentation_cache_schema_forces_rebuild(tmp_path: Path) -> None:
    source = tmp_path / "reference.md"
    source.write_text(_reference_document(), encoding="utf-8")
    first = TesseraEngine(str(tmp_path))
    first.build_index(use_cache=False)
    cache = tmp_path / ".tessera_index" / "graph.pkl"

    with cache.open("rb") as handle:
        snapshot = pickle.load(handle)
    snapshot.pop("index_schema_version")
    with cache.open("wb") as handle:
        pickle.dump(snapshot, handle)

    rebuilt = TesseraEngine(str(tmp_path))
    rebuilt.build_index(use_cache=True)

    assert rebuilt.last_index_stats["mode"] == "clean_rebuild"
    assert rebuilt.last_index_stats["parsed"] == 1
    assert _segments(rebuilt)


def test_segment_ranking_is_stable_across_python_hash_seeds(tmp_path: Path) -> None:
    for index, token in enumerate(("granite", "orichalcum", "cobalt", "titanium")):
        (tmp_path / f"reference-{index}.md").write_text(
            "---\n"
            f"id: docs/reference-{index}\n"
            "document_type: reference\n"
            "---\n\n"
            "# Reference\n\n"
            + _section("Shared", token, lines=18)
            + "\n\n"
            + _section("Common", "durable", lines=18)
            + "\n",
            encoding="utf-8",
        )

    script = """
import json
import sys
from tessera import TesseraEngine

engine = TesseraEngine(sys.argv[1])
engine.build_index(use_cache=False, persist=False)
hits = engine.retrieve_context("durable reference sentence", top_n=4)
print(json.dumps([
    {
        "id": hit["id"],
        "score": hit["score"],
        "score_explain": hit["score_explain"],
        "evidence_info": hit["evidence_info"],
    }
    for hit in hits
], sort_keys=True))
"""

    outputs = []
    for hash_seed in ("1", "947"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = hash_seed
        completed = subprocess.run(
            [sys.executable, "-c", script, str(tmp_path)],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        outputs.append(completed.stdout)

    assert outputs[0] == outputs[1]


def test_segment_seeds_augment_the_document_seed_budget(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr("tessera.engine_core.SEED_NODE_LIMIT", 1)
    (tmp_path / "segmented.md").write_text(
        "---\nid: docs/segmented\ndocument_type: reference\n---\n\n"
        "# Large reference\n\n"
        + _section("Background", "unrelated", lines=40)
        + "\n\n## Target\n"
        + ("needle quartz exact target.\n" * 12)
        + "\n\n"
        + _section("Appendix", "unrelated", lines=40),
        encoding="utf-8",
    )
    (tmp_path / "atomic.md").write_text(
        "---\nid: memory/atomic\nnode_type: factual\n---\n\n"
        "Needle appears in this concise independent fact.",
        encoding="utf-8",
    )

    engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=False, persist=False)
    results = engine.retrieve_context("needle quartz", top_n=2)

    assert {result["id"] for result in results} == {
        "docs/segmented",
        "memory/atomic",
    }
