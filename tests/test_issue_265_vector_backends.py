"""Frozen-vector mechanics; these tests make no embedding-quality claim."""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
import subprocess
import sys

import pytest

from tessera.vector_backend import (
    ExactFlatBackend, SemanticIndexSpec, VectorBackend, VectorFilters,
    VectorIndexError, VectorIndexIncompatible, VectorRecord, VectorSearchRequest,
)
from tessera.vector_sqlite import SQLiteVectorBackend

PROFILE = "sha256:" + "a" * 64
VERSION = "sha256:" + "b" * 64
SPEC = SemanticIndexSpec(PROFILE, 3)


def record(name="a", vector=(1, 0, 0), **kwargs):
    data = dict(canonical_id=name, source_document_id="doc-" + name,
                source_version_hash=VERSION, embedding_profile_fingerprint=PROFILE,
                representation="atomic", representation_version="1", vector=vector,
                source_path=name + ".md", project_scope="project", drawer="facts",
                document_type="memory", evidence_ids=("ev-" + name,))
    data.update(kwargs)
    return VectorRecord(**data)


def query(vector=(1, 0, 0), **kwargs):
    return VectorSearchRequest(vector, PROFILE, **kwargs)


def ids(result):
    return tuple(hit.record.record_id for hit in result.hits)


@pytest.fixture(params=["flat", "sqlite"])
def backend(request, tmp_path):
    value = ExactFlatBackend() if request.param == "flat" else SQLiteVectorBackend(tmp_path / "index")
    value.open(SPEC)
    yield value
    value.close()


def test_protocol_and_empty_lifecycle(backend):
    assert isinstance(backend, VectorBackend)
    assert backend.capabilities().exact_or_ann == "exact"
    assert backend.stats().records == 0
    assert backend.search(query()).hits == ()
    assert backend.verify().valid
    backend.open(SPEC)
    backend.close()
    with pytest.raises(VectorIndexError, match="closed"):
        backend.search(query())
    backend.close()


@pytest.mark.parametrize("metric, scores", [
    ("cosine", [1, 0, -1]), ("dot", [2, 0, -1]), ("l2", [-1, -2, -4]),
])
def test_analytic_metric_oracle(backend, metric, scores):
    backend.close()
    # The fixture's SQLite namespace already has a cosine manifest.
    if isinstance(backend, SQLiteVectorBackend):
        backend = SQLiteVectorBackend(backend._root / metric)
    backend.open(replace(SPEC, metric=metric))
    try:
        backend.upsert([record("a", (2, 0, 0)), record("b", (0, 1, 0)), record("c", (-1, 0, 0))])
        result = backend.search(query())
        assert [hit.backend_score for hit in result.hits] == scores
        assert result.score_meaning == {"cosine": "cosine_similarity", "dot": "dot_product", "l2": "negative_squared_l2"}[metric]
        assert not hasattr(result.hits[0], "confidence")
    finally:
        backend.close()


def test_ties_identity_and_repeated_search(backend):
    records = [record("same-content-a"), record("same-content-b"), record("a", representation="source")]
    backend.upsert(reversed(records))
    expected = tuple(sorted(r.record_id for r in records))
    for _ in range(3):
        assert ids(backend.search(query())) == expected
    assert ids(backend.search(query(top_k=1))) == expected[:1]
    assert len(set(r.record_id for r in records)) == 3


@pytest.mark.parametrize("filters, names", [
    (VectorFilters(representations=("atomic",)), ["a"]),
    (VectorFilters(representations=("source", "segment")), ["b", "c"]),
    (VectorFilters(project_scope="other"), ["b"]),
    (VectorFilters(drawer="preferences"), ["c"]),
    (VectorFilters(document_type="guide"), ["b"]),
    (VectorFilters(source_ids=("doc-c",)), ["c"]),
    (VectorFilters(source_ids=("absent",)), []),
    (VectorFilters(project_scope="project", drawer="facts", representations=("source",)), []),
])
def test_typed_filter_parity(backend, filters, names):
    rows = [record("a"), record("b", representation="source", project_scope="other", drawer=None, document_type="guide"),
            record("c", representation="segment", drawer="preferences", representation_id="segment-2")]
    backend.upsert(rows)
    assert sorted(hit.record.canonical_id for hit in backend.search(query(filters=filters)).hits) == names


