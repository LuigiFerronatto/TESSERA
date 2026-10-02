"""Synthetic metric arithmetic and review-gate tests, never real human labels."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from benchmarks.typed_decomposition.evaluate import (
    CATEGORIES, CONTRACT_VERSION, SCHEMA_VERSION, ProviderResponse,
    adjudication_template, capture, compare, digest, main,
    repeated_agreement, replay, score, telemetry, validate_fixture,
)

FIXTURE = Path(__file__).resolve().parents[1] / "benchmarks/typed_decomposition/fixture.draft.json"


def draft():
    return json.loads(FIXTURE.read_text())


def attest(value):
    """Test-only attestation; production human review cannot be automated."""
    value["review"] = {"status": "human_reviewed", "reviewer": "synthetic-test-not-human",
                       "reviewed_at": "2026-10-02T00:00:00Z",
                       "content_sha256": digest({k: v for k, v in value.items() if k != "review"})}
    return value


def small_fixture():
    return attest({"schema_version": SCHEMA_VERSION, "contract_version": CONTRACT_VERSION,
                   "cases": [{"id": "case", "category": "facts_only",
                              "episode": {"beginning": "A fact.", "middle": "", "end": ""},
                              "expected_units": [{"id": "u1", "content": "A fact.",
                                                  "acceptable_types": ["factual"],
                                                  "rationale": "Test arithmetic only."}]}]})


CONFIG = {"provider": "synthetic-stub", "model": "no-real-model", "decoding": {"temperature": 0}}


def stub_capture(fixture=None, variant="D1", text='[{"type":"factual","content":"A fact."}]',
                 repeat_id="1", usage=None):
    fixture = fixture or small_fixture()
    return capture(fixture, variant=variant,
                   provider=lambda *_: ProviderResponse(text, **(usage or {})),
                   provider_config=CONFIG, repeat_id=repeat_id)


def judge(artifact, matches=None):
    value = adjudication_template(artifact)
    for row in value["rows"]:
        for prediction in row["predictions"]:
            prediction.update(matched_unit_id=(matches or {}).get(prediction["index"]),
                              unsupported=False, atomicity_violation=False,
                              rationale="Synthetic arithmetic test only.")
    return attest(value)


def test_draft_fixture_is_honest_covers_eight_categories_and_has_no_review():
    fixture = draft()
    validate_fixture(fixture)
    assert set(case["category"] for case in fixture["cases"]) == CATEGORIES
    assert fixture["review"]["status"] == "draft"
    assert fixture["review"]["reviewer"] is None
    assert fixture["review"]["content_sha256"] is None
    with pytest.raises(ValueError, match="human-reviewed"):
        validate_fixture(fixture, require_review=True)


@pytest.mark.parametrize("variant", ["D1", "D2"])
def test_draft_labels_block_before_any_provider_request(variant):
    provider = Mock(side_effect=AssertionError("must not call"))
    with pytest.raises(ValueError, match="human-reviewed"):
        capture(draft(), variant=variant, provider=provider, provider_config=CONFIG)
    provider.assert_not_called()


def test_draft_d0_capture_and_replay_are_offline_and_not_quality_results():
    fixture = draft()
    artifact = capture(fixture, variant="D0")
    assert artifact["quality_status"] == "not_scored"
    assert telemetry(artifact)["provider_requests"] == 0
    assert len(replay(fixture, json.loads(json.dumps(artifact)))) == 8
    with pytest.raises(ValueError, match="human-reviewed"):
        score(fixture, artifact, judge(artifact))


def test_changed_episode_label_or_guidance_invalidates_review():
    for field, value in (("content", "Changed fact."), ("rationale", "Changed guidance.")):
        fixture = small_fixture()
        fixture["cases"][0]["expected_units"][0][field] = value
        with pytest.raises(ValueError, match="digest mismatch"):
            capture(fixture, variant="D1", provider=Mock(), provider_config=CONFIG)
    fixture = small_fixture()
    fixture["cases"][0]["episode"]["beginning"] = "Changed episode."
    with pytest.raises(ValueError, match="digest mismatch"):
        validate_fixture(fixture, require_review=True)


@pytest.mark.parametrize("bad", ["not a date", "2026-01-01", "2026-01-01T12:00:00"])
def test_review_requires_timestamp_with_timezone(bad):
    fixture = small_fixture()
    fixture["review"]["reviewed_at"] = bad
    with pytest.raises(ValueError, match="timestamp"):
        validate_fixture(fixture, require_review=True)


def test_label_sentinel_never_reaches_either_candidate_prompt():
    fixture = small_fixture()
    fixture["cases"][0]["expected_units"][0]["content"] = "SECRET_LABEL_SENTINEL"
    attest(fixture)
    for variant in ("D1", "D2"):
        provider = Mock(return_value=ProviderResponse("[]"))
        artifact = capture(fixture, variant=variant, provider=provider, provider_config=CONFIG)
        assert len(artifact["rows"][0]["calls"]) == (1 if variant == "D1" else 3)
        for call in provider.call_args_list:
            assert "SECRET_LABEL_SENTINEL" not in " ".join(call.args)
            assert json.loads(call.args[1]) == fixture["cases"][0]["episode"]


@pytest.mark.parametrize("mutation", ["prompt", "response", "missing_call", "extra_call", "result", "case", "fixture"])
def test_replay_rejects_identity_and_capture_tampering(mutation):
    fixture = small_fixture()
    artifact = stub_capture(fixture)
    row = artifact["rows"][0]
    if mutation == "prompt": row["calls"][0]["system_sha256"] = "wrong"
    if mutation == "response": row["calls"][0]["response"] = "[]"
    if mutation == "missing_call": row["calls"] = []
    if mutation == "extra_call": row["calls"].append(deepcopy(row["calls"][0]))
    if mutation == "result": row["result"]["mode"] = "deterministic"
    if mutation == "case": row["case_id"] = "wrong"
    if mutation == "fixture": artifact["fixture_sha256"] = "wrong"
    with pytest.raises(ValueError):
        replay(fixture, artifact)


def test_provider_failure_is_captured_without_secrets_and_replayed_as_fallback():
    provider = Mock(side_effect=[ProviderResponse("[]"), TimeoutError("SECRET")])
    fixture = small_fixture()
    artifact = capture(fixture, variant="D2", provider=provider, provider_config=CONFIG)
    assert artifact["rows"][0]["result"]["mode"] == "deterministic_fallback"
    assert "SECRET" not in json.dumps(artifact)
    assert len(replay(fixture, artifact)) == 1
    usage = telemetry(artifact)
    assert usage["provider_requests"] == 2 and usage["fallback_episodes"] == 1
    assert usage["cost_usd"] is None and usage["input_tokens"] is None


def test_usage_is_supplied_not_estimated_from_text():
    unknown = telemetry(stub_capture())
    assert unknown["input_tokens"] is None and unknown["output_tokens"] is None
    assert unknown["cost_usd"] is None and unknown["cost_kind"] is None
    measured = telemetry(stub_capture(usage={"input_tokens": 23, "output_tokens": 9,
                                            "cost_usd": .003, "cost_kind": "actual"}))
    assert measured["input_tokens"] == 23 and measured["output_tokens"] == 9
    assert measured["cost_usd"] == .003 and measured["cost_kind"] == "actual"


@pytest.mark.parametrize("usage", [{"input_tokens": True}, {"output_tokens": -1},
    {"cost_usd": float("nan"), "cost_kind": "actual"}, {"cost_usd": 1}, {"cost_kind": "actual"}])
def test_invalid_telemetry_is_not_silently_scored(usage):
    with pytest.raises(ValueError):
        stub_capture(usage=usage)


def test_blank_judgments_cannot_be_scored():
    fixture = small_fixture()
    artifact = stub_capture(fixture)
    with pytest.raises(ValueError, match="human-reviewed"):
        score(fixture, artifact, adjudication_template(artifact))
    pending = attest(adjudication_template(artifact))
    with pytest.raises(ValueError):
        score(fixture, artifact, pending)


def test_scoring_exact_synthetic_arithmetic_and_missing_outputs():
    fixture = small_fixture()
    artifact = stub_capture(fixture)
    result = score(fixture, artifact, judge(artifact, {0: "u1"}))
    assert result["extraction_precision"] == result["extraction_recall"] == result["extraction_f1"] == 1
    assert result["acceptable_type_accuracy"] == result["unambiguous_type_macro_f1"] == 1
    assert result["unsupported_inference_rate"] == result["atomicity_violation_rate"] == 0
    assert result["zero_memory_accuracy"] is None
    empty = stub_capture(fixture, text="[]")
    result = score(fixture, empty, judge(empty))
    assert result["extraction_f1"] == 0 and result["extraction_recall"] == 0
    assert result["extraction_precision"] is None and result["memory_count_delta"] == -1


def test_wrong_type_does_not_hide_extraction_match():
    fixture = small_fixture()
    artifact = stub_capture(fixture, text='[{"type":"preference","content":"A fact."}]')
    result = score(fixture, artifact, judge(artifact, {0: "u1"}))
    assert result["extraction_f1"] == 1
    assert result["acceptable_type_accuracy"] == result["unambiguous_type_macro_f1"] == 0
    assert result["type_macro_classes"] == 2


def test_ambiguous_type_is_accepted_once_and_separated_from_confusion_matrix():
    fixture = small_fixture()
    fixture["cases"][0]["expected_units"][0]["acceptable_types"] = ["preference", "procedural_anchor"]
    attest(fixture)
    artifact = stub_capture(fixture, text='[{"type":"procedural_anchor","content":"A principle."}]')
    result = score(fixture, artifact, judge(artifact, {0: "u1"}))
    assert result["acceptable_type_accuracy"] == 1
    assert result["unambiguous_type_macro_f1"] is None and result["type_macro_classes"] == 0


def test_unsupported_compound_duplicate_outputs_cannot_earn_atomic_matches():
    fixture = small_fixture()
    artifact = stub_capture(fixture, text='[{"type":"factual","content":"A fact."},{"type":"factual","content":"Different wording."}]')
    for field in ("unsupported", "atomicity_violation", "duplicate_of"):
        judgments = judge(artifact, {1: "u1"})
        judgments["rows"][0]["predictions"][1][field] = 0 if field == "duplicate_of" else True
        attest(judgments)
        with pytest.raises(ValueError, match="cannot earn"):
            score(fixture, artifact, judgments)
    judgments = judge(artifact, {0: "u1", 1: "u1"})
    with pytest.raises(ValueError, match="one-to-one"):
        score(fixture, artifact, judgments)


def test_zero_memory_case_and_false_positive_denominators():
    fixture = small_fixture()
    fixture["cases"][0]["expected_units"] = []
    attest(fixture)
    empty = stub_capture(fixture, text="[]")
    good = score(fixture, empty, judge(empty))
    assert good["zero_memory_accuracy"] == 1 and good["extraction_f1"] is None
    artifact = stub_capture(fixture)
    judgments = judge(artifact)
    judgments["rows"][0]["predictions"][0]["unsupported"] = True
    attest(judgments)
    bad = score(fixture, artifact, judgments)
    assert bad["zero_memory_accuracy"] == 0 and bad["unsupported_inference_rate"] == 1
    assert bad["memory_count_delta"] == 1 and bad["extraction_f1"] == 0


def test_scores_bound_to_exact_capture_and_exact_judgments():
    fixture = small_fixture()
    artifact = stub_capture(fixture)
    judgments = judge(artifact, {0: "u1"})
    judgments["rows"][0]["predictions"][0]["unsupported"] = True
    with pytest.raises(ValueError, match="digest mismatch"):
        score(fixture, artifact, judgments)
    judgments = judge(artifact, {0: "u1"})
    artifact["repeat_id"] = "changed"
    with pytest.raises(ValueError, match="different capture"):
        score(fixture, artifact, judgments)


def test_repeated_agreement_is_exact_and_requires_distinct_compatible_runs():
    fixture = small_fixture()
    first, second = stub_capture(fixture), stub_capture(fixture, repeat_id="2")
    assert repeated_agreement(fixture, [first, second])["agreement"] == 1
    different = stub_capture(fixture, repeat_id="3", text="[]")
    assert repeated_agreement(fixture, [first, different])["agreement"] == 0
    with pytest.raises(ValueError, match="distinct"):
        repeated_agreement(fixture, [first, first])
    second["provider_config"] = dict(CONFIG, model="other")
    with pytest.raises(ValueError, match="configuration"):
        repeated_agreement(fixture, [first, second])


def test_compare_freezes_inputs_and_never_chooses_default():
    fixture = small_fixture()
    captures = {variant: capture(fixture, variant=variant,
                                provider=lambda *_: ProviderResponse("[]"), provider_config=CONFIG)
                for variant in ("D0", "D1", "D2")}
    judgments = {variant: judge(artifact) for variant, artifact in captures.items()}
    result = compare(fixture, captures, judgments)
    assert result["default_changed"] is False
    assert result["default_decision"] == "PENDING_HUMAN_DECISION"
    captures["D2"]["provider_config"] = dict(CONFIG, model="other")
    with pytest.raises(ValueError, match="identical"):
        compare(fixture, captures, judgments)


def test_cli_validate_d0_replay_and_blocked_score(tmp_path, capsys):
    assert main(["validate", "--fixture", str(FIXTURE)]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["review_status"] == "draft"
    target = tmp_path / "capture.json"
    assert main(["d0", "--fixture", str(FIXTURE), "--output", str(target)]) == 0
    assert main(["replay", "--fixture", str(FIXTURE), "--capture", str(target)]) == 0
    assert json.loads(capsys.readouterr().out)["provider_requests_this_replay"] == 0
    with pytest.raises(SystemExit):
        main(["score", "--fixture", str(FIXTURE), "--capture", str(target)])


def test_provider_cannot_mutate_original_fixture_and_relabel_the_capture():
    fixture = small_fixture()
    frozen = deepcopy(fixture)
    def provider(*_):
        fixture["cases"][0]["expected_units"] = []
        return ProviderResponse("[]")
    artifact = capture(fixture, variant="D1", provider=provider, provider_config=CONFIG)
    assert artifact["fixture_sha256"] == digest(frozen)
    assert len(replay(frozen, artifact)) == 1
    with pytest.raises(ValueError):
        replay(fixture, artifact)


@pytest.mark.parametrize("mutation", ["root", "row", "call", "negative_latency"])
def test_malformed_capture_is_rejected_with_actionable_error(mutation):
    fixture = small_fixture()
    artifact = stub_capture(fixture)
    if mutation == "root": artifact = []
    elif mutation == "row": artifact["rows"] = [None]
    elif mutation == "call": artifact["rows"][0]["calls"] = [None]
    else: artifact["rows"][0]["latency_ms"] = -1
    with pytest.raises(ValueError):
        replay(fixture, artifact)


@pytest.mark.parametrize("mutation", ["root", "row", "prediction"])
def test_malformed_adjudication_cannot_be_scored(mutation):
    fixture = small_fixture()
    artifact = stub_capture(fixture)
    judgments = judge(artifact)
    if mutation == "root": judgments = []
    else:
        if mutation == "row": judgments["rows"] = [None]
        else: judgments["rows"][0]["predictions"] = [None]
        attest(judgments)
    with pytest.raises(ValueError):
        score(fixture, artifact, judgments)
