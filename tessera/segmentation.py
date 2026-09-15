"""Deterministic, rebuildable structural segmentation for source documents.

Segments are derived index objects. The complete source document remains the
authoritative object and the only object returned as a memory result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple


SEGMENTATION_SCHEMA_VERSION = 1
SEGMENT_NODE_TYPE = "source_segment"
MAX_SEGMENT_CHARS = 1800
MIN_DOCUMENT_CHARS = 1000
MIN_DOCUMENT_LINES = 24
ATOMIC_MEMORY_MIN_CHARS = 4000
ATOMIC_MEMORY_MIN_LINES = 80


@dataclass(frozen=True)
class SourceSegment:
    """One addressable span derived from a complete source document."""

    segment_id: str
    parent_memory_id: str
    document_id: str
    document_hash: str
    source_path: str
    source_format: str
    ordinal: int
    start_line: int
    end_line: int
    text: str
    heading: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _body_start_line(raw_text: str, body: str) -> int:
    offset = raw_text.find(body)
    if offset < 0:
        return 1
    return raw_text.count("\n", 0, offset) + 1


def _nonblank_bounds(lines: Sequence[str], start: int, end: int) -> Optional[Tuple[int, int]]:
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return (start, end) if start < end else None


def _heading_blocks(lines: Sequence[str]) -> List[Tuple[int, int, Optional[str]]]:
    headings = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line.rstrip("\r\n"))
        if match:
            headings.append((index, match.group(1).strip()))
    if len(headings) < 2:
        return []

    blocks: List[Tuple[int, int, Optional[str]]] = []
    first = headings[0][0]
    if _nonblank_bounds(lines, 0, first):
        # Keep a preamble with the first named section so it cannot become an
        # isolated, context-free pseudo-memory.
        first = 0
    for position, (heading_index, title) in enumerate(headings):
        start = first if position == 0 else heading_index
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        bounds = _nonblank_bounds(lines, start, end)
        if bounds:
            block_lines = lines[bounds[0] : bounds[1]]
            if len(block_lines) == 1 and re.match(r"^\s{0,3}#{1,6}\s+", block_lines[0]):
                continue
            blocks.append((bounds[0], bounds[1], title))
    return blocks


def _paragraph_blocks(lines: Sequence[str]) -> List[Tuple[int, int, Optional[str]]]:
    blocks: List[Tuple[int, int, Optional[str]]] = []
    start: Optional[int] = None
    for index, line in enumerate(lines):
        if line.strip() and start is None:
            start = index
        if not line.strip() and start is not None:
            blocks.append((start, index, None))
            start = None
    if start is not None:
        blocks.append((start, len(lines), None))
    return blocks


def _split_oversized_block(
    lines: Sequence[str], block: Tuple[int, int, Optional[str]]
) -> List[Tuple[int, int, Optional[str]]]:
    start, end, heading = block
    pieces: List[Tuple[int, int, Optional[str]]] = []
    cursor = start
    while cursor < end:
        piece_end = cursor
        size = 0
        while piece_end < end:
            candidate_size = size + len(lines[piece_end])
            if piece_end > cursor and candidate_size > MAX_SEGMENT_CHARS:
                break
            size = candidate_size
            piece_end += 1
        pieces.append((cursor, piece_end, heading if cursor == start else None))
        cursor = piece_end
    return pieces


def _pack_paragraphs(
    lines: Sequence[str], blocks: Sequence[Tuple[int, int, Optional[str]]]
) -> List[Tuple[int, int, Optional[str]]]:
    packed: List[Tuple[int, int, Optional[str]]] = []
    current: Optional[Tuple[int, int, Optional[str]]] = None
    for block in blocks:
        start, end, heading = block
        block_size = len("".join(lines[start:end]))
        if block_size > MAX_SEGMENT_CHARS:
            if current:
                packed.append(current)
                current = None
            packed.extend(_split_oversized_block(lines, block))
            continue
        if current is None:
            current = block
            continue
        combined_size = len("".join(lines[current[0] : end]))
        if combined_size <= MAX_SEGMENT_CHARS:
            current = (current[0], end, current[2] or heading)
        else:
            packed.append(current)
            current = block
    if current:
        packed.append(current)
    return packed


def segment_source_document(raw_text: str, body: str, canonical: Any) -> List[SourceSegment]:
    """Return deterministic source spans for a document that benefits from them.

    Short native memory cards stay atomic. Structured documents use Markdown
    headings; long unstructured Markdown or text uses bounded paragraph/line
    windows. Returning fewer than two useful spans is equivalent to no
    segmentation.
    """

    lines = body.splitlines(keepends=True)
    nonblank_chars = len(body.strip())
    document_type = canonical.classification.document_type
    if document_type == "memory":
        if nonblank_chars < ATOMIC_MEMORY_MIN_CHARS and len(lines) < ATOMIC_MEMORY_MIN_LINES:
            return []
    elif nonblank_chars < MIN_DOCUMENT_CHARS and len(lines) < MIN_DOCUMENT_LINES:
        return []

    blocks = _heading_blocks(lines)
    if blocks:
        expanded = []
        for block in blocks:
            expanded.extend(_split_oversized_block(lines, block))
        blocks = expanded
    else:
        blocks = _pack_paragraphs(lines, _paragraph_blocks(lines))
    if len(blocks) < 2:
        return []

    body_start = _body_start_line(raw_text, body)
    segments: List[SourceSegment] = []
    for ordinal, (start, end, heading) in enumerate(blocks, 1):
        bounds = _nonblank_bounds(lines, start, end)
        if not bounds:
            continue
        start, end = bounds
        text = "".join(lines[start:end]).strip()
        if not text:
            continue
        start_line = body_start + start
        end_line = body_start + end - 1
        fingerprint = hashlib.sha256(
            f"{canonical.source.document_id}|{start_line}|{end_line}|{text}".encode("utf-8")
        ).hexdigest()[:12]
        segments.append(
            SourceSegment(
                segment_id=f"seg_{canonical.source.document_id}_{fingerprint}",
                parent_memory_id=canonical.identity.id,
                document_id=canonical.source.document_id,
                document_hash=canonical.source.document_hash,
                source_path=canonical.source.path,
                source_format=canonical.source.format,
                ordinal=ordinal,
                start_line=start_line,
                end_line=end_line,
                text=text,
                heading=heading,
            )
        )
    return segments if len(segments) >= 2 else []
