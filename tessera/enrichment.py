"""Offline, review-only legacy enrichment experiment (#176).

This module has no provider transport, admission, index or source-write path.
A plan is a disclosure artifact, never permission to send its sources anywhere.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
from typing import Any, Dict, List, Optional, Sequence

from .canonical import DRAWERS, effective_entities, effective_tags, parse_and_normalize
from .config import resolve_runtime_configuration
from .segmentation import segment_source_document
from .source_discovery import discover_sources
from .source_formats import split_source

SCHEMA_VERSION = 1
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
RELATION_TYPES = {"supports", "contradicts", "supersedes_candidate", "derived_from", "related_to", "caused_by"}
METADATA_FIELDS = {"document_type", "tags", "entities", "state_key", "valid_from", "valid_until"}


class EnrichmentError(ValueError):
    """Invalid, unsafe, over-budget or stale experiment input."""


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        raise EnrichmentError("artifact must contain finite JSON values") from exc


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise EnrichmentError(f"{field} must be nonempty text of at most {maximum} characters")
    return value


def _integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise EnrichmentError(f"{field} must be an integer in [{minimum}, {maximum}]")
    return value


def _number(value: Any, field: str, maximum: Optional[float] = None) -> float:
    if type(value) not in (int, float):
        raise EnrichmentError(f"{field} must be finite and nonnegative")
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise EnrichmentError(f"{field} is outside the supported numeric range") from exc
    if not finite or value < 0:
        raise EnrichmentError(f"{field} must be finite and nonnegative")
    if maximum is not None and value > maximum:
        raise EnrichmentError(f"{field} exceeds limit")
    return float(value)


def _keys(value: Any, fields: set, label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise EnrichmentError(f"{label} requires exactly these fields: {', '.join(sorted(fields))}")


@dataclass(frozen=True)
class EnrichmentLimits:
    max_sources: int = 16
    max_bytes_per_source: int = 65536
    max_total_bytes: int = 262144
    max_input_tokens_per_source: int = 67584
    max_model_calls: int = 16
    max_output_tokens_per_source: int = 2048
    max_response_bytes_per_source: int = 65536
    max_candidates_per_source: int = 64
    budget_usd: Optional[float] = None

    def validate(self) -> None:
        for key, maximum in (("max_sources", 256), ("max_bytes_per_source", 1048576),
                             ("max_total_bytes", 16777216), ("max_input_tokens_per_source", 2097152),
                             ("max_model_calls", 256), ("max_output_tokens_per_source", 65536),
                             ("max_response_bytes_per_source", 1048576), ("max_candidates_per_source", 512)):
            _integer(getattr(self, key), key, 1, maximum)
        if self.budget_usd is not None:
            _number(self.budget_usd, "budget_usd")


@dataclass(frozen=True)
class EnrichmentProfile:
    name: str
    version: str
    mode: str
    provider_mode: str
    provider: str
    model: str
    prompt_version: str
    prompt_token_allowance: int = 2048
    input_usd_per_million: Optional[float] = None
    output_usd_per_million: Optional[float] = None

    def validate(self) -> None:
        for key in ("name", "version", "provider", "model", "prompt_version"):
            _text(getattr(self, key), key, 256)
        if self.mode not in {"A1", "A2", "A3"}:
            raise EnrichmentError("mode must be A1, A2 or A3; A0 stays the independent core")
        if self.provider_mode not in {"local", "remote"}:
            raise EnrichmentError("provider_mode must explicitly be local or remote")
        _integer(self.prompt_token_allowance, "prompt_token_allowance", 1, 1048576)
        prices = (self.input_usd_per_million, self.output_usd_per_million)
        if (prices[0] is None) != (prices[1] is None):
            raise EnrichmentError("both input/output prices or neither are required")
        for value in prices:
            if value is not None:
                _number(value, "price")


def _read_source(root: Path, relative: str, maximum: int) -> bytes:
    """Pin every path component; never follow a swapped directory/file symlink.

    Fail closed on platforms without descriptor-relative no-follow support.
    Policy eligibility is checked separately by canonical discovery first.
    """
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise EnrichmentError("safe source reads require descriptor-relative O_NOFOLLOW support")
    descriptors = []
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(fd)
        parts = relative.split("/")
        for part in parts[:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            descriptors.append(fd)
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        descriptors.append(file_fd)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise EnrichmentError("source is special or exceeds byte limit")
        chunks = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(file_fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        if (len(data) > maximum or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise EnrichmentError("source changed during read or exceeds byte limit")
        return data
    except OSError as exc:
        raise EnrichmentError(f"unsafe or unreadable selected source: {relative}") from exc
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _prepare(root: Path, selected_paths: Sequence[str], corpus_id: str,
             profile: EnrichmentProfile, limits: EnrichmentLimits):
    profile.validate()
    limits.validate()
    _text(corpus_id, "corpus_id", 256)
    if not isinstance(selected_paths, (list, tuple)) or not selected_paths:
        raise EnrichmentError("select individual source paths explicitly")
    if len(selected_paths) > limits.max_sources:
        raise EnrichmentError("max_sources exceeded")
    if any(not isinstance(path, str) for path in selected_paths) or len(set(selected_paths)) != len(selected_paths):
        raise EnrichmentError("selected paths must be unique strings")
    root = root.resolve(strict=True)
    configuration = resolve_runtime_configuration(cwd=root, environ={})
    discovery = discover_sources(root, configuration, selected_paths=selected_paths,
                                 max_file_size=limits.max_bytes_per_source)
    if discovery.warnings:
        raise EnrichmentError("discovery diagnostics require review before enrichment")
    safe = {item.path for item in discovery.files if item.kind == "file" and item.selectable}
    if not set(selected_paths) <= safe:
        raise EnrichmentError("selection includes forbidden, ignored, missing or non-file sources")
    sources, snapshots = [], {}
    fingerprint = _hash(asdict(profile))
    total_bytes = 0
    for relative in sorted(selected_paths):
        data = _read_source(root, relative, limits.max_bytes_per_source)
        total_bytes += len(data)
        if total_bytes > limits.max_total_bytes:
            raise EnrichmentError("max_total_bytes exceeded")
        try:
            raw = data.decode("utf-8")
            canonical = parse_and_normalize(raw, str(root / relative), str(root))
            _, body = split_source(raw, path=relative)
        except (UnicodeError, ValueError) as exc:
            raise EnrichmentError(f"source requires parse review: {relative}") from exc
        token_bound = len(data) + profile.prompt_token_allowance
        if token_bound > limits.max_input_tokens_per_source:
            raise EnrichmentError("conservative input token allowance exceeded")
        eligible = bool(body.strip()) and canonical.classification.document_type not in {"harness_instructions", "skill_instructions"}
        source_hash = hashlib.sha256(data).hexdigest()
        identity = {"corpus_id": corpus_id, "source_document_id": canonical.source.document_id,
                    "source_version_hash": source_hash, "profile_version": profile.version,
                    "profile_fingerprint": fingerprint}
        source = {"source_document_id": canonical.source.document_id, "source_path": relative,
                  "source_version_hash": source_hash, "size_bytes": len(data),
                  "line_count": len(raw.splitlines()), "input_token_allowance": token_bound,
                  "cache_key": _hash(identity), "eligible": eligible,
                  "skip_reason": None if eligible else "empty_or_instruction_source",
                  "classification": asdict(canonical.classification),
                  "metadata_origin": dict(canonical.metadata_origin),
                  "tags": effective_tags(canonical.raw_frontmatter),
                  "entities": effective_entities(canonical.raw_frontmatter),
                  "state_key": canonical.state_key,
                  "valid_from": canonical.temporal.valid_from,
                  "valid_until": canonical.temporal.valid_until,
                  "structural_segments": [{"segment_id": segment.segment_id,
                                            "start_line": segment.start_line, "end_line": segment.end_line}
                                           for segment in segment_source_document(raw, body, canonical)]}
        sources.append(source)
        snapshots[relative] = raw
    eligible = [source for source in sources if source["eligible"]]
    calls = len(eligible)  # bounded whole-source capture, not #192 chunk scheduling
    if calls > limits.max_model_calls:
        raise EnrichmentError("max_model_calls exceeded")
    input_bound = sum(source["input_token_allowance"] for source in eligible)
    output_bound = calls * limits.max_output_tokens_per_source
    cost = None
    if profile.input_usd_per_million is not None:
        cost = (input_bound * profile.input_usd_per_million + output_bound * profile.output_usd_per_million) / 1000000
        if limits.budget_usd is not None and cost > limits.budget_usd:
            raise EnrichmentError("estimated token cost exceeds budget_usd")
    plan = {"schema_version": SCHEMA_VERSION, "corpus_id": corpus_id,
            "profile": asdict(profile), "profile_fingerprint": fingerprint, "limits": asdict(limits),
            "sources": sources, "source_files_modified": 0, "memories_admitted": 0,
            "source_fallback": "preserved; deterministic indexing remains independent",
            "work": {"sources_discovered": len(safe), "sources_selected": len(sources),
                     "sources_eligible": calls, "structural_segments": sum(len(source["structural_segments"]) for source in sources),
                     "estimated_model_calls": calls, "input_token_allowance": input_bound,
                     "output_token_allowance": output_bound, "estimated_token_cost_usd": cost},
            "consent_preview": {"plan_id_required": True, "authorization_granted": False,
                                "destination": {"provider_mode": profile.provider_mode, "provider": profile.provider, "model": profile.model},
                                "remote_transmission": profile.provider_mode == "remote",
                                "execution_supported": False,
                                "required": ["review exact source hashes and destination", "explicit source-content consent",
                                             "approve complete route pricing and run budget"]},
            "execution_blockers": ["offline experiment has no model transport", "source consent is not an authorization token"]}
    if cost is None:
        plan["execution_blockers"].append("pricing unknown; no zero-cost assumption")
    if limits.budget_usd is None:
        plan["execution_blockers"].append("run budget unapproved")
    plan["plan_id"] = _hash(plan)
    return plan, snapshots


def prepare_plan(root: Path, selected_paths: Sequence[str], corpus_id: str,
                 profile: EnrichmentProfile, limits: Optional[EnrichmentLimits] = None) -> Dict[str, Any]:
    """Disclose bounded work without returning source bodies or performing AI."""
    return _prepare(Path(root), selected_paths, corpus_id, profile, limits or EnrichmentLimits())[0]


def _spans(value: Any, raw: str) -> List[Dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 16:
        raise EnrichmentError("supporting_spans requires 1..16 exact source spans")
    lines = raw.splitlines(keepends=True)
    result = []
    for span in value:
        _keys(span, {"start_line", "end_line", "quote"}, "supporting span")
        start = _integer(span["start_line"], "start_line", 1, len(lines))
        end = _integer(span["end_line"], "end_line", start, len(lines))
        quote = span["quote"]
        if not isinstance(quote, str) or not quote.strip() or quote != "".join(lines[start - 1:end]):
            raise EnrichmentError("supporting quote must exactly match the full source lines")
        result.append({"start_line": start, "end_line": end, "quote": quote})
    if len({_json(span) for span in result}) != len(result):
        raise EnrichmentError("duplicate supporting spans")
    return sorted(result, key=lambda span: (span["start_line"], span["end_line"]))


def _annotation(item: Any, fields: set, raw: str) -> List[Dict[str, Any]]:
    _keys(item, fields | {"confidence", "uncertainty", "supporting_spans"}, "candidate")
    _number(item["confidence"], "confidence", 1)
    if not isinstance(item["uncertainty"], list) or len(item["uncertainty"]) > 16:
        raise EnrichmentError("uncertainty must be a bounded list")
    for uncertainty in item["uncertainty"]:
        _text(uncertainty, "uncertainty")
    return _spans(item["supporting_spans"], raw)


def replay_capture(root: Path, selected_paths: Sequence[str], corpus_id: str,
                   profile: EnrichmentProfile, capture: Dict[str, Any],
                   limits: Optional[EnrichmentLimits] = None) -> Dict[str, Any]:
    """Validate externally captured responses against a freshly recomputed plan.

    No inference or semantic correctness is established by exact-quote matching.
    Success means structurally valid *review candidates*, never admitted memory.
    """
    limits = limits or EnrichmentLimits()
    if len(_json(capture).encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise EnrichmentError("capture exceeds artifact byte limit")
    _keys(capture, {"schema_version", "plan_id", "profile_fingerprint", "capture_kind", "records"}, "capture")
    if type(capture["schema_version"]) is not int or capture["schema_version"] != SCHEMA_VERSION:
        raise EnrichmentError("unsupported capture schema")
    if capture["capture_kind"] not in {"synthetic", "provider_response"}:
        raise EnrichmentError("capture_kind must disclose synthetic or provider_response")
    plan, snapshots = _prepare(Path(root), selected_paths, corpus_id, profile, limits)
    if (capture["plan_id"], capture["profile_fingerprint"]) != (plan["plan_id"], plan["profile_fingerprint"]):
        raise EnrichmentError("stale source, profile, selection or budget; prepare a new plan")
    records = capture["records"]
    if not isinstance(records, list) or len(records) > limits.max_model_calls:
        raise EnrichmentError("capture records exceed model-call limit")
    sources = {source["cache_key"]: source for source in plan["sources"] if source["eligible"]}
    seen, candidate_ids = set(), set()
    candidates, metadata, relations, diagnostics = [], [], [], []
    rejected, duplicates, success, failed, input_tokens, output_tokens = 0, 0, 0, 0, 0, 0
    for record in records:
        _keys(record, {"cache_key", "status", "response", "usage"}, "record")
        key = record["cache_key"]
        if not isinstance(key, str) or key not in sources or key in seen:
            raise EnrichmentError("record refers to unselected/skipped/duplicate source")
        seen.add(key)
        source = sources[key]
        raw = snapshots[source["source_path"]]
        _keys(record["usage"], {"input_tokens", "output_tokens", "latency_ms", "cost_usd"}, "usage")
        usage = record["usage"]
        input_tokens += _integer(usage["input_tokens"], "input_tokens", 0, source["input_token_allowance"])
        output_tokens += _integer(usage["output_tokens"], "output_tokens", 0, limits.max_output_tokens_per_source)
        for field in ("latency_ms", "cost_usd"):
            if usage[field] is not None:
                _number(usage[field], field)
        if record["status"] not in {"success", "error", "refused", "truncated"}:
            raise EnrichmentError("unknown capture status")
        if record["status"] != "success":
            if record["response"] is not None:
                raise EnrichmentError("failed/refused/truncated response must not carry partial candidates")
            failed += 1
            diagnostics.append({"source_path": source["source_path"], "code": record["status"]})
            continue
        response = record["response"]
        if len(_json(response).encode("utf-8")) > limits.max_response_bytes_per_source:
            raise EnrichmentError("response byte limit exceeded")
        _keys(response, {"metadata", "claims", "relations"}, "response")
        if any(not isinstance(response[field], list) for field in ("metadata", "claims", "relations")):
            raise EnrichmentError("response collections must be arrays")
        if sum(len(response[field]) for field in response) > limits.max_candidates_per_source:
            raise EnrichmentError("candidate limit exceeded")
        if ((profile.mode == "A1" and response["claims"])
                or (profile.mode != "A3" and response["relations"])):
            raise EnrichmentError("capture includes proposals outside the selected mode")
        success += 1
        origin = "synthetic" if capture["capture_kind"] == "synthetic" else "ai_inferred"
        lineage = {field: source[field] for field in ("source_document_id", "source_path", "source_version_hash")}
        shared = {"origin": origin, "disposition": "review_required", "profile_fingerprint": plan["profile_fingerprint"],
                  "semantic_support": "unverified", "lineage": lineage, "corpus_id": corpus_id}
        for kind, items in response.items():
            for ordinal, item in enumerate(items):
                try:
                    if kind == "claims":
                        spans = _annotation(item, {"claim", "drawer"}, raw)
                        _text(item["claim"], "claim")
                        if item["drawer"] not in DRAWERS:
                            raise EnrichmentError("unknown drawer")
                        # Do not infer semantic equivalence from spelling, case,
                        # drawer or confidence. Differing annotations need review.
                        candidate_id = _hash({**shared, **item, "supporting_spans": spans})
                        if candidate_id in candidate_ids:
                            duplicates += 1
                            diagnostics.append({"source_path": source["source_path"], "code": "exact_candidate_duplicate", "ordinal": ordinal})
                            continue
                        candidate_ids.add(candidate_id)
                        review = ["human semantic-support and atomicity review required"]
                        explicit = source["metadata_origin"]
                        if explicit.get("drawer") == "explicit" and item["drawer"] != source["classification"]["drawer"]:
                            review.append("conflicts_with_explicit_drawer")
                        candidates.append({**shared, **item, "supporting_spans": spans,
                                           "candidate_id": candidate_id, "review_diagnostics": review,
                                           "lineage": {**lineage, "supporting_spans": spans}})
                    elif kind == "metadata":
                        spans = _annotation(item, {"field", "value"}, raw)
                        field = item["field"]
                        if not isinstance(field, str) or field not in METADATA_FIELDS:
                            raise EnrichmentError("unsupported metadata field")
                        value = item["value"]
                        if field in {"tags", "entities"}:
                            if not isinstance(value, list) or len(value) > 32:
                                raise EnrichmentError("tags/entities must be bounded text arrays")
                            for entry in value:
                                _text(entry, field, 256)
                        else:
                            _text(value, field, 256)
                        original = source["classification"][field] if field == "document_type" else source.get(field)
                        # Tags/entities/state_key lack canonical per-field origin.
                        # Any existing nonempty value is conservatively preserved.
                        conflict = original not in (None, [], "") and original != value
                        metadata.append({**shared, **item, "supporting_spans": spans,
                                         "review_diagnostics": ["existing_metadata_differs"] if conflict else [],
                                         "lineage": {**lineage, "supporting_spans": spans}})
                    else:
                        spans = _annotation(item, {"type", "target_source_document_id"}, raw)
                        if item["type"] not in RELATION_TYPES:
                            raise EnrichmentError("unsupported relation; supersedes is never authoritative")
                        target = item["target_source_document_id"]
                        if not isinstance(target, str) or target not in {entry["source_document_id"] for entry in sources.values()}:
                            raise EnrichmentError("relation target must be an eligible selected document")
                        relations.append({**shared, **item, "supporting_spans": spans,
                                          "relation_origin": "synthetic" if origin == "synthetic" else "ai_proposed",
                                          "lineage": {**lineage, "supporting_spans": spans}})
                except (EnrichmentError, TypeError) as exc:
                    rejected += 1
                    diagnostics.append({"source_path": source["source_path"], "kind": kind, "ordinal": ordinal,
                                        "code": "invalid_candidate", "detail": str(exc)})
    costs = [record["usage"]["cost_usd"] for record in records]
    known_cost = sum(cost for cost in costs if cost is not None)
    _number(known_cost, "total reported cost")
    reported_cost = known_cost if costs and all(cost is not None for cost in costs) else None
    if limits.budget_usd is not None and known_cost > limits.budget_usd:
        raise EnrichmentError("reported cost exceeds budget; capture rejected")
    return {"schema_version": SCHEMA_VERSION, "plan_id": plan["plan_id"], "capture_hash": _hash(capture),
            "capture_kind": capture["capture_kind"], "disposition": "review_only", "decision": "ITERATE",
            "counts": {**{key: plan["work"][key] for key in ("sources_discovered", "sources_selected", "structural_segments")},
                       "sources_analyzed": success, "sources_failed": failed, "sources_missing": len(sources) - len(seen),
                       "semantic_claims_proposed": sum(len(record["response"]["claims"]) for record in records if record["status"] == "success"),
                       "memory_candidates_proposed": len(candidates), "memories_admitted": 0,
                       "exact_candidate_duplicates": duplicates, "invalid_proposals": rejected,
                       "memories_requiring_review": len(candidates), "relations_ai_proposed": len(relations) if capture["capture_kind"] == "provider_response" else 0,
                       "relations_synthetic": len(relations) if capture["capture_kind"] == "synthetic" else 0,
                       "relations_validated": 0, "relations_explicit": None, "relations_deterministic": None,
                       "memories_deduplicated": 0, "memories_rejected": 0},
            "usage": {"model_calls_performed": 0, "capture_calls_reported": len(records),
                      "input_tokens_reported": input_tokens, "output_tokens_reported": output_tokens,
                      "cost_usd_reported": reported_cost, "latency_ms_reported": [record["usage"]["latency_ms"] for record in records]},
            "memory_candidates": candidates, "metadata_candidates": metadata, "relation_candidates": relations,
            "diagnostics": diagnostics, "source_files_modified": 0, "raw_source_fallback": "unchanged",
            "quality": {"human_labels": "missing", "hallucination_rate": None, "retrieval_improvement": None,
                        "span_validation": "exact bytes-as-UTF8-lines, not entailment", "semantic_dedup": "not implemented",
                        "existing_relation_origin_counts": "not measured by capture replay"},
            "consumer_gates": ["#137 canonical lineage adapter", "#192 execution/cache/resume", "#19 semantic admission",
                               "#92 write safety after admission", "#15/#16 temporal/conflict policy", "#168 durable memory"]}


def _load_json(path: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise EnrichmentError("duplicate JSON object key")
            result[key] = value
        return result
    if not hasattr(os, "O_NONBLOCK") or not hasattr(os, "O_NOFOLLOW"):
        raise EnrichmentError("safe artifact reads require O_NONBLOCK and O_NOFOLLOW")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise EnrichmentError("artifact must be a regular file")
        if before.st_size > MAX_ARTIFACT_BYTES:
            raise EnrichmentError("artifact byte limit exceeded")
        remaining, chunks = MAX_ARTIFACT_BYTES + 1, []
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        if (len(data) > MAX_ARTIFACT_BYTES or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise EnrichmentError("artifact changed during read or exceeds byte limit")
    finally:
        os.close(fd)
    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(EnrichmentError("nonfinite JSON")))
    except (RecursionError, OverflowError) as exc:
        raise EnrichmentError("artifact exceeds nesting or numeric limits") from exc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "replay"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--request", required=True, help="explicit selection/profile/limits JSON")
    parser.add_argument("--capture", help="offline response capture; required for replay")
    args = parser.parse_args(argv)
    try:
        request = _load_json(args.request)
        _keys(request, {"corpus_id", "selected_paths", "profile", "limits"}, "request")
        profile = EnrichmentProfile(**request["profile"])
        limits = EnrichmentLimits(**request["limits"])
        arguments = (Path(args.root), request["selected_paths"], request["corpus_id"], profile)
        if args.command == "plan":
            if args.capture:
                raise EnrichmentError("plan does not consume a capture")
            result = prepare_plan(*arguments, limits=limits)
        else:
            if not args.capture:
                raise EnrichmentError("replay requires --capture")
            result = replay_capture(*arguments, capture=_load_json(args.capture), limits=limits)
        print(_json(result))
        return 0
    except (ValueError, TypeError, OSError, RecursionError, OverflowError) as exc:
        print(_json({"error": {"code": "invalid_enrichment_experiment", "message": str(exc)}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
