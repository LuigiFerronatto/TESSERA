"""Immutable Markdown source episodes and verifiable atomic-memory lineage.

Sources live in the store, outside the disposable index. Their text is never
sanitized/replaced in place. Character ranges address exact content in the
Markdown body, allowing repeated text and Unicode without guessed spans.
"""

from copy import deepcopy
from dataclasses import dataclass
import os
import json
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Sequence

import yaml

from .canonical import CanonicalMetadata, LineageMetadata, compute_sha256, parse_and_normalize
from .evidence import EvidenceRecord, EvidenceSpan, evidence_from_canonical
from .models import Episode, EpisodeTurn, WriteGatingViolationError
from .security import WriteAdmission, WriteResult, validate_memory_path
from .source_formats import split_markdown

EPISODE_DIRECTORY = "_episodes"
TEMPORAL_POSITION_SEMANTICS = "last_supporting_turn_position_within_source_episode"


class LineageValidationError(ValueError):
    """An unresolvable/unsupported reference; no replacement support is invented."""


@dataclass(frozen=True)
class SourceEpisode:
    episode_id: str
    episode: Episode
    filepath: str
    canonical: CanonicalMetadata
    turn_spans: Dict[int, EvidenceSpan]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "filepath": self.filepath,
            "source": evidence_from_canonical(self.canonical).to_dict(),
            "sections": {name: getattr(self.episode, name) for name in ("beginning", "middle", "end")},
            "turns": [
                {"position": turn.position, "role": turn.role, "timestamp": turn.timestamp,
                 "content": turn.content, "span": {
                     "start_line": self.turn_spans[turn.position].start_line,
                     "end_line": self.turn_spans[turn.position].end_line,
                 }}
                for turn in self.episode.turns
            ],
        }


def validate_support(episode: Episode, positions: Sequence[int]) -> List[int]:
    if not isinstance(positions, (list, tuple)):
        raise LineageValidationError("supporting_turns must be an ordered list of source positions")
    if any(type(position) is not int or position < 1 for position in positions):
        raise LineageValidationError("supporting turn positions must be positive integers")
    positions = list(positions)
    if positions != sorted(set(positions)):
        raise LineageValidationError("supporting turns must be unique and increasing")
    available = {turn.position for turn in episode.turns}
    if not set(positions).issubset(available):
        raise LineageValidationError("supporting turn position is absent from the source episode")
    if available and not positions:
        raise LineageValidationError("turn-aware candidates require explicit supporting turns")
    return positions


def _source_path(storage_dir: str, episode_id: str) -> Path:
    if not isinstance(episode_id, str) or not episode_id.strip():
        raise LineageValidationError("source episode ID must be nonempty text")
    identifier = f"{EPISODE_DIRECTORY}/{compute_sha256(episode_id)}"
    validation = validate_memory_path(storage_dir, identifier)
    if not validation.valid or validation.destination is None:
        raise LineageValidationError("source episode path is not contained in the store")
    return validation.destination


def _serialize(episode_id: str, episode: Episode) -> str:
    # Revalidate mutable Episode instances before any persistence.
    episode.__post_init__()
    body = ""

    def append(title: str, content: str) -> Dict[str, Any]:
        nonlocal body
        body += f"## {title}\n"
        start = len(body)
        # Preserve CRLF and non-display control characters losslessly without
        # making canonical text readers normalize the authoritative source.
        encoding = "json_string" if any(ord(char) < 32 and char not in "\n\t" for char in content) else "text"
        body += json.dumps(content, ensure_ascii=False) if encoding == "json_string" else content
        end = len(body)
        body += "\n\n"
        return {"start": start, "end": end, "encoding": encoding}

    sections = {name: append(name.title(), getattr(episode, name)) for name in ("beginning", "middle", "end")}
    turns = [
        {"position": turn.position, "role": turn.role, "timestamp": turn.timestamp,
         "content_range": append(f"Turn {turn.position}", turn.content)}
        for turn in episode.turns
    ]
    metadata = {
        "id": f"source-episode/{compute_sha256(episode_id)}",
        "document_type": "reference", "node_type": "source_episode",
        "episode_id": episode_id, "source_episode_schema_version": 1,
        "range_unit": "unicode_codepoints_in_body", "sections": sections, "turns": turns,
    }
    return "---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True) + "---\n" + body


