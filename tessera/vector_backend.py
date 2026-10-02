"""Experimental, opt-in vector mechanics. No encoders or Engine integration.

All scores are ranking signals, never confidence, authority or truth.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional, Protocol, Tuple, runtime_checkable

CONTRACT_VERSION = 1
REPRESENTATIONS = ("atomic", "source", "segment")
DRAWERS = ("facts", "preferences", "insights")


class VectorIndexError(ValueError):
    """Invalid vectors, incompatible derived state or an unopened backend."""


class VectorIndexIncompatible(VectorIndexError):
    """Rebuild/migrate derived vectors; never silently reuse another space."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value):
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value, name, optional=False):
    if optional and value is None:
        return
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise VectorIndexError(f"{name} must be a non-empty string of at most 4096 characters")


def _fingerprint(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise VectorIndexError(f"{name} must be a lowercase sha256 fingerprint")


def _choices(value, name, allowed=None):
    if not isinstance(value, tuple) or len(value) > 256:
        raise VectorIndexError(f"{name} must be a tuple of at most 256 distinct values")
    for item in value:
        _text(item, name)
        if allowed is not None and item not in allowed:
            raise VectorIndexError(f"unsupported {name}: {item}")
    if len(set(value)) != len(value):
        raise VectorIndexError(f"{name} contains duplicates")


def _vector(value, spec):
    if not isinstance(value, tuple) or len(value) != spec.dimensions:
        raise VectorIndexError(f"vector dimensions must equal {spec.dimensions}")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
           abs(x) > 1e100 or not math.isfinite(x) for x in value):
        raise VectorIndexError("vectors require finite numeric components with magnitude <= 1e100")
    norm = math.hypot(*value)
    if spec.metric == "cosine" and norm == 0:
        raise VectorIndexError("cosine vectors must have non-zero norm")
    if spec.normalization == "unit" and not math.isclose(norm, 1.0, abs_tol=1e-6):
        raise VectorIndexError("unit normalization requires norm 1 (tolerance 1e-6)")


@dataclass(frozen=True)
class SemanticIndexSpec:
    embedding_profile_fingerprint: str
    dimensions: int
    metric: str = "cosine"
    normalization: str = "none"
    representations: Tuple[str, ...] = REPRESENTATIONS
    representation_version: str = "1"
    selected_source_manifest_hash: Optional[str] = None
    ignore_rules_hash: Optional[str] = None
    configuration_hash: Optional[str] = None
    semantic_contract_version: int = CONTRACT_VERSION

    def __post_init__(self):
        _fingerprint(self.embedding_profile_fingerprint, "embedding_profile_fingerprint")
        if type(self.dimensions) is not int or not 1 <= self.dimensions <= 65536:
            raise VectorIndexError("dimensions must be an integer between 1 and 65536")
        if self.metric not in ("cosine", "dot", "l2") or self.normalization not in ("none", "unit"):
            raise VectorIndexError("unsupported metric or normalization")
        _choices(self.representations, "representations", REPRESENTATIONS)
        if not self.representations:
            raise VectorIndexError("at least one representation is required")
        _text(self.representation_version, "representation_version")
        for name in ("selected_source_manifest_hash", "ignore_rules_hash", "configuration_hash"):
            if getattr(self, name) is not None:
                _fingerprint(getattr(self, name), name)
        if type(self.semantic_contract_version) is not int or self.semantic_contract_version != CONTRACT_VERSION:
            raise VectorIndexIncompatible("unsupported semantic contract; rebuild with a supported contract")


@dataclass(frozen=True)
class VectorRecord:
    canonical_id: str
    source_document_id: str
    source_version_hash: str
    embedding_profile_fingerprint: str
    representation: str
    representation_version: str
    vector: Tuple[float, ...]
    # Segment identity is independent of path and distinguishes sibling segments.
    representation_id: str = "whole"
    source_path: Optional[str] = None
    project_scope: Optional[str] = None
    drawer: Optional[str] = None
    document_type: Optional[str] = None
    evidence_ids: Tuple[str, ...] = ()

    def __post_init__(self):
        for name in ("canonical_id", "source_document_id", "representation_version", "representation_id"):
            _text(getattr(self, name), name)
        for name in ("source_version_hash", "embedding_profile_fingerprint"):
            _fingerprint(getattr(self, name), name)
        for name in ("source_path", "project_scope", "document_type"):
            _text(getattr(self, name), name, optional=True)
        if self.representation not in REPRESENTATIONS or self.drawer not in (*DRAWERS, None):
            raise VectorIndexError("unsupported representation or drawer")
        _choices(self.evidence_ids, "evidence_ids")
        if not isinstance(self.vector, tuple) or not 1 <= len(self.vector) <= 65536:
            raise VectorIndexError("vector must be an immutable tuple with 1 to 65536 dimensions")
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
               abs(x) > 1e100 or not math.isfinite(x) for x in self.vector):
            raise VectorIndexError("vector components must be finite numbers with magnitude <= 1e100")
        object.__setattr__(self, "vector", tuple(float(x) for x in self.vector))

    @property
    def record_id(self):
        return "vec_" + _hash([self.canonical_id, self.source_document_id,
                              self.source_version_hash, self.embedding_profile_fingerprint,
                              self.representation, self.representation_version,
                              self.representation_id]).split(":")[1]

    @property
    def dimensions(self):
        return len(self.vector)


