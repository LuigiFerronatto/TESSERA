"""Load, derive, validate, and write compact benchmark ledger records."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from benchmarks.longmemeval_v1.run import compare_runs, reproducibility_payload
from benchmarks.longmemeval_v1.schemas import validate_artifact_bundle

from .schema import METRIC_RANGES, PROFILE, SCHEMA_VERSION, validate_record


ARTIFACT_FILES = {
    "manifest": "manifest.json",
    "selection": "selected_questions.json",
    "results": "results.json",
    "scorecard": "scorecard.json",
}
FORBIDDEN_LEDGER_KEYS = {
    "question", "question_text", "expected_answer", "answer",
    "has_answer", "answer_session_ids", "ground_truth_session_ids",
    "selected_question_ids", "results",
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON at {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_record(path: Path) -> Dict[str, Any]:
    record = read_json(path)
    validate_record(record)
    assert_no_restricted_content(record)
    return record


def assert_no_restricted_content(value: Any, path: str = "record") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_LEDGER_KEYS:
                raise ValueError(f"{path}.{key}: restricted benchmark content is not allowed")
            assert_no_restricted_content(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_restricted_content(item, f"{path}[{index}]")


def load_artifact_bundle(directory: Path) -> Dict[str, Any]:
    if not directory.is_dir():
        raise ValueError(f"artifact directory does not exist: {directory}")
    payload = {}
    for key, filename in ARTIFACT_FILES.items():
        path = directory / filename
        if not path.is_file():
            raise ValueError(f"artifact directory missing required file: {filename}")
        payload[key] = read_json(path)
    bundle = {
        "manifest": payload["manifest"],
        "results": payload["results"],
        "scorecard": payload["scorecard"],
    }
    validate_artifact_bundle(bundle)
    if not isinstance(payload["selection"], list):
        raise ValueError("selected_questions.json must be a list")
    return payload


def query_ids_sha256(selection: Any) -> str:
    try:
        ordered = sorted(selection, key=lambda item: item["order"])
        ids = [item["question_id"] for item in ordered]
    except (KeyError, TypeError) as exc:
        raise ValueError("selected questions must contain order and question_id") from exc
    if len(ids) != len(set(ids)):
        raise ValueError("selected question IDs must be unique")
    return sha256_json(ids)


def metric_definitions_sha256(scorecard: Mapping[str, Any]) -> str:
    definitions = scorecard.get("metric_definitions")
    if not isinstance(definitions, Mapping):
        raise ValueError("scorecard.metric_definitions must be an object")
    return sha256_json(definitions)


def retrieval_result_payload(artifacts: Mapping[str, Any]) -> Any:
    """Project full results to retrieval-only, provenance-aware signatures.

    Ground-truth labels and question text are deliberately excluded. The
    projection keeps IDs, ordering, scores, context sizes, and provenance.
    """
    projected = []
    for result in artifacts["results"]:
        projected.append(
            {
                "question_id": result["question_id"],
                "corpus_memory_ids": result.get("corpus_memory_ids", []),
                "retrieved": [
                    {
                        "rank": item["rank"],
                        "memory_id": item["memory_id"],
                        "session_id": item["session_id"],
                        "score": item["score"],
                        "provenance_present": item["provenance_present"],
                        "context_characters": item["context_characters"],
                        "context_tokens": item["context_tokens"],
                    }
                    for item in result["retrieved"]
                ],
            }
        )
    return projected


def retrieval_result_sha256(directory: Path) -> str:
    return sha256_json(retrieval_result_payload(load_artifact_bundle(directory)))


def normalized_artifact_sha256(directory: Path) -> str:
    return sha256_json(reproducibility_payload(directory))


def record_from_artifacts(
    directory: Path,
    *,
    record_id: str,
    issue: int,
    pull_request: int,
    decision: str,
    parent_record_id: Optional[str],
    merge_commit: Optional[str] = None,
    repeat_directory: Optional[Path] = None,
) -> Dict[str, Any]:
    artifacts = load_artifact_bundle(directory)
    manifest = artifacts["manifest"]
    scorecard = artifacts["scorecard"]
    counts = scorecard["counts"]
    metrics = scorecard["metrics"]
    equivalent = True
    run_count = 1
    if repeat_directory is not None:
        load_artifact_bundle(repeat_directory)
        equivalent = compare_runs(directory, repeat_directory)
        run_count = 2

    record = {
        "schema_version": SCHEMA_VERSION,
        "record_id": record_id,
        "benchmark": manifest["benchmark"],
        "profile": PROFILE,
        "issue": issue,
        "pull_request": pull_request,
        "decision": decision,
        "measured_commit": manifest["tessera_commit"],
        "merge_commit": merge_commit,
        "parent_record_id": parent_record_id,
        "retrieval_contract_commit": manifest["retrieval_contract_commit"],
        "dataset": {
            "name": manifest["dataset_file"],
            "revision": manifest["benchmark_version"],
            "source_url": manifest["dataset_url"],
            "upstream_commit": manifest["source_commit"],
            "sha256": manifest["dataset_sha256"],
            "query_count": counts["selected_instances"],
            "positive_count": counts["positive_instances"],
            "abstention_count": counts["abstention_instances"],
        },
        "configuration": {
            "subset": scorecard["subset"],
            "top_k": manifest["top_k"],
            "granularity": manifest["retrieval_granularity"],
            "reader": scorecard["run_configuration"].get("reader"),
            "judge": None,
            "retrieval_configuration": scorecard["run_configuration"],
            "metric_definitions_sha256": metric_definitions_sha256(scorecard),
            "token_count_method": manifest["token_count_method"],
            "adapter_version": manifest["adapter_version"],
        },
        "selection": {
            "algorithm": manifest["selection_algorithm"],
            "seed": manifest["selection_seed"],
            "query_ids_sha256": query_ids_sha256(artifacts["selection"]),
            "query_count": len(artifacts["selection"]),
        },
        "determinism": {
            "run_count": run_count,
            "equivalent": equivalent,
            "normalized_sha256": normalized_artifact_sha256(directory),
            "retrieval_result_sha256": sha256_json(
                retrieval_result_payload(artifacts)
            ),
        },
        "metrics": {name: metrics[name] for name in METRIC_RANGES},
        "latency": {
            "comparable_environment": False,
            "indexing_latency_ms": metrics.get("indexing_latency_ms"),
            "total_indexing_latency_ms": metrics.get("total_indexing_latency_ms"),
            "query_latency_p50_ms": metrics.get("query_latency_p50_ms"),
            "query_latency_p95_ms": metrics.get("query_latency_p95_ms"),
        },
        "cost": {"api_calls": 0, "llm_calls": 0, "estimated_usd": 0},
        "environment": {
            "python_version": manifest.get("python_version"),
            "platform": None,
            "repository_dirty": manifest.get("repository_dirty"),
        },
        "limitations": list(scorecard.get("limitations", [])),
        "created_at": manifest["created_at"],
    }
    validate_record(record)
    assert_no_restricted_content(record)
    return record


def validate_output_path(path: Path, allowed_root: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"output path must not be a symlink: {path}")
    root = allowed_root.resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"output path {path} escapes allowed root {allowed_root}")
    return resolved
