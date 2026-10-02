"""Independent cKDTree candidate selection and inherited lifecycle contract."""
from dataclasses import replace
import subprocess
import sys

import pytest

from tessera.vector_backend import (ExactFlatBackend, SemanticIndexSpec, VectorFilters,
                                    VectorIndexError, VectorIndexIncompatible, VectorSearchRequest)
from tessera.vector_ckdtree import CKDTreeVectorBackend
from test_issue_265_vector_backends import PROFILE, SPEC, query, record


@pytest.mark.parametrize("epsilon", [0, 0.5])
@pytest.mark.parametrize("metric", ["cosine", "l2"])
def test_tree_independent_analytic_neighbors(epsilon, metric):
    tree, flat = CKDTreeVectorBackend(epsilon=epsilon), ExactFlatBackend()
    for b in (tree, flat):
        b.open(replace(SPEC, metric=metric))
        b.upsert([record(str(i), (1, i * .17, i * -.03)) for i in range(60)])
    for filters in (VectorFilters(), VectorFilters(source_ids=("doc-1", "doc-31", "doc-43"))):
        request = query(top_k=2, filters=filters)
        actual, expected = tree.search(request), flat.search(request)
        assert [h.record.record_id for h in actual.hits] == [h.record.record_id for h in expected.hits]
        assert actual.corpus_manifest_hash == expected.corpus_manifest_hash
        assert [h.backend_score for h in actual.hits] == [h.backend_score for h in expected.hits]
        assert tree.search(request) == actual
    assert tree.capabilities().exact_or_ann == ("ann" if epsilon else "exact")
    tree.close()
    assert not tree._trees


def test_tree_source_lifecycle_and_cache_bound():
    tree = CKDTreeVectorBackend()
    tree.open(SPEC)
    original = record()
    tree.upsert([original, record("b", representation="source")])
    old = tree.search(query())
    for i in range(8):
        tree.search(query(filters=VectorFilters(source_ids=("doc-" + str(i),))))
    assert len(tree._trees) == 4
    moved = replace(original, source_path="moved/a.md")
    tree.replace_source("doc-a", [moved])
    assert not tree._trees
    result = tree.search(query())
    assert any(h.record.source_path == "moved/a.md" for h in result.hits)
    assert old.corpus_manifest_hash != result.corpus_manifest_hash
    tree.replace_source("doc-a", [])
    assert all(h.record.source_document_id != "doc-a" for h in tree.search(query()).hits)
    clean = CKDTreeVectorBackend()
    clean.open(SPEC)
    clean.rebuild([record("b", representation="source")])
    assert tree.search(query()) == clean.search(query())
    before = tree.search(query())
    with pytest.raises(VectorIndexError):
        tree.rebuild([record(vector=(1, 2))])
    assert tree.search(query()) == before
    tree.rebuild([])
    assert tree.search(query()).hits == ()


def test_tree_tie_membership_repeatability_is_honest():
    tree = CKDTreeVectorBackend()
    tree.open(SPEC)
    tree.upsert([record(str(i)) for i in range(30)])
    result = tree.search(query(top_k=5))
    assert len(result.hits) == 5
    assert [h.record.record_id for h in result.hits] == sorted(h.record.record_id for h in result.hits)
    assert all(h.backend_score == 1 for h in result.hits)
    assert tree.search(query(top_k=5)) == result


@pytest.mark.parametrize("epsilon", [-1, 3, True, float("nan"), float("inf")])
def test_bad_epsilon(epsilon):
    with pytest.raises(VectorIndexError):
        CKDTreeVectorBackend(epsilon=epsilon)


def test_unsupported_dot_and_profile_validation():
    tree = CKDTreeVectorBackend()
    with pytest.raises(VectorIndexIncompatible, match="cosine and l2"):
        tree.open(replace(SPEC, metric="dot"))
    tree.open(SPEC)
    with pytest.raises(VectorIndexIncompatible):
        tree.search(VectorSearchRequest((1, 0, 0), "sha256:" + "c" * 64))
    with pytest.raises(VectorIndexError):
        tree.search(query((1, 2)))


def test_optional_tree_import_is_lazy():
    subprocess.run([sys.executable, "-c", "import tessera, sys; assert 'tessera.vector_ckdtree' not in sys.modules; import tessera.vector_ckdtree as v; v.CKDTreeVectorBackend(); assert v.CKDTreeVectorBackend()._tree_type is None"], check=True)


def test_failed_generation_keeps_warm_tree_and_source_snapshot():
    tree = CKDTreeVectorBackend()
    tree.open(SPEC)
    tree.upsert([record()])
    before = tree.search(query())
    def interrupted():
        yield record("new")
        raise RuntimeError("interrupted generation")
    with pytest.raises(RuntimeError):
        tree.rebuild(interrupted())
    assert tree.search(query()) == before


def test_missing_optional_spatial_dependency_is_actionable(monkeypatch):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name == "scipy.spatial":
            raise ImportError("simulated missing optional dependency")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    with pytest.raises(VectorIndexError, match="requires SciPy"):
        CKDTreeVectorBackend().open(SPEC)