@dataclass(frozen=True)
class VectorFilters:
    representations: Tuple[str, ...] = ()
    project_scope: Optional[str] = None
    drawer: Optional[str] = None
    document_type: Optional[str] = None
    source_ids: Tuple[str, ...] = ()

    def __post_init__(self):
        _choices(self.representations, "representations", REPRESENTATIONS)
        _choices(self.source_ids, "source_ids")
        _text(self.project_scope, "project_scope", optional=True)
        _text(self.document_type, "document_type", optional=True)
        if self.drawer not in (*DRAWERS, None):
            raise VectorIndexError("unsupported drawer")

    def matches(self, record):
        return ((not self.representations or record.representation in self.representations)
                and (not self.source_ids or record.source_document_id in self.source_ids)
                and all(getattr(self, key) is None or getattr(self, key) == getattr(record, key)
                        for key in ("project_scope", "drawer", "document_type")))


@dataclass(frozen=True)
class VectorSearchRequest:
    query_vector: Tuple[float, ...]
    embedding_profile_fingerprint: str
    top_k: int = 20
    filters: VectorFilters = field(default_factory=VectorFilters)

    def validate(self, spec):
        if self.embedding_profile_fingerprint != spec.embedding_profile_fingerprint:
            raise VectorIndexIncompatible("query embedding profile mismatch; generate a compatible query vector")
        if type(self.top_k) is not int or not 1 <= self.top_k <= 10000:
            raise VectorIndexError("top_k must be an integer between 1 and 10000")
        if not isinstance(self.filters, VectorFilters):
            raise VectorIndexError("filters must be VectorFilters")
        _vector(self.query_vector, spec)


@dataclass(frozen=True)
class VectorBackendCapabilities:
    backend: str
    backend_version: str
    metric: Tuple[str, ...] = ("cosine", "dot", "l2")
    exact_or_ann: str = "exact"
    metadata_filtering: bool = True
    persistence: bool = False
    concurrent_reads: bool = True
    concurrent_writes: str = "serialized"


@dataclass(frozen=True)
class VectorSearchHit:
    record: VectorRecord
    backend_score: float


@dataclass(frozen=True)
class VectorSearchResult:
    hits: Tuple[VectorSearchHit, ...]
    backend: str
    metric: str
    score_meaning: str
    # A reader can identify the exact snapshot it searched.
    corpus_manifest_hash: str


@dataclass(frozen=True)
class MutationResult:
    upserted: int = 0
    removed: int = 0
    reused: int = 0


@dataclass(frozen=True)
class VectorIndexStats:
    records: int
    corpus_manifest_hash: str
    disk_bytes: int = 0


@dataclass(frozen=True)
class VectorIndexVerification:
    valid: bool
    errors: Tuple[str, ...] = ()


@runtime_checkable
class VectorBackend(Protocol):
    def capabilities(self) -> VectorBackendCapabilities: ...
    def open(self, index_spec: SemanticIndexSpec) -> None: ...
    def upsert(self, records: Iterable[VectorRecord]) -> MutationResult: ...
    def delete(self, record_ids: Iterable[str]) -> MutationResult: ...
    def replace_source(self, source_document_id: str, records: Iterable[VectorRecord]) -> MutationResult: ...
    def rebuild(self, records: Iterable[VectorRecord]) -> MutationResult: ...
    def search(self, request: VectorSearchRequest) -> VectorSearchResult: ...
    def stats(self) -> VectorIndexStats: ...
    def verify(self) -> VectorIndexVerification: ...
    def close(self) -> None: ...