def test_source_edit_move_delete_metadata_and_rebuild_equivalence(backend, tmp_path):
    atomic = record("a")
    source = replace(atomic, representation="source", drawer=None)
    segment = replace(source, representation="segment", representation_id="seg-1")
    other = record("untouched")
    backend.upsert([atomic, source, segment, other])
    assert backend.upsert([atomic]).reused == 1
    old_ids = ids(backend.search(query(filters=VectorFilters(source_ids=("doc-a",)))))
    moved = [replace(r, source_path="moved/a.md", project_scope="new") for r in (atomic, source, segment)]
    change = backend.replace_source("doc-a", moved)
    assert change.upserted == 3 and change.removed == 0
    assert ids(backend.search(query(filters=VectorFilters(source_ids=("doc-a",))))) == old_ids
    edited = [replace(r, source_version_hash="sha256:" + "c" * 64, vector=(0, 1, 0)) for r in moved[:2]]
    change = backend.replace_source("doc-a", edited)
    assert change.removed == 3 and change.upserted == 2
    assert not set(old_ids) & set(ids(backend.search(query())))
    clean = ExactFlatBackend()
    clean.open(SPEC)
    clean.rebuild([*edited, other])
    assert backend.stats().corpus_manifest_hash == clean.stats().corpus_manifest_hash
    assert backend.search(query()).hits == clean.search(query()).hits
    assert backend.replace_source("doc-a", []).removed == 2
    assert backend.search(query()).hits[0].record == other
    assert backend.delete([other.record_id, other.record_id]).removed == 1
    assert backend.delete([other.record_id]).removed == 0
    assert backend.verify().valid


@pytest.mark.parametrize("operation", ["upsert", "replace_source", "rebuild"])
def test_bad_batch_and_interrupted_generation_are_atomic(backend, operation):
    original = record()
    backend.upsert([original])
    before = backend.stats().corpus_manifest_hash
    def run(rows):
        if operation == "replace_source":
            return backend.replace_source("doc-a", rows)
        return getattr(backend, operation)(rows)
    with pytest.raises(VectorIndexError):
        run([record("new", source_document_id="doc-a"), record("bad", (1, 2), source_document_id="doc-a")])
    def interrupted():
        yield record("new", source_document_id="doc-a")
        raise RuntimeError("encoder interrupted")
    with pytest.raises(RuntimeError):
        run(interrupted())
    assert backend.stats().corpus_manifest_hash == before
    assert backend.search(query()).hits[0].record == original


@pytest.mark.parametrize("change", [
    {"embedding_profile_fingerprint": "sha256:" + "d" * 64},
    {"representation_version": "2"},
    {"vector": (1, 2)},
])
def test_record_incompatibility_is_rejected(backend, change):
    with pytest.raises(VectorIndexError):
        backend.upsert([replace(record(), **change)])
    assert backend.stats().records == 0


def test_duplicate_and_wrong_source_are_atomic(backend):
    with pytest.raises(VectorIndexError, match="duplicate"):
        backend.upsert([record(), record()])
    with pytest.raises(VectorIndexError, match="another source"):
        backend.replace_source("other-source", [record()])
    with pytest.raises(VectorIndexError, match="invalid vector"):
        backend.delete(["invalid"])
    assert backend.stats().records == 0


@pytest.mark.parametrize("search_request", [
    query((1, 2)), query((float("nan"), 0, 0)), query((float("inf"), 0, 0)),
    query((True, 0, 0)), query((0, 0, 0)), query((1e101, 0, 0)),
    query(top_k=0), query(top_k=True), query(top_k=10001), query(filters={}),
    VectorSearchRequest((1, 0, 0), "sha256:" + "f" * 64),
])
def test_query_validation(backend, search_request):
    with pytest.raises(VectorIndexError):
        backend.search(search_request)


