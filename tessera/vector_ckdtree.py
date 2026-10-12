"""Opt-in, in-memory SciPy cKDTree mechanics candidate (exact or approximate).

No SciPy spatial import occurs until explicit open(). No persistence or model
inference is provided. Positive epsilon enables approximate tree traversal;
this is not a claim that KD trees suit high-dimensional production embeddings.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
import math

from .vector_backend import (
    ExactFlatBackend, SemanticIndexSpec, VectorBackendCapabilities,
    VectorIndexError, VectorIndexIncompatible, corpus_hash, search_snapshot,
)


class CKDTreeVectorBackend(ExactFlatBackend):
    """Independent neighbor selection, shared auditable returned-score semantics.

    Filters are applied before tree construction, never after a limited Top-K.
    At most four filtered trees are retained. Source updates invalidate them;
    cold builds (including filtering/normalization) are paid by the first query.
    All instance operations are serialized. Same-source updates are last-write
    wins as for the reference. Exact boundary-tie membership may differ from
    the flat oracle; selected candidates are sorted by score then record ID.
    """

    def __init__(self, *, epsilon=0.5):
        super().__init__()
        if (isinstance(epsilon, bool) or not isinstance(epsilon, (int, float)) or
                not math.isfinite(epsilon) or not 0 <= epsilon <= 2):
            raise VectorIndexError("epsilon must be finite and between 0 and 2")
        self.epsilon = float(epsilon)
        self._trees = OrderedDict()
        self._corpus_hash = None
        self._tree_type = None

    def capabilities(self):
        return VectorBackendCapabilities("scipy-ckdtree", "1", metric=("cosine", "l2"),
                                         exact_or_ann="ann" if self.epsilon else "exact")

    def open(self, index_spec):
        if not isinstance(index_spec, SemanticIndexSpec):
            raise VectorIndexError("index_spec must be SemanticIndexSpec")
        if index_spec.metric not in self.capabilities().metric:
            raise VectorIndexIncompatible("cKDTree supports cosine and l2 only; select a compatible backend")
        with self._lock:
            try:
                from scipy.spatial import cKDTree
            except ImportError as exc:
                raise VectorIndexError("cKDTree requires SciPy; use ExactFlatBackend or install the optional SciPy dependency") from exc
            super().open(index_spec)
            self._tree_type = cKDTree

    def _mutate(self, records=(), record_ids=(), source_id=None, rebuild=False):
        with self._lock:
            result = super()._mutate(records, record_ids, source_id, rebuild)
            if result.upserted or result.removed:
                self._trees.clear()
                self._corpus_hash = None
            return result

    @staticmethod
    def _coordinates(vector, metric):
        if metric == "cosine":
            norm = math.hypot(*vector)
            return tuple(x / norm for x in vector)
        return vector

    def search(self, request):
        with self._lock:
            spec = self._require_open()
            request.validate(spec)
            if self._corpus_hash is None:
                self._corpus_hash = corpus_hash(self._records.values())
            cached = self._trees.get(request.filters)
            if cached is None:
                rows = tuple(sorted((r for r in self._records.values() if request.filters.matches(r)),
                                    key=lambda r: r.record_id))
                tree = (self._tree_type([self._coordinates(r.vector, spec.metric) for r in rows],
                                        leafsize=16, compact_nodes=True, balanced_tree=True,
                                        copy_data=True) if rows else None)
                cached = (rows, tree)
                self._trees[request.filters] = cached
                if len(self._trees) > 4:
                    self._trees.popitem(last=False)
            self._trees.move_to_end(request.filters)
            rows, tree = cached
            if tree is None:
                candidates = ()
            else:
                k = min(request.top_k, len(rows))
                _, indices = tree.query(self._coordinates(request.query_vector, spec.metric),
                                        k=list(range(1, k + 1)), eps=self.epsilon, p=2)
                candidates = tuple(rows[int(index)] for index in indices)
            result = search_snapshot(candidates, request, spec, self.capabilities().backend)
            return replace(result, corpus_manifest_hash=self._corpus_hash)

    def close(self):
        with self._lock:
            self._trees.clear()
            self._corpus_hash = None
            self._tree_type = None
            super().close()
