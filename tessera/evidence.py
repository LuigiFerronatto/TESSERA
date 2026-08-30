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
    """One traceable claim-to-source record.

    ``evidence_id`` is deterministic for a memory/source-version/span tuple.
    Editing the source creates a new evidence version while preserving the
    stable memory and document identities supplied by Canonical Metadata.
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
    content_hash: str,
    start_line: Optional[int],
    end_line: Optional[int],
) -> str:
    payload = "|".join(
        [
            memory_id,
            document_id,
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
) -> EvidenceRecord:
    """Build a deterministic evidence record from Canonical Metadata."""
    source = metadata.source
    span = source.span
    fingerprint = _evidence_fingerprint(
        metadata.identity.id,
        source.document_id,
        source.content_hash,
        span.start_line,
        span.end_line,
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
        span=EvidenceSpan(span.start_line, span.end_line),
        fingerprint=fingerprint,
        extraction=EvidenceExtraction(method=extraction_method, inferred=inferred),
    )


def _split_body_for_hash(raw_text: str) -> str:
    """Use Canonical's parser so freshness checks follow exactly its semantics."""
    from .canonical import _split_markdown

    _frontmatter, body = _split_markdown(raw_text)
    return body


def verify_evidence_freshness(
    record: EvidenceRecord,
    storage_dir: str,
) -> EvidenceFreshness:
    """Verify whether source evidence still points to the same source version.

    Statuses:
      - ``fresh``: file exists and both document/content hashes match.
      - ``content_changed``: body changed.
      - ``metadata_changed``: whole document changed but body stayed identical.
      - ``missing_source``: source path no longer exists at the recorded path.

    Rename/move reconciliation is intentionally handled by Canonical stable
    identity before ledger reconstruction; this verifier audits one recorded
    evidence version and does not guess alternate paths.
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
    """Small deterministic in-memory ledger with stable serialization.

    It is intentionally storage-agnostic in Foundation v0.1. Persisting a
    separate authoritative ledger database would violate TESSERA's contract:
    the source files are authoritative and this index must be reconstructible.
    """

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