def inspect_source_episode(storage_dir: str, episode_id: str) -> SourceEpisode:
    path = _source_path(storage_dir, episode_id)
    raw = path.read_bytes().decode("utf-8")
    metadata, body = split_markdown(raw)
    if metadata.get("source_episode_schema_version") != 1 or metadata.get("episode_id") != episode_id:
        raise LineageValidationError("unsupported or mismatched source episode record")

    def content(span: Any) -> str:
        if not isinstance(span, dict):
            raise LineageValidationError("invalid source content range")
        start, end = span.get("start"), span.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(body):
            raise LineageValidationError("source content range is out of bounds")
        value = body[start:end]
        if span.get("encoding") == "json_string":
            value = json.loads(value)
        elif span.get("encoding") != "text":
            raise LineageValidationError("unsupported source content encoding")
        if not isinstance(value, str):
            raise LineageValidationError("source content must decode to text")
        return value

    try:
        sections = {name: content(metadata["sections"][name]) for name in ("beginning", "middle", "end")}
        turns = tuple(EpisodeTurn(item["position"], item["role"], content(item["content_range"]), item["timestamp"]) for item in metadata["turns"])
        episode = Episode(**sections, turns=turns)
    except (KeyError, TypeError, ValueError) as exc:
        raise LineageValidationError("invalid source episode structure") from exc
    if _serialize(episode_id, episode) != raw:
        raise LineageValidationError("source episode structure or content ranges were changed")
    canonical = parse_and_normalize(raw, str(path), storage_dir)
    body_offset = len(raw) - len(body)
    spans = {}
    for item in metadata["turns"]:
        start = body_offset + item["content_range"]["start"]
        end = body_offset + item["content_range"]["end"]
        spans[item["position"]] = EvidenceSpan(raw.count("\n", 0, start) + 1, raw.count("\n", 0, end - 1) + 1)
    return SourceEpisode(episode_id, episode, str(path), canonical, spans)


def persist_source_episode(engine: Any, episode_id: str, episode: Episode) -> SourceEpisode:
    path = _source_path(engine.storage_dir, episode_id)
    index_root = Path(engine.index_cache_dir).resolve(strict=False)
    if index_root == path or index_root in path.parents:
        raise LineageValidationError("source episodes cannot live inside the disposable index")
    raw = _serialize(episode_id, episode)
    # Evaluate the actual source text, never a wrapper that changes gate context.
    source_text = "\n".join([episode.beginning, episode.middle, episode.end] + [t.content for t in episode.turns])
    decision = engine.gating_engine.evaluate(source_text, [])
    if decision.admission in {WriteAdmission.REJECT, WriteAdmission.REVIEW}:
        raise WriteGatingViolationError(WriteResult(episode_id, None, False, decision))
    if decision.content_changed:
        raise LineageValidationError("source episode needs transformation; source text will not be rewritten")
    if path.exists():
        if path.read_bytes().decode("utf-8") != raw:
            raise LineageValidationError("source episode ID already exists with different content")
        return inspect_source_episode(engine.storage_dir, episode_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".episode-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            # Atomic, no-clobber publication. A concurrent winner must match.
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes().decode("utf-8") != raw:
                raise LineageValidationError("source episode ID concurrently acquired different content")
    finally:
        os.unlink(temporary)
    return inspect_source_episode(engine.storage_dir, episode_id)


def supporting_evidence_records(source: SourceEpisode, memory_id: str, positions: Sequence[int]) -> List[EvidenceRecord]:
    supporting = validate_support(source.episode, positions)
    claim_metadata = deepcopy(source.canonical)
    claim_metadata.identity.id = memory_id
    return [evidence_from_canonical(
        claim_metadata, extraction_method="source_turn_reference", inferred=False,
        span=source.turn_spans[position],
    ) for position in supporting]


def bind_lineage(source: SourceEpisode, memory_id: str, positions: Sequence[int]) -> LineageMetadata:
    supporting = validate_support(source.episode, positions)
    return LineageMetadata(
        source.episode_id, supporting, supporting[-1] if supporting else None,
        evidence_from_canonical(source.canonical).to_dict(),
        [record.to_dict() for record in supporting_evidence_records(source, memory_id, supporting)],
    )


def validate_lineage(storage_dir: str, memory_id: str, lineage: LineageMetadata) -> SourceEpisode:
    if not isinstance(lineage, LineageMetadata):
        raise LineageValidationError("lineage must be canonical LineageMetadata")
    if lineage.temporal_position is not None and type(lineage.temporal_position) is not int:
        raise LineageValidationError("temporal_position must be an integer source position or None")
    source = inspect_source_episode(storage_dir, lineage.source_episode_id)
    expected = bind_lineage(source, memory_id, lineage.supporting_turns)
    if expected != lineage:
        raise LineageValidationError("lineage does not match the exact source version/turns/position")
    return source


def inspect_lineage(storage_dir: str, memory_id: str, lineage: LineageMetadata) -> Dict[str, Any]:
    result = lineage.to_dict()
    result["temporal_position_semantics"] = TEMPORAL_POSITION_SEMANTICS
    result["support_semantics"] = "source_reference_only_not_semantic_entailment"
    try:
        source = validate_lineage(storage_dir, memory_id, lineage)
        result["status"] = "verified" if source.episode.turns else "episode_only_no_source_turns"
    except FileNotFoundError:
        result["status"] = "missing_source"
    except (OSError, ValueError, TypeError, AttributeError):
        result["status"] = "invalid_or_changed_source"
    return result
