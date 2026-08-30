import copy
import json
from pathlib import Path

import pytest
import yaml

from benchmarks.longmemeval_v1 import DATASET_SHA256, RETRIEVAL_CONTRACT_COMMIT
from benchmarks.longmemeval_v1.prepare_dataset import verify_dataset
from benchmarks.reporting.applicability import parse_applicability
from benchmarks.reporting.compare import (
    compare_query_artifacts,
    compare_records,
    metric_delta,
    validate_compatibility,
)
from benchmarks.reporting.environment import (
    collect_environment,
    environment_fingerprint,
    validate_environment_reference,
)
from benchmarks.reporting.records import (
    assert_no_restricted_content,
    load_record,
    normalized_artifact_sha256,
    record_from_artifacts,
    retrieval_result_sha256,
    validate_output_path,
)
from benchmarks.reporting.render import render_comparison, render_record
from benchmarks.reporting.schema import (
    HISTORICAL_SCHEMA_VERSION,
    SCHEMA_VERSION,
    validate_record,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE_JSON = ROOT / "benchmarks/results/longmemeval-v1-dev-50/baseline.json"
BASELINE_MD = ROOT / "benchmarks/results/longmemeval-v1-dev-50/baseline.md"


@pytest.fixture
def baseline():
    return load_record(BASELINE_JSON)


def changed(record, dotted, value):
    result = copy.deepcopy(record)
    target = result
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    return result


def _write_artifacts(
    root: Path,
    *,
    commit: str = "c" * 40,
    retrieved_session: str = "session-a",
    score: float = 0.75,
    provenance: bool = True,
    context_characters: int = 100,
    created_at: str = "2026-01-01T00:00:00+00:00",
    latency: float = 1.0,
) -> Path:
    root.mkdir(parents=True)
    selection = []
    results = []
    for index in range(50):
        question_id = f"q-{index:02d}"
        abstention = index >= 46
        selection.append(
            {
                "order": index + 1,
                "question_id": question_id,
                "question_type": "synthetic_abs" if abstention else "synthetic",
                "is_abstention": abstention,
                "selection_hash": f"{index:064x}",
            }
        )
        expected = [] if abstention else ["session-a"]
        retrieved = [
            {
                "rank": 1,
                "memory_id": f"longmemeval-v1/{question_id}/{retrieved_session}",
                "session_id": retrieved_session,
                "score": score,
                "is_relevant": retrieved_session in expected,
                "provenance_present": provenance,
                "context_characters": context_characters,
                "context_tokens": context_characters // 5,
            }
        ]
        results.append(
            {
                "question_id": question_id,
                "question_type": "synthetic_abs" if abstention else "synthetic",
                "is_abstention": abstention,
                "question": "synthetic fixture question",
                "ground_truth_session_ids": expected,
                "corpus_memory_ids": [
                    f"longmemeval-v1/{question_id}/session-a",
                    f"longmemeval-v1/{question_id}/session-b",
                ],
                "retrieved": retrieved,
                "first_evidence_position": None if abstention else (
                    1 if retrieved_session == "session-a" else None
                ),
                "latency_ms": latency,
                "indexing_latency_ms": latency * 2,
            }
        )
    retrieval_configuration = {
        "engine": "TesseraEngine.retrieve_context_contract",
        "weights": "runtime-defaults",
        "resolve_conflicts": True,
        "top_k": 10,
        "reader": None,
    }
    manifest = {
        "benchmark": "LongMemEval V1",
        "benchmark_version": "cleaned-2025-09",
        "source_repository": "https://github.com/xiaowu0162/LongMemEval",
        "source_commit": "9e0b455f4ef0e2ab8f2e582289761153549043fc",
        "dataset_url": "https://example.invalid/fixture.json",
        "dataset_file": "longmemeval_s_cleaned.json",
        "dataset_sha256": DATASET_SHA256,
        "dataset_instances": 500,
        "selected_instances": 50,
        "selection_algorithm": "sha256-stratified",
        "selection_seed": "tessera-lme-v1-96",
        "selected_question_ids": [item["question_id"] for item in selection],
        "question_type_quotas": {"synthetic": 46, "synthetic_abs": 4},
        "abstention_instances": 4,
        "retrieval_granularity": "session",
        "top_k": 10,
        "license": "MIT",
        "repository_root": ".",
        "repository_dirty": False,
        "dirty_worktree_override": False,
        "reproducible": True,
        "tessera_commit": commit,
        "retrieval_contract_commit": RETRIEVAL_CONTRACT_COMMIT,
        "python_version": "3.12.3",
        "adapter_version": "1",
        "token_count_method": "whitespace",
        "created_at": created_at,
        "retrieval_configuration": retrieval_configuration,
        "run_count": 1,
    }
    metric_definitions = {
        "relevance": "binary answer_session_ids membership",
        "recall": "relevant sessions retrieved divided by relevant sessions",
        "mrr": "reciprocal rank of first relevant session",
        "ndcg_at_10": "binary relevance, logarithmic discount",
        "evidence_hit_rate": "non-abstention queries with a relevant Top-K session",
        "first_evidence_position": "mean first relevant rank among queries with a hit",
        "provenance_coverage": "results retaining provenance plus question/session metadata",
        "abstention": "excluded from relevance metrics; retrieval emptiness reported separately",
        "tokens": "whitespace-delimited count, not model tokens",
    }
    hit = retrieved_session == "session-a"
    metrics = {
        "recall_at_1": float(hit),
        "recall_at_3": float(hit),
        "recall_at_5": float(hit),
        "recall_at_10": float(hit),
        "mrr": float(hit),
        "ndcg_at_10": float(hit),
        "evidence_hit_rate": float(hit),
        "first_evidence_position": 1.0 if hit else None,
        "provenance_coverage": float(provenance),
        "average_context_characters": float(context_characters),
        "average_context_tokens": float(context_characters // 5),
        "indexing_latency_ms": latency * 2,
        "total_indexing_latency_ms": latency * 100,
        "query_latency_p50_ms": latency,
        "query_latency_p95_ms": latency,
        "abstention_retrieval_empty_rate": 0.0,
    }
    scorecard = {
        "schema_version": 1,
        "benchmark": "LongMemEval V1",
        "subset": "deterministic-small",
        "counts": {
            "dataset_instances": 500,
            "selected_instances": 50,
            "positive_instances": 46,
            "abstention_instances": 4,
        },
        "metrics": metrics,
        "metric_definitions": metric_definitions,
        "run_configuration": retrieval_configuration,
        "limitations": ["synthetic fixture"],
    }
    for filename, payload in (
        ("manifest.json", manifest),
        ("selected_questions.json", selection),
        ("results.json", results),
        ("scorecard.json", scorecard),
    ):
        (root / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (root / "scorecard.md").write_text("# synthetic\n", encoding="utf-8")
    return root


def _record(directory: Path, *, record_id: str, repeat: Path = None):
    return record_from_artifacts(
        directory,
        record_id=record_id,
        issue=100,
        pull_request=0,
        decision="PENDING",
        parent_record_id="longmemeval-v1-dev-50/96-b09ceacc",
        repeat_directory=repeat,
    )


def test_baseline_json_schema_validation_and_closed_contract(baseline):
    assert baseline["schema_version"] == HISTORICAL_SCHEMA_VERSION
    assert SCHEMA_VERSION == "1.1.0"
    schema = json.loads((ROOT / "benchmarks/results/schema.json").read_text())
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["additionalProperties"] is False
    validate_record(baseline)
    with pytest.raises(ValueError, match="unsupported fields: surprise"):
        validate_record({**baseline, "surprise": True})


@pytest.mark.parametrize(
    "dotted,value,message",
    [
        ("record_id", None, "non-empty string"),
        ("dataset.sha256", "bad", "64-character SHA-256"),
        ("metrics.recall_at_10", 1.01, "range"),
        ("dataset.positive_count", 45, r"positive_count \+ abstention_count"),
        ("schema_version", "2.0.0", "unsupported version"),
        ("decision", "DEFER", "unsupported decision"),
    ],
)
def test_invalid_records_are_rejected(baseline, dotted, value, message):
    with pytest.raises(ValueError, match=message):
        validate_record(changed(baseline, dotted, value))


def test_missing_required_field_is_rejected(baseline):
    invalid = copy.deepcopy(baseline)
    invalid.pop("metrics")
    with pytest.raises(ValueError, match="missing required fields: metrics"):
        validate_record(invalid)


def test_baseline_markdown_generation_is_deterministic_and_consistent(baseline):
    first = render_record(baseline)
    second = render_record(copy.deepcopy(baseline))
    assert first == second == BASELINE_MD.read_text(encoding="utf-8")
    assert "does not measure final-answer correctness" in first


@pytest.mark.parametrize(
    "dotted,value",
    [
        ("dataset.sha256", "0" * 64),
        ("dataset.revision", "other"),
        ("selection.query_ids_sha256", "1" * 64),
        ("configuration.top_k", 9),
        ("configuration.granularity", "turn"),
        ("configuration.reader", "reader-x"),
        ("configuration.judge", "judge-x"),
        ("configuration.retrieval_configuration", {"different": True}),
        ("configuration.metric_definitions_sha256", "2" * 64),
        ("configuration.token_count_method", "model"),
        ("configuration.adapter_version", "2"),
    ],
)
def test_incompatible_comparisons_name_exact_field(baseline, dotted, value):
    with pytest.raises(ValueError, match=f"incompatible field {dotted}"):
        validate_compatibility(baseline, changed(baseline, dotted, value))


def test_compatible_aggregate_comparison_and_cross_commit_rule(baseline):
    candidate = changed(baseline, "measured_commit", "a" * 40)
    candidate = changed(candidate, "record_id", "candidate/a")
    comparison = compare_records(baseline, candidate)
    assert comparison["compatibility"]["compatible"] is True
    assert comparison["decision"] == "KEEP"
    assert comparison["determinism"]["same_commit_hash_rule"] is False
    assert comparison["determinism"]["retrieval_signature_match"] is True


def test_metric_directionality_zero_baseline_and_abstention_semantics():
    assert metric_delta("recall_at_10", 0.8, 0.9)["status"] == "improved"
    assert metric_delta("first_evidence_position", 2.0, 3.0)["status"] == "regressed"
    assert metric_delta("average_context_tokens", 100.0, 90.0)["status"] == "improved"
    assert metric_delta("recall_at_1", 0.0, 0.1)["relative_delta"] is None
    abstention = metric_delta("abstention_retrieval_empty_rate", 0.0, 1.0)
    assert abstention["status"] == abstention["semantic_direction"] == "informational"


def test_latency_is_informational_unless_environment_is_comparable(baseline):
    candidate = copy.deepcopy(baseline)
    for record in (baseline, candidate):
        record["latency"]["query_latency_p50_ms"] = 10.0
    candidate["latency"]["query_latency_p50_ms"] = 8.0
    comparison = compare_records(baseline, candidate)
    assert comparison["latency"]["metrics"]["query_latency_p50_ms"]["status"] == "informational"
    for record in (baseline, candidate):
        record["latency"]["comparable_environment"] = True
    comparison = compare_records(baseline, candidate)
    assert comparison["latency"]["metrics"]["query_latency_p50_ms"]["status"] == "improved"


def test_provenance_regression_is_decision_gating(baseline):
    candidate = changed(baseline, "metrics.provenance_coverage", 0.9)
    comparison = compare_records(baseline, candidate)
    assert comparison["provenance"]["regression"] is True
    assert comparison["decision"] == "ITERATE"


def test_comparison_json_and_markdown_are_deterministic(baseline):
    first = compare_records(baseline, copy.deepcopy(baseline))
    second = compare_records(copy.deepcopy(baseline), copy.deepcopy(baseline))
    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second, sort_keys=True, allow_nan=False
    )
    assert render_comparison(first) == render_comparison(second)


def test_candidate_artifact_ingestion_repeatability_and_query_deltas(tmp_path):
    first_dir = _write_artifacts(tmp_path / "first")
    second_dir = _write_artifacts(
        tmp_path / "second", created_at="2026-02-02T00:00:00+00:00", latency=99.0
    )
    first = _record(first_dir, record_id="synthetic/first", repeat=second_dir)
    assert first["determinism"]["equivalent"] is True
    assert first["determinism"]["run_count"] == 2
    assert normalized_artifact_sha256(first_dir) == normalized_artifact_sha256(second_dir)
    assert retrieval_result_sha256(first_dir) == retrieval_result_sha256(second_dir)
    second = _record(second_dir, record_id="synthetic/second", repeat=first_dir)
    equivalent = compare_records(
        first,
        second,
        baseline_artifacts=first_dir,
        candidate_artifacts=second_dir,
    )
    assert equivalent["query_level"]["no_semantic_change_count"] == 50

    historical_drift = changed(first, "metrics.average_context_characters", 101.0)
    historical_drift = changed(
        historical_drift,
        "determinism.retrieval_result_sha256",
        "0" * 64,
    )
    drift_comparison = compare_records(
        historical_drift,
        second,
        baseline_artifacts=first_dir,
        candidate_artifacts=second_dir,
    )
    assert drift_comparison["baseline_runtime_drift"] == {
        "available": True,
        "metrics_match_versioned_record": False,
        "retrieval_signature_match_versioned_record": False,
        "runtime_retrieval_result_sha256": retrieval_result_sha256(first_dir),
    }
    assert drift_comparison["decision"] == "KEEP"

    changed_dir = _write_artifacts(
        tmp_path / "changed",
        retrieved_session="session-b",
        provenance=False,
        context_characters=150,
    )
    query = compare_query_artifacts(first_dir, changed_dir)
    assert len(query["regressions"]) == 50
    assert "retrieval_regression" in query["changes"][0]["classifications"]
    assert "context_size_change" in query["changes"][0]["classifications"]
    assert "provenance_regression" in query["changes"][0]["classifications"]
    assert query["changes"][0]["first_evidence_rank_before"] == 1
    assert query["changes"][0]["first_evidence_rank_after"] is None


def test_same_commit_repeatability_hash_rule(baseline):
    candidate = copy.deepcopy(baseline)
    comparison = compare_records(baseline, candidate)
    assert comparison["determinism"]["same_commit_hash_rule"] is True
    assert comparison["determinism"]["normalized_sha_match"] is True
    candidate["determinism"]["normalized_sha256"] = "0" * 64
    comparison = compare_records(baseline, candidate)
    assert comparison["determinism"]["regression"] is True
    assert comparison["decision"] == "ITERATE"


def test_versioned_outputs_contain_no_restricted_benchmark_content(baseline):
    assert_no_restricted_content(baseline)
    for path in (BASELINE_JSON, BASELINE_MD):
        text = path.read_text(encoding="utf-8").lower()
        assert '"question":' not in text
        assert "expected_answer" not in text
        assert "ground_truth_session_ids" not in text
        assert "answer_session_ids" not in text
        assert "has_answer" not in text


@pytest.mark.parametrize(
    "level,rationale",
    [
        ("REQUIRED", ""),
        ("SMOKE_ONLY", "Transport-only contract change."),
        ("NOT_APPLICABLE", "Documentation only."),
    ],
)
def test_pr_applicability_parsing(level, rationale):
    issue = "Benchmark issue: #100\n" if level == "REQUIRED" else ""
    body = f"Benchmark applicability: {level}\n{issue}Benchmark rationale: {rationale}\n"
    parsed = parse_applicability(body)
    assert parsed["applicability"] == level
    assert parsed["benchmark_issue"] == (100 if level == "REQUIRED" else None)


@pytest.mark.parametrize(
    "body,message",
    [
        ("no declaration", "missing benchmark applicability"),
        (
            "Benchmark applicability: REQUIRED\nBenchmark applicability: SMOKE_ONLY\n",
            "multiple benchmark applicability",
        ),
        ("Benchmark applicability: SMOKE_ONLY\n", "rationale is required"),
        ("Benchmark applicability: NOT_APPLICABLE\n", "rationale is required"),
        ("Benchmark applicability: required\n", "missing benchmark applicability"),
        ("Benchmark applicability: REQUIRED\x00\n", "NUL byte"),
        ("Benchmark applicability: REQUIRED\n", "missing Benchmark issue"),
        (
            "Benchmark applicability: REQUIRED\nBenchmark issue: #100\n"
            "Benchmark issue: #101\n",
            "multiple Benchmark issue",
        ),
        (
            "Benchmark applicability: REQUIRED\nBenchmark issue: issue-100\n",
            "malformed Benchmark issue",
        ),
        (
            "Benchmark applicability: REQUIRED\nBenchmark issue: #abc\n",
            "malformed Benchmark issue",
        ),
        (
            "Benchmark applicability: REQUIRED\nBenchmark issue: #0\n",
            "malformed Benchmark issue",
        ),
    ],
)
def test_invalid_or_malformed_pr_applicability_is_rejected(body, message):
    with pytest.raises(ValueError, match=message):
        parse_applicability(body)


def test_ci_workflow_syntax_and_least_privilege():
    workflow_path = ROOT / ".github/workflows/benchmark.yml"
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    assert {"benchmark-reporting", "longmemeval-dev-50"} <= set(workflow["jobs"])
    text = workflow_path.read_text(encoding="utf-8")
    assert "secrets." not in text
    assert "prepare_dataset" in text
    assert DATASET_SHA256 in text
    assert "ref: ${{ env.CANDIDATE_SHA }}" in text
    assert "github.event.pull_request.base.sha" in text
    assert "parent-comparison.json" in text
    assert "canonical-comparison.json" in text
    assert 'python-version: "3.12.14"' in text
    assert 'pip install -c "$CONSTRAINTS_PATH"' in text
    assert "--issue 100" not in text


def test_artifact_path_validation_rejects_escape_and_symlink(tmp_path):
    allowed = tmp_path / "artifacts"
    allowed.mkdir()
    assert validate_output_path(allowed / "run", allowed) == (allowed / "run").resolve()
    with pytest.raises(ValueError, match="escapes allowed root"):
        validate_output_path(tmp_path / "outside", allowed)
    link = allowed / "link"
    link.symlink_to(tmp_path / "outside", target_is_directory=True)
    with pytest.raises(ValueError, match="must not be a symlink"):
        validate_output_path(link, allowed)


def test_dataset_checksum_mismatch_is_infrastructure_failure(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text("[]", encoding="utf-8")
    with pytest.raises(RuntimeError, match="infrastructure failure.*checksum mismatch"):
        verify_dataset(dataset)


def test_pr_template_requires_benchmark_declaration():
    template = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
    assert "Benchmark applicability: REQUIRED | SMOKE_ONLY | NOT_APPLICABLE" in template
    assert "Benchmark rationale:" in template
    assert "Benchmark issue: #" in template


def test_current_record_captures_complete_injectable_environment(tmp_path):
    directory = _write_artifacts(tmp_path / "artifacts")
    probe_values = {
        "python_implementation": "CPython",
        "python_version": "3.12.14",
        "python_full_version": "3.12.14 pinned",
        "os": "Linux",
        "platform": "Linux-test",
        "architecture": "x86_64",
        "numpy_version": "2.5.2",
        "scipy_version": "1.18.1",
        "scikit_learn_version": "1.9.0",
        "networkx_version": "3.6.1",
        "pyyaml_version": "6.0.3",
    }
    environment = collect_environment(
        ROOT / "benchmarks/longmemeval_v1/constraints-ci.txt",
        repository_dirty=False,
        repository_root=ROOT,
        probe=lambda: probe_values,
    )
    first = record_from_artifacts(
        directory,
        record_id="candidate/injected",
        issue=100,
        pull_request=102,
        decision="PENDING",
        parent_record_id="parent/one",
        parent_commit="a" * 40,
        execution_role="candidate",
        event_name="pull_request",
        event_identity="pull_request:123:1:commit",
        run_id="123",
        run_attempt=1,
        environment=environment,
    )
    second = record_from_artifacts(
        directory,
        record_id="candidate/injected",
        issue=100,
        pull_request=102,
        decision="PENDING",
        parent_record_id="parent/one",
        parent_commit="a" * 40,
        execution_role="candidate",
        event_name="pull_request",
        event_identity="pull_request:123:1:commit",
        run_id="123",
        run_attempt=1,
        environment=environment,
    )
    assert first == second
    assert first["schema_version"] == SCHEMA_VERSION
    assert first["issue"] == 100
    assert first["pull_request"] == 102
    assert first["parent_commit"] == "a" * 40
    assert first["environment"]["complete"] is True
    assert first["environment"]["fingerprint_sha256"] == environment_fingerprint(
        first["environment"]
    )
    validate_record(first)


def test_non_pr_identity_cannot_be_misattributed_to_an_issue(tmp_path):
    directory = _write_artifacts(tmp_path / "artifacts")
    record = _record(directory, record_id="local/record")
    record["execution"]["event_name"] = "schedule"
    record["execution"]["event_identity"] = "schedule:123:1:commit"
    with pytest.raises(ValueError, match="non-PR events must use issue=0"):
        validate_record(record)


def test_immediate_parent_gate_rejects_regression_hidden_by_canonical(baseline):
    canonical = changed(baseline, "metrics.recall_at_10", 0.80)
    parent = changed(canonical, "metrics.recall_at_10", 0.95)
    parent = changed(parent, "measured_commit", "a" * 40)
    parent = changed(parent, "record_id", "parent/a")
    candidate = changed(parent, "metrics.recall_at_10", 0.90)
    candidate = changed(candidate, "measured_commit", "b" * 40)
    candidate = changed(candidate, "record_id", "candidate/b")
    assert compare_records(canonical, candidate)["decision"] == "KEEP"
    assert compare_records(parent, candidate)["decision"] == "ITERATE"


def test_shared_runner_drift_cannot_hide_from_forward_reference(tmp_path):
    first_dir = _write_artifacts(tmp_path / "first")
    parent = _record(first_dir, record_id="parent/current")
    candidate = copy.deepcopy(parent)
    candidate["record_id"] = "candidate/current"
    forward = copy.deepcopy(parent)
    forward["record_id"] = "forward/pinned"

    parent["environment"]["fingerprint_sha256"] = "0" * 64
    candidate["environment"]["fingerprint_sha256"] = "0" * 64
    assert compare_records(parent, candidate)["decision"] == "KEEP"
    with pytest.raises(ValueError, match="forward benchmark environment drift"):
        validate_environment_reference(candidate, forward)
