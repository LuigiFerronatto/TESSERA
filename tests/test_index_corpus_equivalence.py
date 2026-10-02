"""Regression coverage for physical source identity and incremental equivalence."""

import hashlib
import json
import pickle
from pathlib import Path

import pytest

from tessera.canonical import compute_sha256
from tessera.config import ConfigurationResolver, ResolvedConfiguration, SourceRootRecord
from tessera.corpus_diagnostics import run_corpus_doctor
from tessera.engine import TesseraEngine
from tessera.evidence import verify_evidence_freshness
from tessera.source_formats import split_source


def _note(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _configuration(project: Path, includes=None) -> ResolvedConfiguration:
    includes = includes or ["docs/**/*.md", "memories/**/*.md"]
    _note(
        project / ".tessera" / "config.yaml",
        "schema_version: 2\nstore:\n"
        "  id: 3fdde7d1-deb7-4937-856a-a65cb6afeda7\n  path: memories\n"
        "sources:\n  roots:\n    - path: .\n      include:\n"
        + "".join("        - " + json.dumps(value) + "\n" for value in includes)
        + "index:\n  path: .tessera/index\n",
    )
    return ConfigurationResolver(cwd=project, environ={}).resolve()


def _old_entry(path: Path, memory_id: str, document_id: str):
    raw_text = path.read_text(encoding="utf-8")
    _metadata, body = split_source(raw_text, path=path)
    return {
        "id": memory_id,
        "document_id": document_id,
        "content_hash": compute_sha256(body),
        "file_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _old_cache(index: Path, manifest):
    index.mkdir(parents=True, exist_ok=True)
    (index / "identity_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    # An old graph must never be used to skip reparsing under the new namespace.
    (index / "graph.pkl").write_bytes(pickle.dumps({"index_schema_version": 2}))


@pytest.mark.parametrize("fresh_engine", [False, True])
@pytest.mark.parametrize("use_cache", [False, True])
def test_incremental_target_update_retains_unchanged_inbound_relation(
    tmp_path, fresh_engine, use_cache
):
    _note(tmp_path / "a.md", "---\nid: project/a\nrelated_to: project/b\n---\nAlpha queryanchor.")
    _note(tmp_path / "b.md", "---\nid: project/b\n---\nBeta is a related topic.")
    engine = TesseraEngine(str(tmp_path))
    engine.build_index()
    assert engine.graph.has_edge("project/a", "project/b")
    _note(tmp_path / "b.md", "---\nid: project/b\n---\nBeta is the updated related topic.")
    if fresh_engine:
        engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=use_cache)
    assert engine.graph.has_edge("project/a", "project/b")
    assert {row["id"] for row in engine.retrieve_context("queryanchor")} == {"project/a", "project/b"}
    reloaded = TesseraEngine(str(tmp_path))
    reloaded.build_index()
    assert reloaded.graph.has_edge("project/a", "project/b")


def test_incremental_relation_resolves_new_target_and_retracts_removed_link(tmp_path):
    source = tmp_path / "a.md"
    _note(source, "---\nid: project/a\nrelated_to: project/b\n---\nAlpha queryanchor.")
    engine = TesseraEngine(str(tmp_path))
    engine.build_index()
    assert not engine.graph.has_edge("project/a", "project/b")
    _note(tmp_path / "b.md", "---\nid: project/b\n---\nBeta related topic.")
    engine.build_index()
    assert engine.graph.has_edge("project/a", "project/b")
    _note(source, "---\nid: project/a\n---\nAlpha queryanchor, no remaining relation.")
    engine.build_index()
    assert not engine.graph.has_edge("project/a", "project/b")


@pytest.mark.parametrize("fresh_engine", [False, True])
def test_recursion_changes_do_not_reuse_a_different_corpus(tmp_path, fresh_engine):
    _note(tmp_path / "root.md", "Root source.")
    _note(tmp_path / "nested" / "child.md", "Child source.")
    engine = TesseraEngine(str(tmp_path))
    for recursive, expected in [(True, {"root", "nested/child"}), (False, {"root"}), (True, {"root", "nested/child"})]:
        if fresh_engine:
            engine = TesseraEngine(str(tmp_path))
        engine.build_index(recursive=recursive)
        assert set(engine.file_registry) == expected
        assert engine.last_index_stats["scanned"] == len(expected)
        # A repeated identical traversal may safely hit the cache.
        engine.build_index(recursive=recursive)
        assert engine.last_index_stats["mode"] == "cache_hit"
        assert engine.last_index_stats["unchanged"] == len(expected)


@pytest.mark.parametrize("includes, expected", [
    (["allowed.md"], {"allowed"}),
    (["nested/child.md"], set()),
    (["**/*.md"], {"allowed", "excluded"}),
])
def test_nonrecursive_index_only_narrows_configured_allowlist(tmp_path, includes, expected):
    _note(tmp_path / "allowed.md", "Approved source beacon.")
    _note(tmp_path / "excluded.md", "Unselected source canary.")
    _note(tmp_path / "nested" / "child.md", "Nested source token.")
    engine = TesseraEngine(configuration=_configuration(tmp_path, includes))
    engine.build_index(recursive=False, use_cache=False)
    assert set(engine.file_registry) == expected
    if "excluded" not in expected:
        assert not engine.retrieve_context("canary")


@pytest.mark.parametrize("edited", ["docs/guide.md", "memories/docs/guide.md"])
def test_project_and_store_same_relative_path_are_independent_sources(tmp_path, edited):
    _note(tmp_path / "docs/guide.md", "---\nid: documentation/guide\n---\nDocumentation source amber.")
    _note(tmp_path / "memories/docs/guide.md", "---\nid: generated/guide\n---\nGenerated source cobalt.")
    config = _configuration(tmp_path)
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert set(engine.identity_manifest) == {"docs/guide.md", "memories/docs/guide.md"}
    original_documents = {key: engine.graph.nodes[key]["canonical_metadata"].source.document_id for key in engine.file_registry}
    assert len(set(original_documents.values())) == 2
    assert run_corpus_doctor(config).status == "healthy"
    for record in engine.evidence_ledger.to_list():
        assert record["source"]["path"] in engine.identity_manifest
    for key in engine.file_registry:
        assert verify_evidence_freshness(engine.evidence_ledger.for_memory(key)[0], config).is_fresh
    changed_id = "documentation/guide" if edited == "docs/guide.md" else "generated/guide"
    _note(tmp_path / edited, f"---\nid: {changed_id}\n---\nUpdated source magenta.")
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert [row["id"] for row in engine.retrieve_context("magenta")] == [changed_id]
    assert engine.last_index_stats["parsed"] == 1
    assert {key: engine.graph.nodes[key]["canonical_metadata"].source.document_id for key in engine.file_registry} == original_documents
    assert run_corpus_doctor(config).status == "healthy"


def test_generated_logical_ids_and_duplicate_content_stay_distinct(tmp_path):
    _note(tmp_path / "docs/guide.md", "Identical body.")
    _note(tmp_path / "memories/docs/guide.md", "Identical body.")
    config = _configuration(tmp_path)
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert len(engine.file_registry) == 2
    assert "docs/guide" in engine.file_registry
    assert all(not key.startswith("memories/") for key in engine.file_registry)
    assert len({data["document_id"] for data in engine.identity_manifest.values()}) == 2
    engine.build_index()
    assert engine.last_index_stats["mode"] == "cache_hit"


def test_old_mixed_namespace_migration_preserves_provable_generated_identity(tmp_path):
    project_source = tmp_path / "docs/guide.md"
    generated = tmp_path / "memories/docs/guide.md"
    _note(project_source, "---\nid: documentation/guide\n---\nProject amber.")
    _note(generated, "Generated cobalt source without frontmatter.")
    config = _configuration(tmp_path)
    document_id = "doc_" + compute_sha256("docs/guide.md")[:12]
    _old_cache(Path(config.index_dir), {
        "docs/guide.md": _old_entry(generated, "docs/original-name", document_id),
        "gone.md": {"id": "gone", "document_id": "doc_gone", "content_hash": "gone", "file_hash": "gone"},
    })
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert set(engine.file_registry) == {"documentation/guide", "docs/original-name"}
    assert engine.graph.nodes["docs/original-name"]["canonical_metadata"].source.document_id == document_id
    assert len({entry["document_id"] for entry in engine.identity_manifest.values()}) == 2
    assert set(engine.identity_manifest) == {"docs/guide.md", "memories/docs/guide.md"}
    assert run_corpus_doctor(config).status == "healthy"
    # Rename after upgrading; the generated logical ID and document ID survive.
    renamed = generated.with_name("renamed.md")
    generated.rename(renamed)
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert engine.file_registry["docs/original-name"] == str(renamed)
    assert engine.graph.nodes["docs/original-name"]["canonical_metadata"].source.document_id == document_id
    assert run_corpus_doctor(config).status == "healthy"


def test_old_legacy_manifest_keeps_ids_paths_and_rename_tracking(tmp_path):
    source = tmp_path / "renamed.md"
    _note(source, "Legacy durable body.")
    _old_cache(tmp_path / ".tessera_index", {
        "renamed.md": _old_entry(source, "original", "doc_original"),
    })
    engine = TesseraEngine(str(tmp_path))
    engine.build_index()
    metadata = engine.graph.nodes["original"]["canonical_metadata"]
    assert metadata.source.path == "renamed.md"
    assert metadata.source.document_id == "doc_original"
    source.rename(tmp_path / "renamed-again.md")
    engine = TesseraEngine(str(tmp_path))
    engine.build_index()
    assert set(engine.file_registry) == {"original"}
    assert engine.graph.nodes["original"]["canonical_metadata"].source.document_id == "doc_original"


def test_broadening_store_only_sources_migrates_physical_keys_without_changing_ids(tmp_path):
    store = tmp_path / "memories"
    _note(store / "docs/guide.md", "Generated amber source.")
    _note(tmp_path / "docs/project.md", "Project cobalt source.")
    config = _configuration(tmp_path)
    store_only = ResolvedConfiguration(
        config.store_id, str(store), "project_config", source_roots=(SourceRootRecord(str(store)),),
        identity_root=str(tmp_path), index_dir=config.index_dir,
    )
    first = TesseraEngine(configuration=store_only)
    first.build_index()
    before = first.graph.nodes["docs/guide"]["canonical_metadata"].source
    assert before.path == "docs/guide.md"
    broadened = TesseraEngine(configuration=config)
    broadened.build_index()
    after = broadened.graph.nodes["docs/guide"]["canonical_metadata"].source
    assert after.path == "memories/docs/guide.md"
    assert after.document_id == before.document_id
    assert run_corpus_doctor(config).status == "healthy"
    narrowed = TesseraEngine(configuration=store_only)
    narrowed.build_index()
    assert set(narrowed.file_registry) == {"docs/guide"}
    assert narrowed.graph.nodes["docs/guide"]["canonical_metadata"].source.path == "docs/guide.md"
    assert narrowed.graph.nodes["docs/guide"]["canonical_metadata"].source.document_id == before.document_id


def test_ambiguous_legacy_manifest_does_not_merge_identical_sources(tmp_path):
    project_source = tmp_path / "docs/guide.md"
    generated = tmp_path / "memories/docs/guide.md"
    _note(project_source, "Identical source body.")
    _note(generated, "Identical source body.")
    config = _configuration(tmp_path)
    _old_cache(Path(config.index_dir), {
        "docs/guide.md": _old_entry(generated, "unprovable-old-id", "doc_old_shared"),
    })
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert len(engine.file_registry) == 2
    assert "unprovable-old-id" not in engine.file_registry
    assert len({entry["document_id"] for entry in engine.identity_manifest.values()}) == 2
    assert run_corpus_doctor(config).status == "healthy"


def test_legacy_migration_does_not_read_unselected_source_or_steal_its_identity(tmp_path, monkeypatch):
    import builtins

    project_source = tmp_path / "docs/guide.md"
    unselected = tmp_path / "memories/docs/guide.md"
    _note(project_source, "Selected project body.")
    _note(unselected, "Unselected generated body.")
    config = _configuration(tmp_path, ["docs/**/*.md"])
    _old_cache(Path(config.index_dir), {
        "docs/guide.md": _old_entry(unselected, "unselected/identity", "doc_unselected"),
    })
    original_open = builtins.open

    def guarded_open(path, *args, **kwargs):
        assert Path(path) != unselected, "Migration must not read an unselected source"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert set(engine.file_registry) == {"docs/guide"}


def test_external_generated_store_uses_same_physical_namespace(tmp_path):
    project = tmp_path / "project"
    store = tmp_path / "external-store"
    _note(project / "docs/guide.md", "---\nid: documentation/guide\n---\nProject source amber.")
    _note(store / "docs/guide.md", "Generated source cobalt.")
    config = ResolvedConfiguration(
        None, str(store), "project_config", project_root=str(project),
        source_roots=(SourceRootRecord(str(project)), SourceRootRecord(str(store))),
        identity_root=str(project), index_dir=str(project / ".tessera/index"),
    )
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert set(engine.identity_manifest) == {"docs/guide.md", "../external-store/docs/guide.md"}
    assert set(engine.file_registry) == {"documentation/guide", "docs/guide"}
    for key in engine.file_registry:
        assert verify_evidence_freshness(engine.evidence_ledger.for_memory(key)[0], config).is_fresh
    assert run_corpus_doctor(config).status == "healthy"


def test_project_relocation_keeps_external_store_ids_with_duplicate_bodies(tmp_path):
    project = tmp_path / "project"
    store = tmp_path / "external-store"
    _note(project / "docs/context.md", "---\nid: context\nrelated_to: [original_one, original_two]\n---\nProject context.")
    _note(store / "original_one.md", "First unique body.")
    _note(store / "original_two.md", "Second unique body.")

    def configuration(root):
        return ResolvedConfiguration(
            None, str(store), "project_config", project_root=str(root),
            source_roots=(SourceRootRecord(str(root), ("docs/**/*.md",)), SourceRootRecord(str(store))),
            identity_root=str(root), index_dir=str(root / ".tessera/index"),
        )

    engine = TesseraEngine(configuration=configuration(project))
    engine.build_index()
    for original, renamed in [("original_one", "one"), ("original_two", "two")]:
        (store / f"{original}.md").rename(store / f"{renamed}.md")
    engine = TesseraEngine(configuration=configuration(project))
    engine.build_index()
    _note(store / "one.md", "Common boilerplate.")
    _note(store / "two.md", "Common boilerplate.")
    engine.build_index()
    document_ids = {key: engine.graph.nodes[key]["canonical_metadata"].source.document_id for key in engine.file_registry}
    destination = tmp_path / "deeper/project"
    destination.parent.mkdir()
    project.rename(destination)
    relocated = configuration(destination)
    engine = TesseraEngine(configuration=relocated)
    engine.build_index()
    assert set(engine.file_registry) == {"context", "original_one", "original_two"}
    assert {key: engine.graph.nodes[key]["canonical_metadata"].source.document_id for key in engine.file_registry} == document_ids
    assert engine.graph.has_edge("context", "original_one")
    assert engine.graph.has_edge("context", "original_two")
    assert run_corpus_doctor(relocated).status == "healthy"
    for key in engine.file_registry:
        assert verify_evidence_freshness(engine.evidence_ledger.for_memory(key)[0], relocated).is_fresh


def test_new_inferred_project_source_cannot_take_existing_generated_id(tmp_path):
    store = tmp_path / "memories"
    generated = store / "docs/guide.md"
    _note(generated, "Existing generated cobalt source.")
    store_only = ResolvedConfiguration(
        None, str(store), "project_config", source_roots=(SourceRootRecord(str(store)),),
        identity_root=str(tmp_path), index_dir=str(tmp_path / ".tessera/index"),
    )
    engine = TesseraEngine(configuration=store_only)
    engine.build_index()
    before = engine.graph.nodes["docs/guide"]["canonical_metadata"].source.document_id
    _note(tmp_path / "docs/guide.md", "New project amber source.")
    config = _configuration(tmp_path)
    engine = TesseraEngine(configuration=config)
    engine.build_index()
    assert engine.file_registry["docs/guide"] == str(generated)
    assert engine.graph.nodes["docs/guide"]["canonical_metadata"].source.document_id == before
    assert len(engine.file_registry) == 2
    assert [row["id"] for row in engine.retrieve_context("cobalt")] == ["docs/guide"]
    assert run_corpus_doctor(config).status == "healthy"
