import copy

import pytest

from benchmarks.information_needs.run import digest, run_experiment, score_review


@pytest.fixture(scope="module")
def mechanics():
    return run_experiment()


def captured(mechanics):
    return {
        "mode": "provider_capture", "fixture_sha256": mechanics["fixture_sha256"],
        "provider": {"name": "TEST DOUBLE", "model_revision": "test-only", "temperature": 0,
                     "max_output_tokens": 2048, "timeout_s": 60, "captured_at": "test-only",
                     "adapter_revision": "test-only"},
        "runs": {r["id"]: {"calls": [{**call, "usage": {"input_tokens": 1, "output_tokens": 1, "latency_ms": 0}}
                                      for call in r["calls"]]} for r in mechanics["runs"]},
    }


def test_frozen_mechanics_counts_and_no_quality_claim(mechanics):
    assert mechanics["mode"] == "mock_mechanics"
    assert mechanics["quality_metrics"] is None
    assert mechanics["quality_gate"].startswith("BLOCKED")
    metrics = mechanics["contract_metrics"]
    assert metrics["N0"]["provider_callable_calls"] == 18
    assert metrics["N1"]["provider_callable_calls"] == metrics["N2"]["provider_callable_calls"] == 14
    assert metrics["N1"]["need_counts"] == [1, 1, 1, 0, 0, 1]
    assert metrics["N2"]["need_counts"] == [1, 3, 3, 0, 0, 3]
    assert all(row["schema_errors"] == 0 for row in metrics.values())


def test_frozen_repeated_results(mechanics):
    assert run_experiment() == mechanics


def test_replay_validates_exact_prompts_and_corpus(mechanics):
    replay = captured(mechanics)
    report = run_experiment(replay=replay)
    assert report["contract_metrics"] == mechanics["contract_metrics"]
    assert report["quality_metrics"] is None
    replay["fixture_sha256"] = "wrong"
    with pytest.raises(ValueError, match="fixture"):
        run_experiment(replay=replay)
    replay = captured(mechanics)
    replay["runs"]["simple-fact/N1"]["calls"][0]["prompt_sha256"] = "wrong"
    with pytest.raises(ValueError):
        run_experiment(replay=replay)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, True])
def test_replay_rejects_invalid_usage(mechanics, bad):
    replay = captured(mechanics)
    replay["runs"]["simple-fact/N0"]["calls"][0]["usage"]["input_tokens"] = bad
    with pytest.raises(ValueError):
        run_experiment(replay=replay)


def test_no_review_of_mocks_or_unbound_reviews(mechanics):
    with pytest.raises(ValueError, match="Mock"):
        run_experiment(review={})
    with pytest.raises(ValueError, match="bind"):
        score_review(mechanics, {})
    review = {"fixture_sha256": mechanics["fixture_sha256"], "report_sha256": digest(mechanics["runs"]),
              "reviewer": "tester", "status": "independently_reviewed", "runs": {}}
    with pytest.raises(ValueError, match="every scenario"):
        score_review(mechanics, review)


def test_explicit_capture_receives_budgets_and_replays_exactly(mechanics):
    replay = captured(mechanics)
    calls = [call for run in mechanics["runs"] for call in replay["runs"][run["id"]]["calls"]]
    index = 0

    def adapter(system, user, *, max_output_tokens, timeout_s):
        nonlocal index
        assert max_output_tokens == 2048 and timeout_s == 60
        call = calls[index]
        index += 1
        assert digest({"system": system, "user": user}) == call["prompt_sha256"]
        return {"response": call["response"], "usage": call["usage"]}

    report = run_experiment(capture_fn=adapter, provider=replay["provider"])
    assert index == 46
    assert report["quality_metrics"] is None  # Capture alone proves no quality.
    replayed = run_experiment(replay=report["provider_capture"])
    assert replayed["runs"] == report["runs"]


def test_review_metrics_are_bound_and_null_is_not_zero(mechanics):
    from benchmarks.information_needs.run import score_review
    fields = {"need_coverage", "unsupported_need_rate", "duplicate_need_rate", "evidence_recall_at_3",
              "state_accuracy", "no_memory_needed_accuracy", "missed_critical_facets",
              "agent_authored_search_formulations", "duplicate_formulations_across_repeated_runs"}
    review = {"fixture_sha256": mechanics["fixture_sha256"], "report_sha256": digest(mechanics["runs"]),
              "reviewer": "TEST REVIEWER", "status": "independently_reviewed",
              "runs": {r["id"]: dict.fromkeys(fields, None) for r in mechanics["runs"]}}
    metrics = score_review(mechanics, review)
    assert metrics["N2"]["state_accuracy"] == {"mean": None, "applicable_runs": 0}
    review["runs"]["simple-fact/N1"]["need_coverage"] = 1.5
    with pytest.raises(ValueError, match="Invalid reviewed"):
        score_review(mechanics, review)