@pytest.mark.parametrize("factory", [
    lambda: SemanticIndexSpec(PROFILE, True), lambda: SemanticIndexSpec(PROFILE, 0),
    lambda: SemanticIndexSpec(PROFILE, 3, metric="other"),
    lambda: SemanticIndexSpec(PROFILE, 3, semantic_contract_version=2),
    lambda: SemanticIndexSpec("../escape", 3), lambda: VectorFilters(drawer="tasks"),
    lambda: VectorFilters(source_ids=["a"]), lambda: VectorFilters(source_ids=("a", "a")),
    lambda: VectorFilters(representations=("unknown",)), lambda: record(vector=(float("nan"),)),
    lambda: record(vector=[1, 0, 0]), lambda: record(source_version_hash="not-a-hash"),
])
def test_invalid_typed_contract(factory):
    with pytest.raises(VectorIndexError):
        factory()


def test_unit_normalization_validation(tmp_path):
    for value in (ExactFlatBackend(), SQLiteVectorBackend(tmp_path)):
        value.open(replace(SPEC, normalization="unit"))
        with pytest.raises(VectorIndexError, match="unit normalization"):
            value.upsert([record(vector=(2, 0, 0))])
        value.upsert([record()])
        with pytest.raises(VectorIndexError, match="unit normalization"):
            value.search(query((2, 0, 0)))
        value.close()


def test_numeric_representation_is_canonical(backend):
    first = record(vector=(1, 0, 0))
    second = record(vector=(1.0, 0.0, 0.0))
    backend.upsert([first])
    before = backend.stats().corpus_manifest_hash
    assert backend.upsert([second]).reused == 1
    assert backend.stats().corpus_manifest_hash == before


def test_persistence_and_incompatible_manifests(tmp_path):
    value = SQLiteVectorBackend(tmp_path)
    value.open(SPEC)
    value.upsert([record()])
    before = value.stats()
    value.close()
    for change in ({"dimensions": 4}, {"metric": "dot"}, {"normalization": "unit"},
                   {"representation_version": "2"}, {"representations": ("atomic",)},
                   {"configuration_hash": "sha256:" + "1" * 64},
                   {"selected_source_manifest_hash": "sha256:" + "2" * 64},
                   {"ignore_rules_hash": "sha256:" + "3" * 64}):
        with pytest.raises(VectorIndexIncompatible, match="mismatch"):
            value.open(replace(SPEC, **change))
    value.open(SPEC)
    assert value.stats() == before
    assert value.search(query()).hits[0].record == record()
    value.close()
    value.open(replace(SPEC, embedding_profile_fingerprint="sha256:" + "e" * 64))
    assert value.stats().records == 0
    value.close()


@pytest.mark.parametrize("corruption", ["payload", "identity", "manifest", "backend", "manifest_type", "invalid_json"])
def test_corruption_detected_and_not_silently_reused(tmp_path, corruption):
    value = SQLiteVectorBackend(tmp_path)
    value.open(SPEC)
    value.upsert([record()])
    connection = value._connection
    if corruption == "payload":
        row = asdict(record(vector=(0, 1, 0)))
        connection.execute("UPDATE vectors SET payload=?", (json.dumps(row),))
    elif corruption == "identity":
        connection.execute("UPDATE vectors SET record_id='wrong'")
    elif corruption == "manifest":
        connection.execute("DELETE FROM vector_manifest")
    elif corruption in ("manifest_type", "invalid_json"):
        connection.execute("UPDATE vector_manifest SET payload=?", ("[]" if corruption == "manifest_type" else "{",))
    else:
        manifest = json.loads(connection.execute("SELECT payload FROM vector_manifest").fetchone()[0])
        manifest["backend"] = "another-backend"
        connection.execute("UPDATE vector_manifest SET payload=?", (json.dumps(manifest),))
    assert not value.verify().valid
    value.close()
    with pytest.raises(VectorIndexIncompatible):
        value.open(SPEC)


