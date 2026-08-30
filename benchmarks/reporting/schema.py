"""Strict, dependency-free schema validation for benchmark ledger records."""

import math
import re
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence, Set


SCHEMA_VERSION = "1.0.0"
BENCHMARK = "LongMemEval V1"
PROFILE = "longmemeval-v1-dev-50"
DECISIONS = {"KEEP", "ITERATE", "REVERT", "DROP", "PENDING"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

METRIC_RANGES = {
    "recall_at_1": (0.0, 1.0),
    "recall_at_3": (0.0, 1.0),
    "recall_at_5": (0.0, 1.0),
    "recall_at_10": (0.0, 1.0),
    "mrr": (0.0, 1.0),
    "ndcg_at_10": (0.0, 1.0),
    "evidence_hit_rate": (0.0, 1.0),
    "first_evidence_position": (1.0, None),
    "provenance_coverage": (0.0, 1.0),
    "abstention_retrieval_empty_rate": (0.0, 1.0),
    "average_context_characters": (0.0, None),
    "average_context_tokens": (0.0, None),
}

RECORD_FIELDS = {
    "schema_version", "record_id", "benchmark", "profile", "issue",
    "pull_request", "decision", "measured_commit", "merge_commit",
    "parent_record_id", "retrieval_contract_commit", "dataset",
    "configuration", "selection", "determinism", "metrics", "latency",
    "cost", "environment", "limitations", "created_at",
}
DATASET_FIELDS = {
    "name", "revision", "source_url", "upstream_commit", "sha256",
    "query_count", "positive_count", "abstention_count",
}
CONFIGURATION_FIELDS = {
    "subset", "top_k", "granularity", "reader", "judge",
    "retrieval_configuration", "metric_definitions_sha256",
    "token_count_method", "adapter_version",
}
SELECTION_FIELDS = {"algorithm", "seed", "query_ids_sha256", "query_count"}
DETERMINISM_FIELDS = {
    "run_count", "equivalent", "normalized_sha256", "retrieval_result_sha256",
}
LATENCY_FIELDS = {
    "comparable_environment", "indexing_latency_ms",
    "total_indexing_latency_ms", "query_latency_p50_ms", "query_latency_p95_ms",
}
COST_FIELDS = {"api_calls", "llm_calls", "estimated_usd"}
ENVIRONMENT_FIELDS = {"python_version", "platform", "repository_dirty"}


def _fail(path: str, message: str) -> None:
    raise ValueError(f"{path}: {message}")


def _object(value: Any, path: str, fields: Set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    missing = sorted(fields - set(value))
    extra = sorted(set(value) - fields)
    if missing:
        _fail(path, f"missing required fields: {', '.join(missing)}")
    if extra:
        _fail(path, f"unsupported fields: {', '.join(extra)}")
    return value


def _string(value: Any, path: str, nullable: bool = False) -> Optional[str]:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value:
        _fail(path, "must be a non-empty string")
    return value


def _integer(value: Any, path: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(path, "must be an integer")
    if value < minimum:
        _fail(path, f"must be >= {minimum}")
    return value


def _number(value: Any, path: str, nullable: bool = False) -> Optional[float]:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        _fail(path, "must be finite (NaN and Infinity are unsupported)")
    return numeric


def _boolean(value: Any, path: str, nullable: bool = False) -> Optional[bool]:
    if value is None and nullable:
        return None
    if not isinstance(value, bool):
        _fail(path, "must be a boolean")
    return value


def _sha256(value: Any, path: str) -> str:
    text = _string(value, path)
    if not SHA256_RE.fullmatch(text):
        _fail(path, "must be a lowercase 64-character SHA-256")
    return text


def _git_sha(value: Any, path: str, nullable: bool = False) -> Optional[str]:
    text = _string(value, path, nullable=nullable)
    if text is not None and not re.fullmatch(r"[0-9a-f]{40}", text):
        _fail(path, "must be a lowercase 40-character Git SHA")
    return text


def _json_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            _fail(path, "contains NaN or Infinity")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(path, "object keys must be strings")
            _json_value(item, f"{path}.{key}")
        return
    _fail(path, f"contains unsupported value type {type(value).__name__}")


def validate_record(record: Mapping[str, Any]) -> None:
    """Validate a ledger record using the closed v1 contract.

    All ledger-owned objects reject unknown fields. The nested
    ``retrieval_configuration`` object is intentionally open because it records
    the complete runtime configuration of future retrieval experiments; it must
    still contain only deterministic JSON values and is compared by exact value.
    """
    record = _object(record, "record", RECORD_FIELDS)
    if record["schema_version"] != SCHEMA_VERSION:
        _fail(
            "record.schema_version",
            f"unsupported version {record['schema_version']!r}; expected {SCHEMA_VERSION!r}",
        )
    _string(record["record_id"], "record.record_id")
    if record["benchmark"] != BENCHMARK:
        _fail("record.benchmark", f"must be {BENCHMARK!r}")
    if record["profile"] != PROFILE:
        _fail("record.profile", f"must be {PROFILE!r}")
    _integer(record["issue"], "record.issue")
    _integer(record["pull_request"], "record.pull_request")
    if record["decision"] not in DECISIONS:
        _fail("record.decision", f"unsupported decision {record['decision']!r}")
    _git_sha(record["measured_commit"], "record.measured_commit")
    _git_sha(record["merge_commit"], "record.merge_commit", nullable=True)
    _string(record["parent_record_id"], "record.parent_record_id", nullable=True)
    _git_sha(record["retrieval_contract_commit"], "record.retrieval_contract_commit")

    dataset = _object(record["dataset"], "record.dataset", DATASET_FIELDS)
    _string(dataset["name"], "record.dataset.name")
    _string(dataset["revision"], "record.dataset.revision")
    _string(dataset["source_url"], "record.dataset.source_url")
    _git_sha(dataset["upstream_commit"], "record.dataset.upstream_commit")
    _sha256(dataset["sha256"], "record.dataset.sha256")
    query_count = _integer(dataset["query_count"], "record.dataset.query_count", 1)
    positive_count = _integer(dataset["positive_count"], "record.dataset.positive_count")
    abstention_count = _integer(
        dataset["abstention_count"], "record.dataset.abstention_count"
    )
    if positive_count + abstention_count != query_count:
        _fail(
            "record.dataset",
            "positive_count + abstention_count must equal query_count",
        )
    if (query_count, positive_count, abstention_count) != (50, 46, 4):
        _fail(
            "record.dataset",
            "longmemeval-v1-dev-50 requires 50 queries (46 positive, 4 abstention)",
        )

    configuration = _object(
        record["configuration"], "record.configuration", CONFIGURATION_FIELDS
    )
    if configuration["subset"] != "deterministic-small":
        _fail("record.configuration.subset", "must be 'deterministic-small'")
    if _integer(configuration["top_k"], "record.configuration.top_k", 1) != 10:
        _fail("record.configuration.top_k", "profile requires 10")
    if configuration["granularity"] != "session":
        _fail("record.configuration.granularity", "profile requires 'session'")
    if configuration["reader"] is not None:
        _fail("record.configuration.reader", "retrieval-only profile requires null")
    if configuration["judge"] is not None:
        _fail("record.configuration.judge", "retrieval-only profile requires null")
    if not isinstance(configuration["retrieval_configuration"], Mapping):
        _fail("record.configuration.retrieval_configuration", "must be an object")
    _json_value(
        configuration["retrieval_configuration"],
        "record.configuration.retrieval_configuration",
    )
    _sha256(
        configuration["metric_definitions_sha256"],
        "record.configuration.metric_definitions_sha256",
    )
    _string(configuration["token_count_method"], "record.configuration.token_count_method")
    _string(configuration["adapter_version"], "record.configuration.adapter_version")

    selection = _object(record["selection"], "record.selection", SELECTION_FIELDS)
    _string(selection["algorithm"], "record.selection.algorithm")
    _string(selection["seed"], "record.selection.seed")
    _sha256(selection["query_ids_sha256"], "record.selection.query_ids_sha256")
    if _integer(selection["query_count"], "record.selection.query_count", 1) != query_count:
        _fail("record.selection.query_count", "must equal dataset.query_count")

    determinism = _object(
        record["determinism"], "record.determinism", DETERMINISM_FIELDS
    )
    _integer(determinism["run_count"], "record.determinism.run_count", 1)
    _boolean(determinism["equivalent"], "record.determinism.equivalent")
    _sha256(determinism["normalized_sha256"], "record.determinism.normalized_sha256")
    _sha256(
        determinism["retrieval_result_sha256"],
        "record.determinism.retrieval_result_sha256",
    )

    metrics = _object(record["metrics"], "record.metrics", set(METRIC_RANGES))
    for name, (minimum, maximum) in METRIC_RANGES.items():
        numeric = _number(
            metrics[name],
            f"record.metrics.{name}",
            nullable=name == "first_evidence_position",
        )
        if numeric is None:
            continue
        if numeric < minimum or (maximum is not None and numeric > maximum):
            upper = "unbounded" if maximum is None else str(maximum)
            _fail(
                f"record.metrics.{name}",
                f"must be in range [{minimum}, {upper}]",
            )

    latency = _object(record["latency"], "record.latency", LATENCY_FIELDS)
    _boolean(latency["comparable_environment"], "record.latency.comparable_environment")
    for name in LATENCY_FIELDS - {"comparable_environment"}:
        numeric = _number(latency[name], f"record.latency.{name}", nullable=True)
        if numeric is not None and numeric < 0:
            _fail(f"record.latency.{name}", "must be >= 0")

    cost = _object(record["cost"], "record.cost", COST_FIELDS)
    _integer(cost["api_calls"], "record.cost.api_calls")
    _integer(cost["llm_calls"], "record.cost.llm_calls")
    estimated = _number(cost["estimated_usd"], "record.cost.estimated_usd")
    if estimated < 0:
        _fail("record.cost.estimated_usd", "must be >= 0")

    environment = _object(
        record["environment"], "record.environment", ENVIRONMENT_FIELDS
    )
    _string(environment["python_version"], "record.environment.python_version", nullable=True)
    _string(environment["platform"], "record.environment.platform", nullable=True)
    _boolean(
        environment["repository_dirty"],
        "record.environment.repository_dirty",
        nullable=True,
    )
    if not isinstance(record["limitations"], list) or not all(
        isinstance(item, str) and item for item in record["limitations"]
    ):
        _fail("record.limitations", "must be a list of non-empty strings")
    created_at = _string(record["created_at"], "record.created_at")
    try:
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail("record.created_at", f"must be ISO-8601: {exc}")
