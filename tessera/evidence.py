"""Auditable evidence ledger for TESSERA.

Evidence is derived from canonical source metadata and is therefore fully
rebuildable. Source documents remain the source of truth; the ledger never
mutates them and never becomes a competing persistence layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from typing import Any, Dict, Iterable, List, Optional

from .canonical import CanonicalMetadata, compute_sha256


EVIDENCE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EvidenceSpan:
    start_line: Optional[int]
    end_line: Optional[int]


@dataclass(frozen=True)
class EvidenceSource:
    document_id: str
    path: str
    document_hash: str
    content_hash: str
    format: str


@dataclass(frozen=True)
class EvidenceExtraction:
    method: str = "canonical_document"
    inferred: bool = False


@dataclass(frozen=True)
class EvidenceRecord:
    """One traceable claim-to-source-version record.

    ``evidence_id`` is deterministic for a memory/source-version/span tuple.
    Any source-document version change creates a new evidence version while
    stable memory/document identity can remain unchanged.
    """

    schema_version: int
    evidence_id: str
    memory_id: str
    source: EvidenceSource
    span: EvidenceSpan
    fingerprint: str
    extraction: EvidenceExtraction

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceFreshness:
    evidence_id: str
    status: str
    path_exists: bool
    document_hash_matches: bool
    content_hash_matches: bool
    current_document_hash: Optional[str] = None
    current_content_hash: Optional[str] = None

    @property
    def is_fresh(self) -> bool:
        return self.status == "fresh"


def _evidence_fingerprint(
    memory_id: str,
    document_id: str,
    document_hash: str,
    content_hash: str,
    start_line: Optional[int],
    end_line: Optional[int],
) -> str:
    # document_hash is deliberately included: provenance identifies the exact
    # source version, not merely an unchanged body. Frontmatter-only changes
    # can alter semantics/retrieval and must therefore yield a new record.
    payload = "|".join(
        [
            memory_id,
            document_id,
            document_hash,
            content_hash,
            str(start_line or ""),
            str(end_line or ""),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def evidence_from_canonical(
    metadata: CanonicalMetadata,
    *,
    extraction_method: str = "canonical_document",
    inferred: bool = False,
    span: Optional[EvidenceSpan] = None,
) -> EvidenceRecord:
    """Build a deterministic evidence record from Canonical Metadata.

    ``span`` defaults to Canonical's document-level source span. Retrieval can
    pass an exact query-aware span when a specific paragraph/snippet is used as
    evidence, without changing the source or canonical identity.
    """
    source = metadata.source
    resolved_span = span or EvidenceSpan(source.span.start_line, source.span.end_line)
    fingerprint = _evidence_fingerprint(
        metadata.identity.id,
        source.document_id,
        source.document_hash,
        source.content_hash,
        resolved_span.start_line,
        resolved_span.end_line,
    )
    return EvidenceRecord(
        schema_version=EVIDENCE_SCHEMA_VERSION,
        evidence_id=f"ev_{fingerprint[:16]}",
        memory_id=metadata.identity.id,
        source=EvidenceSource(
            document_id=source.document_id,
            path=source.path,
            document_hash=source.document_hash,
            content_hash=source.content_hash,
            format=source.format,
        ),
        span=resolved_span,
        fingerprint=fingerprint,
        extraction=EvidenceExtraction(method=extraction_method, inferred=inferred),
    )


def locate_evidence_span(raw_text: str, evidence_text: str) -> EvidenceSpan:
    """Resolve an exact unambiguous 1-based line span for evidence text.

    Precision is never guessed. If the text is absent *or appears more than
    once*, ``(None, None)`` is returned because the available evidence cannot
    prove which occurrence the retriever intended.
    """
    if not evidence_text:
        return EvidenceSpan(None, None)
    start_offset = raw_text.find(evidence_text)
    if start_offset < 0:
        return EvidenceSpan(None, None)
    if raw_text.find(evidence_text, start_offset + 1) >= 0:
        return EvidenceSpan(None, None)
    end_offset = start_offset + len(evidence_text)
    start_line = raw_text.count("\n", 0, start_offset) + 1
    end_line = raw_text.count("\n", 0, max(start_offset, end_offset - 1)) + 1
    return EvidenceSpan(start_line, end_line)


def evidence_for_text(
    metadata: CanonicalMetadata,
    raw_text: str,
    evidence_text: str,
    *,
    extraction_method: str = "paragraph_lexical",
) -> EvidenceRecord:
    """Create query-aware evidence with an exact span only when provable."""
    span = locate_evidence_span(raw_text, evidence_text)
    return evidence_from_canonical(
        metadata,
        extraction_method=extraction_method,
        inferred=False,
        span=span,
    )


def ledger_from_graph(graph: Any) -> "EvidenceLedger":
    """Rebuild document-level evidence records from an indexed TESSERA graph."""
    ledger = EvidenceLedger()
    for _node_id, data in graph.nodes(data=True):
        canonical = data.get("canonical_metadata")
        if isinstance(canonical, CanonicalMetadata):
            ledger.add(evidence_from_canonical(canonical))
    return ledger


def enrich_retrieval_results(engine: Any, results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach structured provenance to real retrieval results without mutation.

    Every canonical memory gets document-level ``provenance``. Query-specific
    ``evidence`` exists only when ``relevant_evidence`` exists; an unresolved
    or ambiguous source span remains explicitly null rather than fabricated.
    """
    enriched: List[Dict[str, Any]] = []
    for result in results:
        item = dict(result)
        node_id = item.get("id")
        node_data = engine.graph.nodes.get(node_id, {}) if node_id in engine.graph else {}
        canonical = node_data.get("canonical_metadata") if node_data else None
        if not isinstance(canonical, CanonicalMetadata):
            item["provenance"] = None
            item["evidence"] = None
            enriched.append(item)
            continue

        provenance = evidence_from_canonical(canonical)
        item["provenance"] = provenance.to_dict()

        evidence_text = item.get("relevant_evidence")
        if evidence_text:
            filepath = node_data.get("filepath") or item.get("filepath")
            try:
                with open(filepath, "r", encoding="utf-8") as handle:
                    raw_text = handle.read()
                evidence = evidence_for_text(
                    canonical,
                    raw_text,
                    evidence_text,
                    extraction_method=(item.get("evidence_info") or {}).get(
                        "strategy", "paragraph_lexical"
                    ),
                )
                item["evidence"] = evidence.to_dict()
            except (OSError, UnicodeError):
                item["evidence"] = evidence_from_canonical(
                    canonical,
                    extraction_method=(item.get("evidence_info") or {}).get(
                        "strategy", "paragraph_lexical"
                    ),
                    span=EvidenceSpan(None, None),
                ).to_dict()
        else:
            item["evidence"] = None
        enriched.append(item)
    return enriched


