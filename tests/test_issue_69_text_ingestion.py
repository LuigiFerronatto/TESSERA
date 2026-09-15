"""Acceptance coverage for Issue #69 plain-text source ingestion."""

from pathlib import Path

from tessera.canonical import parse_and_normalize
from tessera.engine import TesseraEngine
from tessera.evidence import evidence_from_canonical, verify_evidence_freshness


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_txt_is_body_only_even_when_it_looks_like_markdown_frontmatter(tmp_path):
    raw = "---\nid: must-not-be-metadata\n---\nplain text body\n"
    path = tmp_path / "source.txt"
    _write(path, raw)

    metadata = parse_and_normalize(raw, str(path), str(tmp_path))

    assert metadata.source.format == "text"
    assert metadata.identity.id == "source"
    assert metadata.metadata_origin["id"] == "inferred"
    assert metadata.raw_frontmatter == {}
    assert metadata.classification.drawer == "facts"
    assert metadata.source.content_hash == metadata.source.document_hash
    assert path.read_text(encoding="utf-8") == raw


def test_identical_markdown_and_txt_are_distinct_retrievable_documents(tmp_path):
    _write(tmp_path / "same.md", "shared platypus knowledge\n")
    _write(tmp_path / "same.txt", "shared platypus knowledge\n")
    engine = TesseraEngine(storage_dir=str(tmp_path))

    engine.build_index(use_cache=False)

    memory_nodes = {
        node_id: data
        for node_id, data in engine.graph.nodes(data=True)
        if data.get("canonical_metadata") is not None
    }
    assert len(memory_nodes) == 2
    assert len({data["canonical_metadata"].source.document_id for data in memory_nodes.values()}) == 2
    assert {data["canonical_metadata"].source.format for data in memory_nodes.values()} == {
        "markdown",
        "text",
    }
    results = engine.retrieve_context("platypus", top_n=5)
    assert len(results) == 2
    assert {item["provenance"]["source"]["format"] for item in results} == {
        "markdown",
        "text",
    }
    txt_result = next(item for item in results if item["provenance"]["source"]["format"] == "text")
    assert txt_result["evidence"]["source"]["path"] == "same.txt"
    assert txt_result["evidence"]["span"] == {"start_line": 1, "end_line": 1}


def test_txt_incremental_add_edit_move_delete_lifecycle(tmp_path):
    source = tmp_path / "notes.txt"
    _write(source, "alpha\n")
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.build_index(use_cache=False)
    memory_id = next(iter(engine.file_registry))
    document_id = engine.graph.nodes[memory_id]["canonical_metadata"].source.document_id

    engine.build_index(use_cache=False)
    assert engine.last_index_stats["parsed"] == 0
    assert engine.last_index_stats["unchanged"] == 1

    _write(source, "beta\n")
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["updated"] == 1
    assert engine.graph.nodes[memory_id]["body"] == "beta"

    moved = tmp_path / "archive" / "renamed.txt"
    moved.parent.mkdir()
    source.rename(moved)
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["moved"] == 1
    assert engine.graph.nodes[memory_id]["canonical_metadata"].source.document_id == document_id
    assert engine.graph.nodes[memory_id]["filename"] == "archive/renamed.txt"

    moved.unlink()
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["removed"] == 1
    assert memory_id not in engine.graph


def test_txt_evidence_freshness_uses_plain_text_semantics(tmp_path):
    raw = "---\nnot: frontmatter\n---\nunique evidence line\n"
    path = tmp_path / "evidence.txt"
    _write(path, raw)
    metadata = parse_and_normalize(raw, str(path), str(tmp_path))
    record = evidence_from_canonical(metadata)

    assert record.source.format == "text"
    assert record.span.start_line == 1
    assert record.span.end_line == 4
    assert verify_evidence_freshness(record, str(tmp_path)).status == "fresh"

    _write(path, raw + "changed\n")
    assert verify_evidence_freshness(record, str(tmp_path)).status == "content_changed"
