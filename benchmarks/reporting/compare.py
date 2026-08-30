"""Deterministic baseline/candidate comparison CLI and library."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .records import (
    load_artifact_bundle,
    load_record,
    record_from_artifacts,
    write_json,
)
from .render import render_comparison


HIGHER_IS_BETTER = {
    "recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10", "mrr",
    "ndcg_at_10", "evidence_hit_rate", "provenance_coverage",
}
LOWER_IS_BETTER = {
    "first_evidence_position", "average_context_characters",
    "average_context_tokens", "api_calls", "llm_calls", "estimated_usd",
    "indexing_latency_ms", "total_indexing_latency_ms",
    "query_latency_p50_ms", "query_latency_p95_ms",
}
INFORMATIONAL = {"abstention_retrieval_empty_rate"}
LATENCY_METRICS = {
    "indexing_latency_ms", "total_indexing_latency_ms",
    "query_latency_p50_ms", "query_latency_p95_ms",
}
GATING_METRICS = set(HIGHER_IS_BETTER)

COMPATIBILITY_PATHS = (
    "benchmark",
    "profile",
    "dataset.name",
    "dataset.revision",
    "dataset.sha256",
    "dataset.upstream_commit",
    "dataset.query_count",
    "dataset.positive_count",
    "dataset.abstention_count",
    "selection.query_ids_sha256",
    "selection.query_count",
    "configuration.subset",
    "configuration.top_k",
    "configuration.granularity",
    "configuration.reader",
    "configuration.judge",
    "configuration.retrieval_configuration",
    "configuration.metric_definitions_sha256",
    "configuration.token_count_method",
    "configuration.adapter_version",
)


def _path(record: Mapping[str, Any], dotted: str) -> Any:
    value: Any = record
    for part in dotted.split("."):
        value = value[part]
    return value


def validate_compatibility(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> Sequence[str]:
    baseline_major = baseline["schema_version"].split(".", 1)[0]
    candidate_major = candidate["schema_version"].split(".", 1)[0]
    if baseline_major != candidate_major:
        raise ValueError(
            "incompatible field schema_version: "
            f"baseline={baseline['schema_version']!r}, "
            f"candidate={candidate['schema_version']!r}"
        )
    checked = ["schema_version (compatible 1.x ledger contracts)"]
    for dotted in COMPATIBILITY_PATHS:
        baseline_value = _path(baseline, dotted)
        candidate_value = _path(candidate, dotted)
        if baseline_value != candidate_value:
            raise ValueError(
                f"incompatible field {dotted}: baseline={baseline_value!r}, "
                f"candidate={candidate_value!r}"
            )
        checked.append(dotted)
    baseline_environment = baseline["environment"]
    candidate_environment = candidate["environment"]
    if baseline_environment.get("complete") and candidate_environment.get("complete"):
        for field in ("constraints_sha256", "fingerprint_sha256"):
            dotted = f"environment.{field}"
            if baseline_environment[field] != candidate_environment[field]:
                raise ValueError(
                    f"incompatible field {dotted}: "
                    f"baseline={baseline_environment[field]!r}, "
                    f"candidate={candidate_environment[field]!r}"
                )
            checked.append(dotted)
    return checked


def metric_delta(
    name: str,
    baseline: Optional[float],
    candidate: Optional[float],
    *,
    decision_gating: Optional[bool] = None,
    threshold: Optional[float] = None,
    force_informational: bool = False,
    comparable_latency: bool = False,
) -> Dict[str, Any]:
    absolute = (
        None if baseline is None or candidate is None else candidate - baseline
    )
    relative = (
        None
        if absolute is None or baseline == 0
        else absolute / abs(baseline)
    )
    unavailable_status = None
    if baseline is not None and candidate is None:
        unavailable_status = "regressed"
    elif baseline is None and candidate is not None:
        unavailable_status = "improved"
    elif baseline is None and candidate is None:
        unavailable_status = "unchanged"
    if force_informational or name in INFORMATIONAL or (
        name in LATENCY_METRICS and not comparable_latency
    ):
        semantic_direction = "informational"
        status = "informational"
    elif name in HIGHER_IS_BETTER:
        semantic_direction = "higher_is_better"
        status = unavailable_status or (
            "improved" if absolute > 0 else "regressed" if absolute < 0 else "unchanged"
        )
    elif name in LOWER_IS_BETTER:
        semantic_direction = "lower_is_better"
        status = unavailable_status or (
            "improved" if absolute < 0 else "regressed" if absolute > 0 else "unchanged"
        )
    else:
        semantic_direction = "informational"
        status = "informational"
    gating = name in GATING_METRICS if decision_gating is None else decision_gating
    return {
        "baseline": baseline,
        "candidate": candidate,
        "absolute_delta": absolute,
        "relative_delta": relative,
        "semantic_direction": semantic_direction,
        "status": status,
        "decision_gating": gating,
        "threshold": threshold,
        "threshold_passed": (
            None
            if threshold is None
            else False
            if absolute is None
            else (-absolute if semantic_direction == "lower_is_better" else absolute)
            >= threshold
        ),
    }


def _first_relevant(retrieved: Sequence[Mapping[str, Any]]) -> Optional[int]:
    return next((item["rank"] for item in retrieved if item.get("is_relevant")), None)


def compare_query_artifacts(
    baseline_directory: Path, candidate_directory: Path
) -> Dict[str, Any]:
    baseline = load_artifact_bundle(baseline_directory)
    candidate = load_artifact_bundle(candidate_directory)
    baseline_selection = [item["question_id"] for item in baseline["selection"]]
    candidate_selection = [item["question_id"] for item in candidate["selection"]]
    if baseline_selection != candidate_selection:
        raise ValueError("incompatible field selected question IDs/order")
    baseline_results = baseline["results"]
    candidate_results = candidate["results"]
    if [item["question_id"] for item in baseline_results] != [
        item["question_id"] for item in candidate_results
    ]:
        raise ValueError("incompatible field result question IDs/order")

    changes = []
    for before, after in zip(baseline_results, candidate_results):
        before_items = before["retrieved"]
        after_items = after["retrieved"]
        before_ids = [item["session_id"] for item in before_items]
        after_ids = [item["session_id"] for item in after_items]
        before_relevant = [item["session_id"] for item in before_items if item["is_relevant"]]
        after_relevant = [item["session_id"] for item in after_items if item["is_relevant"]]
        before_rank = _first_relevant(before_items)
        after_rank = _first_relevant(after_items)
        provenance_before = all(item["provenance_present"] for item in before_items)
        provenance_after = all(item["provenance_present"] for item in after_items)
        context_before = sum(item["context_characters"] for item in before_items)
        context_after = sum(item["context_characters"] for item in after_items)
        scores_before = [item["score"] for item in before_items]
        scores_after = [item["score"] for item in after_items]
        relevant_gained = sorted(set(after_relevant) - set(before_relevant))
        relevant_lost = sorted(set(before_relevant) - set(after_relevant))
        classifications = []
        if before_rank is not None and after_rank is None:
            classifications.append("retrieval_regression")
        if before_rank is None and after_rank is not None:
            classifications.append("retrieval_improvement")
        if relevant_lost:
            classifications.append("relevant_session_loss")
        if relevant_gained:
            classifications.append("relevant_session_gain")
        if before_rank is not None and after_rank is not None:
            if after_rank > before_rank:
                classifications.append("first_evidence_rank_regression")
            elif after_rank < before_rank:
                classifications.append("first_evidence_rank_improvement")
        if provenance_before and not provenance_after:
            classifications.append("provenance_regression")
        if context_before != context_after:
            classifications.append("context_size_change")
        if (
            (before_ids != after_ids or scores_before != scores_after)
            and not relevant_gained
            and not relevant_lost
            and before_rank == after_rank
            and provenance_before == provenance_after
            and context_before == context_after
        ):
            classifications.append("ranking_only_change")
        if not classifications:
            classifications.append("no_semantic_change")
        changes.append(
            {
                "question_id": before["question_id"],
                "classifications": classifications,
                "hit_before": before_rank is not None,
                "hit_after": after_rank is not None,
                "first_evidence_rank_before": before_rank,
                "first_evidence_rank_after": after_rank,
                "retrieved_ids_changed": before_ids != after_ids,
                "relevant_retrieved_ids_gained": relevant_gained,
                "relevant_retrieved_ids_lost": relevant_lost,
                "context_characters_delta": context_after - context_before,
                "scores_changed": scores_before != scores_after,
                "provenance_before": provenance_before,
                "provenance_after": provenance_after,
            }
        )
    regressions = [
        item for item in changes
        if "retrieval_regression" in item["classifications"]
        or "first_evidence_rank_regression" in item["classifications"]
        or "provenance_regression" in item["classifications"]
        or item["relevant_retrieved_ids_lost"]
    ]
    improvements = [
        item for item in changes
        if "retrieval_improvement" in item["classifications"]
        or "first_evidence_rank_improvement" in item["classifications"]
        or item["relevant_retrieved_ids_gained"]
    ]
    return {
        "available": True,
        "query_count": len(changes),
        "changes": changes,
        "improvements": improvements,
        "regressions": regressions,
        "no_semantic_change_count": sum(
            item["classifications"] == ["no_semantic_change"] for item in changes
        ),
    }


def validate_artifacts_match_record(
    record: Mapping[str, Any],
    directory: Path,
    *,
    require_result_equivalence: bool,
) -> Mapping[str, Any]:
    derived = record_from_artifacts(
        directory,
        record_id="runtime-validation",
        issue=0,
        pull_request=0,
        decision="PENDING",
        parent_record_id=None,
    )
    validate_compatibility(record, derived)
    if record["measured_commit"] != derived["measured_commit"]:
        raise ValueError(
            "artifact measured_commit does not match record: "
            f"record={record['measured_commit']!r}, "
            f"artifact={derived['measured_commit']!r}"
        )
    if require_result_equivalence and record["metrics"] != derived["metrics"]:
        raise ValueError("artifact non-latency metrics do not match record")
    if require_result_equivalence and (
        record["determinism"]["retrieval_result_sha256"]
        != derived["determinism"]["retrieval_result_sha256"]
    ):
        raise ValueError("artifact retrieval-result signature does not match record")
    return derived


def compare_records(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    thresholds: Optional[Mapping[str, float]] = None,
    baseline_artifacts: Optional[Path] = None,
    candidate_artifacts: Optional[Path] = None,
) -> Dict[str, Any]:
    checked = validate_compatibility(baseline, candidate)
    thresholds = dict(thresholds or {})
    unknown_thresholds = sorted(set(thresholds) - set(baseline["metrics"]))
    if unknown_thresholds:
        raise ValueError(f"unknown threshold metrics: {', '.join(unknown_thresholds)}")
    metrics = {
        name: metric_delta(
            name,
            baseline["metrics"][name],
            candidate["metrics"][name],
            threshold=thresholds.get(name),
        )
        for name in baseline["metrics"]
    }
    comparable_latency = bool(
        baseline["latency"]["comparable_environment"]
        and candidate["latency"]["comparable_environment"]
        and baseline["environment"] == candidate["environment"]
    )
    baseline_environment_complete = bool(baseline["environment"].get("complete"))
    candidate_environment_complete = bool(candidate["environment"].get("complete"))
    environment_fingerprint_match = (
        baseline["environment"].get("fingerprint_sha256")
        == candidate["environment"].get("fingerprint_sha256")
        if baseline_environment_complete and candidate_environment_complete
        else None
    )
    latency = {"comparable_environment": comparable_latency, "metrics": {}}
    for name in baseline["latency"]:
        if name == "comparable_environment":
            continue
        before = baseline["latency"][name]
        after = candidate["latency"][name]
        latency["metrics"][name] = (
            None
            if before is None or after is None
            else metric_delta(
                name, before, after,
                decision_gating=False,
                force_informational=not comparable_latency,
                comparable_latency=comparable_latency,
            )
        )
    cost = {
        name: metric_delta(
            name,
            baseline["cost"][name],
            candidate["cost"][name],
            decision_gating=False,
        )
        for name in ("api_calls", "llm_calls", "estimated_usd")
    }
    if baseline_artifacts is not None or candidate_artifacts is not None:
        if baseline_artifacts is None or candidate_artifacts is None:
            raise ValueError("query-level comparison requires both artifact directories")
        baseline_runtime = validate_artifacts_match_record(
            baseline,
            baseline_artifacts,
            require_result_equivalence=False,
        )
        validate_artifacts_match_record(
            candidate,
            candidate_artifacts,
            require_result_equivalence=True,
        )
        query_level = compare_query_artifacts(baseline_artifacts, candidate_artifacts)
        baseline_runtime_drift = {
            "available": True,
            "metrics_match_versioned_record": (
                baseline_runtime["metrics"] == baseline["metrics"]
            ),
            "retrieval_signature_match_versioned_record": (
                baseline_runtime["determinism"]["retrieval_result_sha256"]
                == baseline["determinism"]["retrieval_result_sha256"]
            ),
            "runtime_retrieval_result_sha256": baseline_runtime["determinism"][
                "retrieval_result_sha256"
            ],
        }
    else:
        query_level = {
            "available": False,
            "query_count": 0,
            "changes": [],
            "improvements": [],
            "regressions": [],
            "no_semantic_change_count": 0,
        }
        baseline_runtime_drift = {
            "available": False,
            "metrics_match_versioned_record": None,
            "retrieval_signature_match_versioned_record": None,
            "runtime_retrieval_result_sha256": None,
        }
    provenance_regression = (
        candidate["metrics"]["provenance_coverage"]
        < baseline["metrics"]["provenance_coverage"]
        or any(
            "provenance_regression" in item["classifications"]
            for item in query_level["changes"]
        )
    )
    gating_regressions = sum(
        item["status"] == "regressed" and item["decision_gating"]
        for item in metrics.values()
    )
    threshold_failures = [
        name for name, item in metrics.items() if item["threshold_passed"] is False
    ]
    same_commit = baseline["measured_commit"] == candidate["measured_commit"]
    normalized_sha_match = (
        baseline["determinism"]["normalized_sha256"]
        == candidate["determinism"]["normalized_sha256"]
    )
    determinism_regression = (
        not candidate["determinism"]["equivalent"]
        or (same_commit and not normalized_sha_match)
    )
    decision = "ITERATE" if (
        provenance_regression or gating_regressions or threshold_failures
        or query_level["regressions"] or determinism_regression
    ) else "KEEP"
    return {
        "schema_version": "1.0.0",
        "comparison_id": f"{baseline['record_id']}..{candidate['record_id']}",
        "baseline": {
            "record_id": baseline["record_id"],
            "measured_commit": baseline["measured_commit"],
        },
        "candidate": {
            "record_id": candidate["record_id"],
            "measured_commit": candidate["measured_commit"],
        },
        "compatibility": {"compatible": True, "checked_fields": list(checked)},
        "environment_context": {
            "baseline_complete": baseline_environment_complete,
            "candidate_complete": candidate_environment_complete,
            "fingerprint_match": environment_fingerprint_match,
            "historical_context_incomplete": not baseline_environment_complete,
        },
        "metrics": metrics,
        "latency": latency,
        "cost": cost,
        "determinism": {
            "candidate_run_count": candidate["determinism"]["run_count"],
            "candidate_equivalent": candidate["determinism"]["equivalent"],
            "same_commit_hash_rule": same_commit,
            "normalized_sha_match": normalized_sha_match,
            "regression": determinism_regression,
            "retrieval_signature_match": (
                baseline["determinism"]["retrieval_result_sha256"]
                == candidate["determinism"]["retrieval_result_sha256"]
            ),
        },
        "provenance": {"regression": provenance_regression},
        "query_level": query_level,
        "baseline_runtime_drift": baseline_runtime_drift,
        "summary": {
            "gating_regressions": gating_regressions,
            "threshold_failures": threshold_failures,
            "improvements": sum(item["status"] == "improved" for item in metrics.values()),
            "unchanged": sum(item["status"] == "unchanged" for item in metrics.values()),
        },
        "limitations": sorted(set(baseline["limitations"] + candidate["limitations"])),
        "decision": decision,
    }


def _threshold(value: str) -> Tuple[str, float]:
    try:
        name, raw = value.split("=", 1)
        return name, float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("threshold must use METRIC=MINIMUM_DELTA") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-artifacts", type=Path)
    parser.add_argument("--candidate-artifacts", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--threshold", action="append", type=_threshold, default=[])
    parser.add_argument("--fail-on-regression", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    baseline = load_record(args.baseline)
    if args.candidate.is_dir():
        candidate = record_from_artifacts(
            args.candidate,
            record_id=f"candidate/{args.candidate.name}",
            issue=0,
            pull_request=0,
            decision="PENDING",
            parent_record_id=baseline["record_id"],
        )
    else:
        candidate = load_record(args.candidate)
    comparison = compare_records(
        baseline,
        candidate,
        thresholds=dict(args.threshold),
        baseline_artifacts=args.baseline_artifacts,
        candidate_artifacts=args.candidate_artifacts,
    )
    write_json(args.output_json, comparison)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_comparison(comparison), encoding="utf-8")
    print(json.dumps(comparison["summary"], sort_keys=True))
    if args.fail_on_regression and comparison["decision"] != "KEEP":
        raise SystemExit("benchmark comparison failed: decision is not KEEP")


if __name__ == "__main__":
    main()