def retrieval_result_contract(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the stable machine-readable retrieval contract.

    This is a presentation projection only: it preserves every semantic field
    produced by the Engine and deliberately does not calculate or reorder
    anything.  CLI and MCP use it to avoid surface-specific field loss.
    """
    return dict(result)


def retrieval_results_contract(results: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [retrieval_result_contract(result) for result in results]


def _split_body_for_hash(raw_text: str) -> str:
    """Use Canonical's parser so freshness checks follow exactly its semantics."""
    from .canonical import _split_markdown

    _frontmatter, body = _split_markdown(raw_text)
    return body


def verify_evidence_freshness(
    record: EvidenceRecord,
    storage_dir: str,
) -> EvidenceFreshness:
    """Verify whether evidence still points to the same exact source version.

    Statuses: ``fresh``, ``metadata_changed``, ``content_changed``,
    ``missing_source``.
    """
    full_path = os.path.join(storage_dir, record.source.path.replace("/", os.sep))
    if not os.path.exists(full_path):
        return EvidenceFreshness(
            evidence_id=record.evidence_id,
            status="missing_source",
            path_exists=False,
            document_hash_matches=False,
            content_hash_matches=False,
        )

    with open(full_path, "r", encoding="utf-8") as handle:
        raw_text = handle.read()
    body = _split_body_for_hash(raw_text)
    current_document_hash = compute_sha256(raw_text)
    current_content_hash = compute_sha256(body)
    document_matches = current_document_hash == record.source.document_hash
    content_matches = current_content_hash == record.source.content_hash

    if document_matches and content_matches:
        status = "fresh"
    elif content_matches:
        status = "metadata_changed"
    else:
        status = "content_changed"

    return EvidenceFreshness(
        evidence_id=record.evidence_id,
        status=status,
        path_exists=True,
        document_hash_matches=document_matches,
        content_hash_matches=content_matches,
        current_document_hash=current_document_hash,
        current_content_hash=current_content_hash,
    )


class EvidenceLedger:
    """Deterministic, derived in-memory ledger with stable serialization."""

    def __init__(self, records: Optional[Iterable[EvidenceRecord]] = None) -> None:
        self._records: Dict[str, EvidenceRecord] = {}
        for record in records or ():
            self.add(record)

    def add(self, record: EvidenceRecord) -> None:
        existing = self._records.get(record.evidence_id)
        if existing is not None and existing != record:
            raise ValueError(f"Evidence ID collision: {record.evidence_id}")
        self._records[record.evidence_id] = record

    def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        return self._records.get(evidence_id)

    def for_memory(self, memory_id: str) -> List[EvidenceRecord]:
        return sorted(
            (r for r in self._records.values() if r.memory_id == memory_id),
            key=lambda r: r.evidence_id,
        )

    def to_list(self) -> List[Dict[str, Any]]:
        return [self._records[key].to_dict() for key in sorted(self._records)]

    def __len__(self) -> int:
        return len(self._records)