def test_sqlite_crash_rolls_back_public_rebuild(tmp_path):
    value = SQLiteVectorBackend(tmp_path)
    value.open(SPEC)
    value.upsert([record()])
    before = value.stats().corpus_manifest_hash
    value.close()
    script = '''
import os, sys
from tessera.vector_backend import SemanticIndexSpec, VectorRecord
from tessera.vector_sqlite import SQLiteVectorBackend
b=SQLiteVectorBackend(sys.argv[1]); b.open(SemanticIndexSpec(sys.argv[2], 3))
b._connection.set_trace_callback(lambda sql: os._exit(42) if sql.startswith('UPDATE vector_manifest') else None)
b.rebuild([VectorRecord('new','doc-new',sys.argv[3],sys.argv[2],'source','1',(0,1,0))])
'''
    completed = subprocess.run([sys.executable, "-c", script, str(tmp_path), PROFILE, VERSION])
    assert completed.returncode == 42
    value.open(SPEC)
    assert value.stats().corpus_manifest_hash == before
    assert value.verify().valid
    value.close()


def test_threaded_writes_and_snapshot_reads(backend):
    def write(i):
        backend.replace_source("doc-" + str(i), [record(str(i))])
        result = backend.search(query(top_k=100))
        assert len(set(ids(result))) == len(result.hits)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, range(16)))
    assert backend.stats().records == 16
    assert backend.verify().valid


def test_separate_sqlite_instances_do_not_lose_updates(tmp_path):
    instances = [SQLiteVectorBackend(tmp_path) for _ in range(3)]
    for instance in instances:
        instance.open(SPEC)
    def write(i):
        instances[i % 3].upsert([record(str(i))])
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(write, range(18)))
    assert all(instance.stats().records == 18 for instance in instances)
    for instance in instances:
        instance.close()


def test_symlink_is_rejected_without_source_mutation(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    path = tmp_path / "index"
    path.symlink_to(source, target_is_directory=True)
    with pytest.raises(VectorIndexError, match="symlink"):
        SQLiteVectorBackend(path).open(SPEC)
    assert list(source.iterdir()) == []


def test_semantic_rebuild_isolated_from_canonical_and_lexical_state(tmp_path):
    from tessera import TesseraEngine
    store = tmp_path / "memories"
    store.mkdir()
    source = store / "alpha.md"
    source.write_text("# Alpha guide\n\nTelemetry retry schedule is thirty seconds.\n")
    engine = TesseraEngine(storage_dir=str(store))
    engine.build_index()
    before_files = {str(p): p.read_bytes() for p in store.rglob("*") if p.is_file()}
    before_hits = engine.retrieve_context("Telemetry retry schedule")
    assert before_hits
    value = SQLiteVectorBackend(store / ".tessera_index")
    value.open(SPEC)
    value.rebuild([record()])
    value.replace_source("doc-a", [])
    value.close()
    for path, payload in before_files.items():
        assert Path(path).read_bytes() == payload
    assert engine.retrieve_context("Telemetry retry schedule") == before_hits
    value.path.write_bytes(b"deliberately corrupt optional semantic state")
    reopened_engine = TesseraEngine(storage_dir=str(store))
    reopened_engine.build_index()
    assert "Telemetry" in json.dumps(reopened_engine.retrieve_context("Telemetry retry schedule"))
    assert source.read_bytes() == before_files[str(source)]


def test_base_deterministic_imports_do_not_load_semantic_adapters():
    script = "import tessera, tessera.cli, sys; assert 'tessera.vector_backend' not in sys.modules; assert 'tessera.vector_sqlite' not in sys.modules; assert not any(x in sys.modules for x in ('faiss','lancedb','chromadb','sentence_transformers','torch'))"
    subprocess.run([sys.executable, "-c", script], check=True)


def test_huge_integer_is_rejected_actionably(backend):
    with pytest.raises(VectorIndexError):
        backend.search(query((10 ** 1000, 0, 0)))


def test_sqlite_journal_symlink_is_rejected(tmp_path):
    value = SQLiteVectorBackend(tmp_path / "index")
    value.open(SPEC)
    path = value.path
    value.close()
    source = tmp_path / "source.txt"
    source.write_text("canonical source bytes")
    Path(str(path) + "-journal").symlink_to(source)
    with pytest.raises(VectorIndexError, match="symlink"):
        value.open(SPEC)
    assert source.read_text() == "canonical source bytes"
