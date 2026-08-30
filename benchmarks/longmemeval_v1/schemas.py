"""Artifact schemas and lightweight validation for the benchmark."""

from typing import Any, Dict, Mapping


MANIFEST_REQUIRED = {
    "benchmark", "benchmark_version", "source_repository", "source_commit",
    "dataset_url", "dataset_file", "dataset_sha256", "dataset_instances",
    "selected_instances", "selection_algorithm", "selection_seed",
    "retrieval_granularity", "top_k", "license", "tessera_commit",
    "retrieval_contract_commit", "repository_dirty", "repository_root",
    "dirty_worktree_override",
    "reproducible",
    "python_version", "adapter_version", "token_count_method", "created_at",
    "question_type_quotas", "abstention_instances", "retrieval_configuration",
    "run_count",
}

RESULT_REQUIRED = {
    "question_id", "question_type", "is_abstention", "question",
    "ground_truth_session_ids", "retrieved", "latency_ms",
    "indexing_latency_ms",
}

RETRIEVED_REQUIRED = {
    "rank", "memory_id", "session_id", "score", "is_relevant",
    "provenance_present", "context_characters", "context_tokens",
}

SCORECARD_REQUIRED = {
    "schema_version", "benchmark", "subset", "counts", "metrics",
    "metric_definitions", "run_configuration", "limitations",
}


def _require(mapping: Mapping[str, Any], required: set, label: str) -> None:
    missing = sorted(required - set(mapping))
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    _require(manifest, MANIFEST_REQUIRED, "manifest")


def validate_result(result: Mapping[str, Any]) -> None:
    _require(result, RESULT_REQUIRED, "result")
    if not isinstance(result["retrieved"], list):
        raise ValueError("result.retrieved must be a list")
    for item in result["retrieved"]:
        _require(item, RETRIEVED_REQUIRED, "retrieved result")


def validate_scorecard(scorecard: Mapping[str, Any]) -> None:
    _require(scorecard, SCORECARD_REQUIRED, "scorecard")


def validate_artifact_bundle(bundle: Dict[str, Any]) -> None:
    validate_manifest(bundle["manifest"])
    for result in bundle["results"]:
        validate_result(result)
    validate_scorecard(bundle["scorecard"])
