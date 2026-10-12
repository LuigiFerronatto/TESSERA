"""Offline-first, human-gated capture/replay and adjudicated F/P/I scoring.

No provider SDK, discovery, credentials, downloads, or network CLI is included.
A host may supply a provider callback to capture() after reviewing/fixing labels.
Semantic matching is human adjudication, not substring or LLM self-grading.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Callable, Optional

from tessera.models import Episode
from tessera.typed_decomposition import (
    CONTRACT_VERSION, TYPES, decompose_typed_episode,
)

SCHEMA_VERSION = "typed-decomposition-eval-v1"
CATEGORIES = {
    "facts_only", "preference_rationale", "preference_change", "transferable_insight",
    "unsupported_inference", "zero_memory", "multiple_same_type", "cross_type_ambiguity",
}


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def label_digest(fixture):
    """Bind reviewer approval to all episodes, labels and annotation guidance."""
    return digest({key: value for key, value in fixture.items() if key != "review"})


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")


def _review(review, expected_digest):
    if not isinstance(review, dict) or review.get("status") != "human_reviewed":
        raise ValueError("human-reviewed labels/adjudication required; draft is not evidence")
    _text(review.get("reviewer"), "reviewer")
    _text(review.get("reviewed_at"), "reviewed_at")
    try:
        timestamp = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError("timezone required")
    except (ValueError, TypeError) as exc:
        raise ValueError("reviewed_at must be an ISO timestamp with timezone") from exc
    if review.get("content_sha256") != expected_digest:
        raise ValueError("review digest mismatch; review changed content again")


def validate_fixture(fixture, *, require_review=False):
    if not isinstance(fixture, dict) or fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported fixture schema")
    if fixture.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("fixture contract mismatch")
    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture cases must be nonempty")
    case_ids = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        _text(case.get("id"), "case id")
        if case["id"] in case_ids:
            raise ValueError("duplicate case id")
        case_ids.add(case["id"])
        if case.get("category") not in CATEGORIES:
            raise ValueError("unknown case category")
        episode = case.get("episode")
        if not isinstance(episode, dict) or set(episode) != {"beginning", "middle", "end"}:
            raise ValueError("episode must have exactly beginning, middle, end")
        if any(not isinstance(value, str) for value in episode.values()):
            raise ValueError("episode fields must be text")
        expected = case.get("expected_units")
        if not isinstance(expected, list):
            raise ValueError("expected_units must be an array; [] means zero memory")
        unit_ids = set()
        for unit in expected:
            if not isinstance(unit, dict):
                raise ValueError("unit must be an object")
            for field in ("id", "content", "rationale"):
                _text(unit.get(field), f"unit {field}")
            if unit["id"] in unit_ids:
                raise ValueError("duplicate unit id")
            unit_ids.add(unit["id"])
            allowed = unit.get("acceptable_types")
            if (not isinstance(allowed, list) or not allowed
                    or any(not isinstance(kind, str) or kind not in TYPES for kind in allowed)
                    or len(set(allowed)) != len(allowed)):
                raise ValueError("invalid acceptable_types")
    if require_review:
        _review(fixture.get("review"), label_digest(fixture))
    return fixture


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    cost_kind: Optional[str] = None  # actual or estimated; None means unknown


def _usage(response):
    if not isinstance(response, ProviderResponse) or not isinstance(response.text, str):
        raise TypeError("provider must return ProviderResponse with text")
    for value in (response.input_tokens, response.output_tokens):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("token counts must be nonnegative integers or null")
    cost = response.cost_usd
    if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
        raise ValueError("cost must be nonnegative finite USD or null")
    if (cost is None and response.cost_kind is not None) or (
        cost is not None and response.cost_kind not in ("actual", "estimated")
    ):
        raise ValueError("cost kind must identify actual/estimated when cost is supplied")
    return {key: value for key, value in asdict(response).items() if key != "text"}


def capture(fixture, *, variant, provider: Optional[Callable] = None,
            provider_config=None, repeat_id="1"):
    """Capture a frozen full fixture; validates approval before the first callback.

    Human review metadata is an attestation, not authentication. Maintainers must
    verify the review in their normal review process. Draft D0 is mechanics only.
    Provider config must name provider, model and decoding settings, never keys.
    """
    validate_fixture(fixture, require_review=variant != "D0")
    # Freeze inputs before invoking caller code; later mutations cannot relabel a run.
    fixture = json.loads(json.dumps(fixture, allow_nan=False))
    provider_config = json.loads(json.dumps(provider_config, allow_nan=False))
    if variant not in ("D0", "D1", "D2"):
        raise ValueError("unknown variant")
    _text(repeat_id, "repeat_id")
    if variant != "D0":
        if provider is None:
            raise ValueError("assisted capture requires an explicitly supplied provider")
        if not isinstance(provider_config, dict):
            raise ValueError("provider_config required")
        for key in ("provider", "model"):
            _text(provider_config.get(key), key)
        if not isinstance(provider_config.get("decoding"), dict):
            raise ValueError("explicit decoding settings required")
        digest(provider_config)  # JSON-safe; secrets must never be supplied here.
    rows = []
    for case in fixture["cases"]:
        calls = []

        def call(system, user):
            entry = {"system_sha256": digest(system), "user_sha256": digest(user)}
            start = perf_counter()
            try:
                response = provider(system, user)
                entry.update(response=response.text if isinstance(response, ProviderResponse) else None,
                             usage=_usage(response))
                return response.text
            except (RuntimeError, TimeoutError, ConnectionError) as exc:
                # Only store exception type, not provider messages that may carry secrets.
                entry.update(error=type(exc).__name__, response=None, usage=None)
                raise
            finally:
                entry["latency_ms"] = (perf_counter() - start) * 1000
                calls.append(entry)

        start = perf_counter()
        result = decompose_typed_episode(Episode(**case["episode"]), variant=variant,
                                        llm_fn=call if variant != "D0" else None)
        rows.append({"case_id": case["id"], "result": asdict(result), "calls": calls,
                     "latency_ms": (perf_counter() - start) * 1000})
    return {
        "schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
        "fixture_sha256": digest(fixture), "labels_sha256": label_digest(fixture),
        "variant": variant, "repeat_id": repeat_id,
        "execution_kind": "deterministic" if variant == "D0" else "provider_capture",
        "provider_config": provider_config if variant != "D0" else None,
        "quality_status": "not_scored", "rows": rows,
    }


def replay(fixture, capture_artifact):
    """Verify the entire capture against current prompts and extraction mechanics.

    Does not call a provider. Rejects changed labels/episodes/prompts, extra/missing
    cases/calls and altered results. Historical latency/usage are never remeasured.
    """
    if not isinstance(capture_artifact, dict):
        raise ValueError("capture must be an object")
    validate_fixture(fixture, require_review=capture_artifact.get("variant") != "D0")
    if (capture_artifact.get("schema_version") != SCHEMA_VERSION
            or capture_artifact.get("contract_version") != CONTRACT_VERSION
            or capture_artifact.get("fixture_sha256") != digest(fixture)
            or capture_artifact.get("labels_sha256") != label_digest(fixture)):
        raise ValueError("capture identity does not match frozen fixture/contract")
    variant = capture_artifact.get("variant")
    if variant not in ("D0", "D1", "D2"):
        raise ValueError("unknown capture variant")
    expected_kind = "deterministic" if variant == "D0" else "provider_capture"
    if capture_artifact.get("execution_kind") != expected_kind:
        raise ValueError("unsupported capture execution kind")
    rows = capture_artifact.get("rows")
    if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            or [row.get("case_id") for row in rows] != [
        case["id"] for case in fixture["cases"]
    ]):
        raise ValueError("capture must contain all cases exactly once in frozen order")
    results = []
    for case, row in zip(fixture["cases"], rows):
        calls = row.get("calls")
        if not isinstance(calls, list):
            raise ValueError("capture calls must be an array")
        index = 0

        def replay_call(system, user):
            nonlocal index
            if index >= len(calls):
                raise ValueError("missing captured call")
            entry = calls[index]
            if not isinstance(entry, dict):
                raise ValueError("captured call must be an object")
            index += 1
            if (entry.get("system_sha256") != digest(system)
                    or entry.get("user_sha256") != digest(user)):
                raise ValueError("prompt mismatch")
            _nonnegative(entry.get("latency_ms"), "call latency")
            if entry.get("error"):
                errors = {"RuntimeError": RuntimeError, "TimeoutError": TimeoutError,
                          "ConnectionError": ConnectionError}
                if (entry["error"] not in errors or entry.get("response") is not None
                        or entry.get("usage") is not None):
                    raise ValueError("invalid captured failure")
                raise errors[entry["error"]]("replayed provider failure")
            usage = entry.get("usage")
            if not isinstance(usage, dict) or set(usage) != {
                "input_tokens", "output_tokens", "cost_usd", "cost_kind"
            }:
                raise ValueError("invalid captured usage")
            _usage(ProviderResponse(entry.get("response"), **usage))
            return entry["response"]

        result = decompose_typed_episode(Episode(**case["episode"]), variant=variant,
                                        llm_fn=replay_call if variant != "D0" else None)
        if index != len(calls):
            raise ValueError("unused captured calls")
        # JSON normalizes tuples to arrays for loaded artifacts.
        if digest(asdict(result)) != digest(row.get("result")):
            raise ValueError("captured result does not reproduce")
        _nonnegative(row.get("latency_ms"), "episode latency")
        results.append(result)
    return results


def _nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be nonnegative and finite")


def adjudication_template(capture_artifact):
    """Blank review fields cannot be mistaken for negative or positive judgments."""
    return {"capture_sha256": digest(capture_artifact), "review": {"status": "draft"},
            "rows": [{"case_id": row["case_id"], "predictions": [
                {"index": i, "matched_unit_id": None, "unsupported": None,
                 "atomicity_violation": None, "duplicate_of": None, "rationale": ""}
                for i, _ in enumerate(row["result"]["memories"])
            ]} for row in capture_artifact["rows"]]}


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def score(fixture, artifact, judgments):
    """Score human one-to-one unit matching; no quality score on unreviewed data.

    Type macro F1 uses only matched units having exactly one acceptable type.
    Ambiguous labels count toward acceptable-type accuracy, with their denominator
    reported separately. Misses/unsupported outputs enter extraction metrics.
    """
    validate_fixture(fixture, require_review=True)
    if not isinstance(judgments, dict):
        raise ValueError("judgments must be an object")
    replay(fixture, artifact)
    if judgments.get("capture_sha256") != digest(artifact):
        raise ValueError("adjudication belongs to a different capture")
    _review(judgments.get("review"), digest({k: v for k, v in judgments.items() if k != "review"}))
    judged_rows = judgments.get("rows")
    if (not isinstance(judged_rows, list)
            or any(not isinstance(row, dict) for row in judged_rows)
            or [row.get("case_id") for row in judged_rows] != [
                case["id"] for case in fixture["cases"]
            ]):
        raise ValueError("judgments must cover all cases in order")
    totals = Counter(dict.fromkeys(("expected", "predicted", "zero_cases", "zero_correct",
                                    "matched", "type_correct", "unambiguous_matches",
                                    "unsupported", "atomicity_violations", "duplicates"), 0))
    confusion = {actual: Counter() for actual in TYPES}
    for case, row, judged in zip(fixture["cases"], artifact["rows"], judgments["rows"]):
        units = {unit["id"]: unit for unit in case["expected_units"]}
        memories = row["result"]["memories"]
        annotations = judged.get("predictions", [])
        if (not isinstance(annotations, list)
                or any(not isinstance(item, dict) for item in annotations)
                or [item.get("index") for item in annotations] != list(range(len(memories)))):
            raise ValueError("exactly one ordered judgment per prediction required")
        totals["expected"] += len(units)
        totals["predicted"] += len(memories)
        totals["zero_cases"] += not units
        totals["zero_correct"] += not units and not memories
        matched = set()
        for i, (prediction, judgment) in enumerate(zip(memories, annotations)):
            _text(judgment.get("rationale"), "judgment rationale")
            if any(type(judgment.get(field)) is not bool for field in ("unsupported", "atomicity_violation")):
                raise ValueError("human unsupported/atomicity judgments must be booleans")
            unit_id = judgment.get("matched_unit_id")
            duplicate = judgment.get("duplicate_of")
            if duplicate is not None and (type(duplicate) is not int or not 0 <= duplicate < i):
                raise ValueError("duplicate_of must reference an earlier prediction")
            if unit_id is not None:
                if not isinstance(unit_id, str) or unit_id not in units or unit_id in matched:
                    raise ValueError("unit matches must be valid and one-to-one")
                if judgment["unsupported"] or judgment["atomicity_violation"] or duplicate is not None:
                    raise ValueError("unsupported, compound or duplicate output cannot earn an atomic match")
                matched.add(unit_id)
                allowed = units[unit_id]["acceptable_types"]
                kind = prediction["mem_type"]
                totals["matched"] += 1
                totals["type_correct"] += kind in allowed
                if len(allowed) == 1:
                    confusion[allowed[0]][kind] += 1
                    totals["unambiguous_matches"] += 1
            totals["unsupported"] += judgment["unsupported"]
            totals["atomicity_violations"] += judgment["atomicity_violation"]
            totals["duplicates"] += duplicate is not None
    precision = _ratio(totals["matched"], totals["predicted"])
    recall = _ratio(totals["matched"], totals["expected"])
    per_type = {}
    for kind in TYPES:
        true_positive = confusion[kind][kind]
        actual = sum(confusion[kind].values())
        predicted = sum(row[kind] for row in confusion.values())
        per_type[kind] = _ratio(2 * true_positive, actual + predicted)
    defined = [value for value in per_type.values() if value is not None]
    return {
        "quality_status": "human_adjudicated", "capture_sha256": digest(artifact),
        "counts": dict(totals), "extraction_precision": precision,
        "extraction_recall": recall,
        "extraction_f1": _ratio(2 * totals["matched"], totals["predicted"] + totals["expected"]),
        "acceptable_type_accuracy": _ratio(totals["type_correct"], totals["matched"]),
        "unambiguous_type_macro_f1": sum(defined) / len(defined) if defined else None,
        "type_macro_classes": len(defined), "type_f1": per_type,
        "unsupported_inference_rate": _ratio(totals["unsupported"], totals["predicted"]),
        "atomicity_violation_rate": _ratio(totals["atomicity_violations"], totals["predicted"]),
        "duplicate_rate": _ratio(totals["duplicates"], totals["predicted"]),
        "zero_memory_accuracy": _ratio(totals["zero_correct"], totals["zero_cases"]),
        "memory_count_delta": totals["predicted"] - totals["expected"],
        "telemetry": telemetry(artifact),
    }


def telemetry(artifact):
    calls = [call for row in artifact["rows"] for call in row["calls"]]
    result = {"provider_requests": len(calls),
              "capture_latency_ms": sum(row["latency_ms"] for row in artifact["rows"]),
              "fallback_episodes": sum(row["result"]["mode"] == "deterministic_fallback"
                                       for row in artifact["rows"]),
              "duplicates_removed": sum(row["result"]["duplicates_removed"]
                                        for row in artifact["rows"])}
    for field in ("input_tokens", "output_tokens", "cost_usd"):
        values = [(call.get("usage") or {}).get(field) for call in calls]
        # Missing usage is unknown, including calls that failed.
        result[field] = sum(values) if all(value is not None for value in values) else None
    kinds = {(call.get("usage") or {}).get("cost_kind") for call in calls}
    result["cost_kind"] = (next(iter(kinds)) if len(kinds) == 1 and None not in kinds
                           else "mixed" if kinds and None not in kinds else None)
    return result


def compare(fixture, captures, judgments):
    """Compare matched D0/D1/D2 runs, without automatically selecting a default."""
    if set(captures) != {"D0", "D1", "D2"} or set(judgments) != set(captures):
        raise ValueError("all three variants and their adjudications are required")
    for variant, artifact in captures.items():
        if artifact.get("variant") != variant:
            raise ValueError("variant key mismatch")
    if captures["D1"]["provider_config"] != captures["D2"]["provider_config"]:
        raise ValueError("D1/D2 must use identical provider/model/decoding settings")
    if len({artifact["repeat_id"] for artifact in captures.values()}) != 1:
        raise ValueError("comparison must pair the same repeat ID")
    scores = {variant: score(fixture, captures[variant], judgments[variant])
              for variant in ("D0", "D1", "D2")}
    return {"fixture_sha256": digest(fixture), "scores": scores,
            "default_decision": "PENDING_HUMAN_DECISION", "default_changed": False}


def repeated_agreement(fixture, artifacts):
    """Exact typed-output multiset agreement, not semantic equivalence or quality."""
    if len(artifacts) < 2:
        raise ValueError("at least two captures required")
    for artifact in artifacts:
        replay(fixture, artifact)
    first = artifacts[0]
    if any((a["variant"], a["provider_config"]) != (first["variant"], first["provider_config"])
           for a in artifacts):
        raise ValueError("repeat agreement requires the same variant and provider configuration")
    if len({a["repeat_id"] for a in artifacts}) != len(artifacts):
        raise ValueError("distinct repeat IDs required")
    matches = comparisons = 0
    for i, left in enumerate(artifacts):
        for right in artifacts[i + 1:]:
            for lrow, rrow in zip(left["rows"], right["rows"]):
                def signature(row):
                    return sorted((m["mem_type"], m["content"]) for m in row["result"]["memories"])
                matches += signature(lrow) == signature(rrow)
                comparisons += 1
    return {"metric": "exact_typed_output_multiset_agreement",
            "agreement": _ratio(matches, comparisons), "episode_pairs": comparisons,
            "fallback_episodes": sum(telemetry(a)["fallback_episodes"] for a in artifacts)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "d0", "replay", "template", "score"))
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    fixture = json.loads(args.fixture.read_text())
    try:
        validate_fixture(fixture)
        artifact = json.loads(args.capture.read_text()) if args.capture else None
        if args.action == "validate":
            result = {"fixture_valid": True, "label_digest_for_review": label_digest(fixture),
                      "review_status": fixture.get("review", {}).get("status", "draft"),
                      "quality_status": "not_scored"}
        elif args.action == "d0":
            result = capture(fixture, variant="D0")
        elif artifact is None:
            raise ValueError("--capture is required")
        elif args.action == "replay":
            replay(fixture, artifact)
            result = {"replay_matches": True, "provider_requests_this_replay": 0,
                      "quality_status": "not_scored"}
        elif args.action == "template":
            replay(fixture, artifact)
            result = adjudication_template(artifact)
        elif not args.judgments:
            raise ValueError("--judgments is required")
        else:
            result = score(fixture, artifact, json.loads(args.judgments.read_text()))
    except (ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(output)
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