def validate_records(records, spec):
    batch = tuple(records)
    ids = set()
    for record in batch:
        if not isinstance(record, VectorRecord):
            raise VectorIndexError("records must be VectorRecord instances")
        if record.embedding_profile_fingerprint != spec.embedding_profile_fingerprint:
            raise VectorIndexIncompatible("record embedding profile mismatch; rebuild or use another namespace")
        if (record.representation not in spec.representations or
                record.representation_version != spec.representation_version):
            raise VectorIndexIncompatible("representation mismatch; rebuild or use another namespace")
        _vector(record.vector, spec)
        if record.record_id in ids:
            raise VectorIndexError("duplicate vector record ID in one batch")
        ids.add(record.record_id)
    return batch


def corpus_hash(records):
    return _hash([asdict(r) for r in sorted(records, key=lambda r: r.record_id)])


def search_snapshot(records, request, spec, backend):
    request.validate(spec)
    hits = []
    for record in records:
        if not request.filters.matches(record):
            continue
        a, b = request.query_vector, record.vector
        if spec.metric == "cosine":
            na, nb = math.hypot(*a), math.hypot(*b)
            score = max(-1.0, min(1.0, math.fsum((x / na) * (y / nb) for x, y in zip(a, b))))
        elif spec.metric == "dot":
            score = math.fsum(x * y for x, y in zip(a, b))
        else:
            score = -math.fsum((x - y) ** 2 for x, y in zip(a, b))
        hits.append(VectorSearchHit(record, score))
    hits.sort(key=lambda hit: (-hit.backend_score, hit.record.record_id))
    meaning = {"cosine": "cosine_similarity", "dot": "dot_product", "l2": "negative_squared_l2"}[spec.metric]
    return VectorSearchResult(tuple(hits[:request.top_k]), backend, spec.metric, meaning, corpus_hash(records))


class ExactFlatBackend:
    """Small-fixture correctness oracle; instance lifetime only, serialized access."""

    def __init__(self):
        self._lock = threading.RLock()
        self._spec = None
        self._records = {}

    def capabilities(self):
        return VectorBackendCapabilities("exact-flat", "1")

    def _require_open(self):
        if self._spec is None:
            raise VectorIndexError("backend is closed; call open(index_spec)")
        return self._spec

    def open(self, index_spec):
        if not isinstance(index_spec, SemanticIndexSpec):
            raise VectorIndexError("index_spec must be SemanticIndexSpec")
        with self._lock:
            if self._spec is not None and self._spec != index_spec:
                raise VectorIndexIncompatible("index spec mismatch; close and rebuild in a fresh namespace")
            self._spec = index_spec

    def _mutate(self, records=(), record_ids=(), source_id=None, rebuild=False):
        with self._lock:
            batch = validate_records(records, self._require_open())
            if source_id is not None:
                _text(source_id, "source_document_id")
                if any(r.source_document_id != source_id for r in batch):
                    raise VectorIndexError("replace_source batch contains another source")
            old = self._records
            ids = set(record_ids)
            if any(not isinstance(i, str) or not re.fullmatch(r"vec_[0-9a-f]{64}", i) for i in ids):
                raise VectorIndexError("invalid vector record ID")
            new = {key: r for key, r in old.items() if not rebuild and key not in ids and
                   (source_id is None or r.source_document_id != source_id)}
            new.update((r.record_id, r) for r in batch)
            result = MutationResult(sum(old.get(r.record_id) != r for r in batch),
                                    len(set(old) - set(new)),
                                    sum(old.get(r.record_id) == r for r in batch))
            self._records = new  # one commit point, including generator/validation failures
            return result

    def upsert(self, records):
        """Upsert exact identities. Use replace_source for authoritative source versions."""
        return self._mutate(records)

    def delete(self, record_ids):
        return self._mutate(record_ids=record_ids)

    def replace_source(self, source_document_id, records):
        return self._mutate(records, source_id=source_document_id)

    def rebuild(self, records):
        return self._mutate(records, rebuild=True)

    def search(self, request):
        with self._lock:
            spec = self._require_open()
            records = tuple(self._records.values())
        return search_snapshot(records, request, spec, self.capabilities().backend)

    def stats(self):
        with self._lock:
            self._require_open()
            return VectorIndexStats(len(self._records), corpus_hash(self._records.values()))

    def verify(self):
        with self._lock:
            validate_records(self._records.values(), self._require_open())
            return VectorIndexVerification(True)

    def close(self):
        with self._lock:
            self._spec = None
            self._records = {}
