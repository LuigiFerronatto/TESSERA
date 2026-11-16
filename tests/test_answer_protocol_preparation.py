"""All fixtures are invented; no dataset download, provider calls or human claims."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchmarks.answer_protocols.common import LABEL_KEYS, canonical, decode, digest, read
from benchmarks.answer_protocols.evaluation import score_persisted
from benchmarks.answer_protocols.judge import draft_packet, validate_draft_packet, validate_human_review
from benchmarks.answer_protocols.preregistration import (
    draft_preregistration, execute, readiness_errors, require_ready, selection_from_dataset,
    validate_preregistration, validate_selection,
)
from benchmarks.answer_protocols.reader import (
    attempt, capture_synthetic, draft_configuration, load_capture, make_request,
    persist_capture, run_scripted, validate_capture, validate_configuration,
    validate_output, validate_request,
)
from benchmarks.answer_protocols.synthetic import oracle_run, row

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmarks" / "answer_protocols"


def request(qid="synthetic-color_abs"):
    return make_request(row(qid), capture_sha256=digest("frozen-evidence"),
                        policy_sha256=digest("policy"), configuration=draft_configuration())


def answer():
    return {"answer": "blue", "abstained": False, "citations": []}


def capture():
    return capture_synthetic(request(), [attempt(1, canonical(answer()))])


def selection():
    return read(DATA / "full500-ids.json")


def reseal(value, field):
    value[field] = digest({k: v for k, v in value.items() if k != field})


def test_draft_selections_are_completely_null():
    config = read(DATA / "reader-configuration-draft.json")
    assert config == draft_configuration()
    validate_configuration(config)
    assert all(value is None for value in config["selection"].values())
    packet = read(DATA / "judge-calibration-draft.json")
    validate_draft_packet(packet)
    assert packet == draft_packet()
    assert len(packet["coverage_slots"]) == 8
    assert all(slot["human_labels"] is None for slot in packet["coverage_slots"])


def test_input_does_not_include_id_suffix_or_evaluator_fields():
    frozen = row("contains-hidden-label_abs")
    original = copy.deepcopy(frozen)
    result = make_request(frozen, capture_sha256=digest("evidence"), policy_sha256=digest("policy"),
                          configuration=draft_configuration())
    assert frozen == original
    assert result["payload"]["messages"] == frozen["messages"]
    assert result["input_sha256"] == frozen["input_sha256"]
    assert "contains-hidden-label" not in canonical(result)
    frozen["messages"][0]["content"] = "mutated"
    validate_request(result)  # The request is a frozen deep copy.


@pytest.mark.parametrize("label", sorted(LABEL_KEYS))
@pytest.mark.parametrize("boundary", ["row", "metrics", "message"])
def test_label_injection_rejected_at_each_transport_boundary(label, boundary):
    value = row()
    target = value if boundary == "row" else value["metrics"] if boundary == "metrics" else value["messages"][0]
    target[label.upper()] = "private evaluator value"
    with pytest.raises(ValueError):
        make_request(value, capture_sha256=digest("e"), policy_sha256=digest("p"),
                     configuration=draft_configuration())


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(unknown=True),
    lambda v: v["payload"].update(secret="invalid"),
    lambda v: v["payload"]["messages"][0].update(role="user"),
    lambda v: v["payload"]["messages"].append({"role": "user", "content": "extra"}),
    lambda v: v["payload"]["messages"][0].update(content="modified"),
    lambda v: v["payload"]["response_schema"].update(additionalProperties=True),
    lambda v: v.update(question_ref="x"),
    lambda v: v.update(renderer="auto"),
])
def test_requests_fail_closed(mutation):
    value = request()
    mutation(value)
    with pytest.raises(ValueError):
        validate_request(value)


@pytest.mark.parametrize("raw", ["not json", "[]", "null", '{"answer":"x","answer":"y"}',
                                  '{"answer":NaN,"abstained":false,"citations":[]}',
                                  '{"answer":"x","abstained":1,"citations":[]}',
                                  '{"answer":"x","abstained":true,"citations":[]}',
                                  '{"answer":"","abstained":false,"citations":[]}',
                                  '{"answer":"x","abstained":false,"citations":["x","x"]}'])
def test_malformed_attempts_are_preserved(raw):
    result = attempt(1, raw)
    assert result["status"] == "parse_failure"
    assert result["raw_response"] == raw
    assert result["output"] is None
    assert result["raw_response_sha256"]


def test_retry_preserves_failed_attempt_and_raw_hashes(tmp_path):
    script = [{"raw_response": None, "provider_error": "synthetic_timeout"},
              {"raw_response": "broken", "provider_error": None},
              {"raw_response": canonical(answer()), "provider_error": None}]
    path = tmp_path / "run"
    value = run_scripted(request(), script, path)
    assert [x["status"] for x in value["attempts"]] == ["provider_failure", "parse_failure", "ok"]
    assert len(list(path.glob("attempt-*.json"))) == 3
    assert load_capture(path) == value
    with pytest.raises(FileExistsError):
        run_scripted(request(), script, path)
    assert load_capture(path) == value


def test_request_is_on_disk_before_mock_parsing(tmp_path, monkeypatch):
    import benchmarks.answer_protocols.reader as reader
    original = reader.attempt
    path = tmp_path / "ordered"
    def checked(*args, **kwargs):
        assert read(path / "request.json") == request()
        assert not (path / "complete.json").exists()
        return original(*args, **kwargs)
    # Validation also replays parsing after completion; intercept only the first
    # attempt to assert write-before-inference, then restore the implementation.
    def once(*args, **kwargs):
        result = checked(*args, **kwargs)
        monkeypatch.setattr(reader, "attempt", original)
        return result
    monkeypatch.setattr(reader, "attempt", once)
    run_scripted(request(), [{"raw_response": canonical(answer()), "provider_error": None}], path)


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(execution_mode="REAL"),
    lambda v: v["attempts"][0].update(attempt=True),
    lambda v: v["attempts"][0].update(attempt=2),
    lambda v: v["attempts"][0].update(raw_response="modified"),
    lambda v: v["attempts"][0].update(provider_error="silently failed"),
    lambda v: v["attempts"][0]["usage"].update(cost_usd=float("inf")),
    lambda v: v["attempts"].append(attempt(2, canonical(answer()))),
    lambda v: v["attempts"][0].update(extra=True),
])
def test_capture_tampering_is_rejected(mutation):
    value = capture()
    mutation(value)
    with pytest.raises(ValueError):
        validate_capture(value)


@pytest.mark.parametrize("file", ["request.json", "attempt-001.json", "capture.json", "complete.json"])
def test_tampered_persistence_cannot_be_evaluated(tmp_path, file):
    path = tmp_path / "capture"
    persist_capture(path, capture())
    (path / file).write_text("{}")
    with pytest.raises(ValueError):
        score_persisted(path, {"question_id": "synthetic-color_abs", "answer": "blue", "should_abstain": False})


def test_incomplete_or_extra_attempt_not_scored(tmp_path):
    path = tmp_path / "capture"
    persist_capture(path, capture())
    (path / "attempt-002.json").write_text("{}")
    with pytest.raises(ValueError, match="untracked"):
        load_capture(path)
    (path / "complete.json").unlink()
    with pytest.raises(OSError):
        score_persisted(path, {})


def test_deterministic_metrics_join_only_matching_persisted_output(tmp_path):
    path = tmp_path / "capture"
    persist_capture(path, capture())
    value = score_persisted(path, {"question_id": "synthetic-color_abs", "answer": "Blue!", "should_abstain": False})
    assert value["exact_match"] == value["normalized_f1"] == 1
    assert value["judge_metrics"] is None
    with pytest.raises(ValueError, match="different"):
        score_persisted(path, {"question_id": "other", "answer": "Blue!", "should_abstain": False})


@pytest.mark.parametrize("status", ["provider", "parse"])
def test_failure_not_scored_as_incorrect(tmp_path, status):
    path = tmp_path / status
    row_ = attempt(1, None, provider_error="synthetic_timeout") if status == "provider" else attempt(1, "bad")
    persist_capture(path, capture_synthetic(request(), [row_]))
    result = score_persisted(path, {"question_id": "synthetic-color_abs", "answer": "blue", "should_abstain": False})
    assert result["exact_match"] is result["normalized_f1"] is result["abstention_correct"] is None


def test_two_synthetic_runs_match_without_model_determinism_claim(tmp_path):
    one, two = oracle_run(tmp_path / "one"), oracle_run(tmp_path / "two")
    assert one == two
    assert one["cases"] == 4 and one["successful_captures"] == 3
    assert one["provider_calls"] == one["cost_usd"] == 0
    assert one["quality_acceptance"] is None


def human_review(disagree=False):
    rows = [{"reviewer": "synthetic-reviewer-one", "label": "correct", "rationale": "Invented test only.",
             "evidence_sha256": digest("synthetic-review-one")},
            {"reviewer": "synthetic-reviewer-two", "label": "incorrect" if disagree else "correct",
             "rationale": "Invented test only.", "evidence_sha256": digest("synthetic-review-two")}]
    return {"case_ref": digest("synthetic-case"), "reader_author": "synthetic-author", "reviews": rows,
            "adjudication": None, "reference_label": "correct"}


def test_independent_human_review_mechanics_do_not_invent_labels():
    validate_human_review(human_review())
    value = human_review(True)
    with pytest.raises(ValueError):
        validate_human_review(value)
    value["adjudication"] = {"reviewer": "synthetic-third-reviewer", "label": "correct",
                              "rationale": "Synthetic test, no real review.", "evidence_sha256": digest("test")}
    validate_human_review(value)
    assert value["reviews"][1]["label"] == "incorrect"  # Disagreement retained.
    value["adjudication"]["reviewer"] = "synthetic-reviewer-one"
    with pytest.raises(ValueError, match="independent"):
        validate_human_review(value)


@pytest.mark.parametrize("change", ["author", "duplicate", "missing_rationale", "reference"])
def test_invalid_human_review_rejected(change):
    value = human_review()
    if change == "author":
        value["reviews"][0]["reviewer"] = value["reader_author"]
    elif change == "duplicate":
        value["reviews"][1]["reviewer"] = value["reviews"][0]["reviewer"]
    elif change == "missing_rationale":
        value["reviews"][0]["rationale"] = ""
    else:
        value["reference_label"] = "incorrect"
    with pytest.raises(ValueError):
        validate_human_review(value)


def test_committed_id_manifest_has_no_dataset_text_or_labels():
    value = selection()
    validate_selection(value)
    assert len(value["question_ids"]) == 500
    assert not ({"question", "answer", "haystack_sessions", "has_answer", "question_type"} & set(value))
    assert value["dataset_revision"].startswith("content-sha256:")


@pytest.mark.parametrize("mutation", [
    lambda v: v["question_ids"].reverse(),
    lambda v: v["question_ids"].pop(),
    lambda v: v["question_ids"].__setitem__(0, v["question_ids"][1]),
    lambda v: v.update(question_count=True),
    lambda v: v.update(dataset_sha256=digest("different")),
    lambda v: v.update(answer="not allowed"),
])
def test_bad_selection_rejected(mutation):
    value = selection()
    mutation(value)
    with pytest.raises(ValueError):
        validate_selection(value)


def test_recomputed_hash_cannot_hide_changed_official_membership():
    value = selection()
    value["question_ids"][0] = "invented-substitute"
    value["question_ids_sha256"] = digest(value["question_ids"])
    with pytest.raises(ValueError):
        validate_selection(value)


def test_dataset_checksum_checked_before_parsing(tmp_path):
    bad = tmp_path / "dataset.json"
    bad.write_text("not official dataset")
    with pytest.raises(ValueError, match="checksum"):
        selection_from_dataset(bad)


def test_draft_preregistration_valid_but_execution_blocked():
    selected = selection()
    prereg = read(DATA / "full500-preregistration.json")
    assert prereg == draft_preregistration(selected)
    validate_preregistration(prereg, selected)
    errors = readiness_errors(prereg, selected)
    assert len(errors) > 40
    assert any("calibration_review" in item for item in errors)
    assert any("cost_ceiling" in item for item in errors)
    with pytest.raises(ValueError, match="execution blocked"):
        execute(prereg, selected)


@pytest.mark.parametrize("mutation", [
    lambda v: v.update(profile="dev-50"),
    lambda v: v.update(selection_sha256=digest("wrong")),
    lambda v: v["reader"].update(model_revision="latest"),
    lambda v: v["judge"].update(extra="implicit"),
    lambda v: v["budget"].update(cost_ceiling=float("nan")),
    lambda v: v["budget"].update(cost_ceiling=-1),
    lambda v: v["budget"].update(maximum_run_attempts=True),
    lambda v: v["budget"].update(maximum_run_attempts=0),
    lambda v: v["budget"].update(currency="unknown"),
    lambda v: v["dependencies"].pop(),
    lambda v: v["dependencies"][0].update(decision="ITERATE"),
    lambda v: v["dependencies"][0].update(canonical_commit="pending"),
    lambda v: v["review"].update(evidence_url="not a URL"),
])
def test_strict_preregistration_mutations(mutation):
    value = draft_preregistration(selection())
    mutation(value)
    with pytest.raises(ValueError):
        validate_preregistration(value, selection())


def test_review_status_alone_cannot_unlock_missing_gates():
    value = draft_preregistration(selection())
    value["status"] = "REVIEWED"
    with pytest.raises(ValueError):
        require_ready(value, selection())


def test_cli_real_execution_exits_before_any_run(tmp_path):
    completed = subprocess.run([sys.executable, "-m", "benchmarks.answer_protocols.cli", "execute",
                                "--selection", str(DATA / "full500-ids.json"),
                                "--preregistration", str(DATA / "full500-preregistration.json")],
                               cwd=ROOT, text=True, capture_output=True)
    assert completed.returncode == 2
    assert "execution blocked" in completed.stderr
    assert not list(tmp_path.iterdir())


def test_no_runtime_or_provider_coupling():
    for path in (ROOT / "tessera").rglob("*.py"):
        assert "answer_protocols" not in path.read_text(encoding="utf-8")
    for path in DATA.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "import requests" not in text
        assert "import openai" not in text
        assert "import anthropic" not in text
        assert "os.environ" not in text
        assert "urllib" not in text
    assert "answer_protocols" not in (ROOT / "pyproject.toml").read_text()
    assert not any("answer_protocols" in p.read_text() for p in (ROOT / ".github/workflows").glob("*.yml"))


def test_json_reader_rejects_duplicate_keys_and_nonfinite_numbers():
    for invalid in ('{"a":1,"a":2}', '{"n":NaN}', '{"n":Infinity}'):
        with pytest.raises(ValueError):
            decode(invalid)


def test_json_schema_boolean_cannot_be_replaced_by_equal_integer():
    value = request()
    value["payload"]["response_schema"]["additionalProperties"] = 0
    reseal(value, "request_sha256")
    with pytest.raises(ValueError, match="response schema"):
        validate_request(value)


def test_persisted_copy_type_change_is_not_hidden_by_python_equality(tmp_path):
    path = tmp_path / "capture"
    persist_capture(path, capture())
    altered = read(path / "attempt-001.json")
    altered["usage"]["cost_usd"] = False
    (path / "attempt-001.json").write_text(canonical(altered))
    with pytest.raises(ValueError, match="persisted attempt"):
        load_capture(path)


def test_no_execution_even_with_structurally_filled_synthetic_approval():
    # Mechanical fixture only, not actual approval evidence or selected models.
    value = draft_preregistration(selection())
    value["status"] = "REVIEWED"
    def fill(mapping):
        for key, item in mapping.items():
            if isinstance(item, dict):
                fill(item)
            elif isinstance(item, list):
                for child in item:
                    fill(child)
            elif item is None:
                if key.endswith("sha256"):
                    mapping[key] = digest("synthetic-only")
                elif key.endswith("commit"):
                    mapping[key] = "a" * 40
                elif key == "evidence_url":
                    mapping[key] = "https://example.invalid/synthetic-only"
                elif key == "decision":
                    mapping[key] = "KEEP"
                elif key == "cost_ceiling":
                    mapping[key] = 1
                elif key == "maximum_run_attempts":
                    mapping[key] = 1
                else:
                    mapping[key] = "synthetic-only"
    fill(value)
    require_ready(value, selection())
    with pytest.raises(RuntimeError, match="deliberately unavailable"):
        execute(value, selection())
