"""Focused lifecycle coverage for Issue #12 incremental indexing."""

from pathlib import Path

from tessera.engine import TesseraEngine


def _note(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_noop_index_parses_zero_sources(tmp_path):
    _note(tmp_path / "one.md", "# One\nalpha")
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.build_index(use_cache=False)

    engine.build_index(use_cache=False)

    assert engine.last_index_stats["parsed"] == 0
    assert engine.last_index_stats["unchanged"] == 1
    assert engine.last_index_stats["mode"] == "incremental"


def test_manifest_without_graph_snapshot_forces_full_rebuild(tmp_path):
    _note(tmp_path / "one.md", "# One\nalpha")
    first = TesseraEngine(storage_dir=str(tmp_path))
    first.build_index(use_cache=False)
    Path(first.index_cache_pkl).unlink()

    second = TesseraEngine(storage_dir=str(tmp_path))
    second.build_index(use_cache=False)

    assert second.last_index_stats["mode"] == "clean_rebuild"
    assert second.last_index_stats["parsed"] == 1
    assert len(second.graph.nodes) == 1


def test_add_edit_move_delete_preserves_identity_and_removes_stale_nodes(tmp_path):
    original = tmp_path / "one.md"
    _note(original, "# One\nalpha")
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.build_index(use_cache=False)
    original_id = next(iter(engine.file_registry))
    original_doc_id = engine.graph.nodes[original_id]["canonical_metadata"].source.document_id

    added = tmp_path / "two.md"
    _note(added, "# Two\nbeta")
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["added"] == 1
    added_id = next(node for node, path in engine.file_registry.items() if path == str(added))

    _note(added, "# Two\ngamma")
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["updated"] == 1
    assert "gamma" in engine.graph.nodes[added_id]["body"]

    moved = tmp_path / "nested" / "renamed.md"
    moved.parent.mkdir()
    original.rename(moved)
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["moved"] == 1
    assert original_id in engine.graph
    assert engine.graph.nodes[original_id]["canonical_metadata"].source.document_id == original_doc_id
    assert engine.graph.nodes[original_id]["filename"] == "nested/renamed.md"

    added.unlink()
    engine.build_index(use_cache=False)
    assert engine.last_index_stats["removed"] == 1
    assert added_id not in engine.graph
    assert all("beta" not in text for text in engine.node_corpus.values())
