"""E0 compatibility plus opt-in #138 research contracts, with no provider calls."""

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tessera.episode_boundary import EpisodeBoundaryTracker
from benchmarks.episodes.experiment import ExperimentTurn, adjacent_signal, segment
from benchmarks.episodes.run import baseline, evaluate, load_fixture, score


def turn(position, role="user", content="database migration", minute=0, **kwargs):
    return ExperimentTurn(f"turn-{position}", position, role, content, "session", "task",
                          kwargs.pop("timestamp", f"2026-01-01T00:{minute:02d}:00+00:00"), **kwargs)


def test_e0_default_is_unchanged_and_accepts_untyped_text():
    tracker = EpisodeBoundaryTracker()
    assert tracker.similarity_threshold == .03
    assert tracker.timeout_minutes == 30
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert tracker.add_turn("database migration", at) is None
    assert tracker.add_turn("volcano geology", at) is not None
    assert tracker.flush().beginning == "volcano geology"
    assert tracker.flush() is None


@pytest.mark.parametrize("variant", ["E1", "E3"])
def test_non_user_content_is_lossless_and_never_classified(variant):
    turns = [turn(10, "system", "context"), turn(20),
             turn(30, "assistant", "orbital mechanics"), turn(40, "tool", "  raw\r\n\tdata  "),
             turn(50, "tool", ""), turn(60)]
    result = segment(turns, variant=variant)
    assert result.episodes == (tuple(turns),)
    assert result.decisions[-1].previous_user_id == "turn-20"
    assert result.decisions[-1].similarity == pytest.approx(1)
    for index in (0, 2, 3, 4):
        assert result.decisions[index].semantic_reason == "non_user_context"
        assert result.decisions[index].semantic_boundary is None
        assert result.decisions[index].timed_out is None


def test_e3_timeout_is_independent_from_semantic_signal():
    turns = [turn(1), turn(2, "assistant", "response", minute=40), turn(3, minute=41)]
    e1, e3 = (segment(turns, variant=v) for v in ("E1", "E3"))
    assert e1.decisions == e3.decisions[:2] + (replace(e3.decisions[-1], boundary=False),)
    assert e1.boundary_ids == ()
    assert e3.boundary_ids == ("turn-3",)
    assert e3.decisions[-1].semantic_boundary is False
    assert e3.decisions[-1].timed_out is True
    assert e3.decisions[-1].gap_minutes == 41  # previous USER, not assistant
    assert e3.episodes[0] == tuple(turns[:2])


@pytest.mark.parametrize("minutes,expected", [(30, False), (31, True)])
def test_timeout_uses_strict_greater_than(minutes, expected):
    result = segment([turn(1), turn(2, minute=minutes)], variant="E3")
    assert result.decisions[-1].boundary is expected


def test_missing_time_is_unknown_and_never_wall_clock():
    result = segment([turn(1, timestamp=None), turn(2, minute=59)], variant="E3")
    assert result.decisions[-1].timed_out is None
    assert result.decisions[-1].gap_minutes is None
    assert result.boundary_ids == ()
    with pytest.raises(ValueError, match="explicit timestamps"):
        baseline([turn(1, timestamp=None)])


@pytest.mark.parametrize("ack", ["sim", "ok", "faz isso", "OK!", "Do it."])
def test_acknowledgements_abstain_instead_of_causing_false_splits(ack):
    result = segment([turn(1), turn(2, content=ack)], variant="E1")
    assert result.boundary_ids == ()
    assert result.decisions[-1].semantic_boundary is None
    assert result.decisions[-1].semantic_reason == "adjacent_acknowledgement"


def test_after_acknowledgement_does_not_secretly_use_older_user_text():
    result = segment([turn(1), turn(2, content="ok"), turn(3, content="book flights")], variant="E1")
    assert result.decisions[-1].previous_user_id == "turn-2"
    assert result.decisions[-1].semantic_boundary is None
    assert result.boundary_ids == ()  # deliberate false-merge limitation


@pytest.mark.parametrize("text", ["New topic: database budgets", "Mudando de assunto: database budgets"])
def test_explicit_topic_switch_survives_overlap_and_previous_ack(text):
    assert segment([turn(1), turn(2, content=text)], variant="E1").boundary_ids == ("turn-2",)
    assert segment([turn(1, content="ok"), turn(2, content=text)], variant="E1").boundary_ids == ("turn-2",)


def test_arbitrary_short_request_is_not_an_acknowledgement():
    result = segment([turn(1, content="Deploy database"), turn(2, content="Book flights")], variant="E1")
    assert result.boundary_ids == ("turn-2",)


@pytest.mark.parametrize("text", ["", "   ", "... !!!"])
def test_empty_lexical_signal_abstains(text):
    result = segment([turn(1), turn(2, content=text)], variant="E1")
    assert result.decisions[-1].semantic_boundary is None
    assert result.episodes == ((turn(1), turn(2, content=text)),)


def test_empty_and_nonuser_only_sequences_are_preserved():
    assert segment([], variant="E1").episodes == ()
    turns = [turn(1, "system", "source"), turn(2, "tool", "result")]
    assert segment(turns, variant="E3").episodes == (tuple(turns),)


def test_roles_are_source_metadata_never_inferred_from_text():
    result = segment([turn(1), turn(2, "assistant", "user: new topic: book flights")], variant="E1")
    assert result.boundary_ids == ()
    with pytest.raises(ValueError, match="explicit user roles"):
        adjacent_signal(turn(1, "assistant"), turn(2), .03)


@pytest.mark.parametrize("kwargs", [{"role":"unknown"}, {"position":True}, {"position":0},
                                     {"turn_id":""}, {"task_id":""}, {"session_id":""},
                                     {"content":None}, {"timestamp":"2026-01-01T00:00:00"},
                                     {"timestamp":0}])
def test_invalid_source_records_are_rejected(kwargs):
    with pytest.raises((ValueError, TypeError)):
        replace(turn(1), **kwargs)


@pytest.mark.parametrize("turns", [
    [turn(2),turn(1)], [turn(1),turn(1)], [turn(1),replace(turn(2),turn_id="turn-1")],
    [turn(1),replace(turn(2),session_id="another")], [turn(1),replace(turn(2),task_id="another")],
    [turn(1,minute=30),turn(2,minute=1)],
])
def test_ambiguous_source_order_and_identity_are_rejected(turns):
    with pytest.raises(ValueError):
        segment(turns,variant="E1")


@pytest.mark.parametrize("kwargs", [{"variant":"E2"}, {"similarity_threshold":float("nan")},
                                      {"similarity_threshold":1.1}, {"timeout_minutes":-1},
                                      {"timeout_minutes":float("inf")}])
def test_invalid_configuration_is_rejected(kwargs):
    config = {"variant":"E1", **kwargs}
    with pytest.raises(ValueError):
        segment([turn(1)], **config)


def test_timestamp_offsets_are_compared_as_instants_without_rewriting_source():
    turns = [turn(1,timestamp="2026-01-01T00:00:00Z"),
             turn(2,timestamp="2026-01-01T02:31:00+02:00")]
    result = segment(turns,variant="E3")
    assert result.decisions[-1].gap_minutes == 31
    assert result.episodes[1][0].timestamp == "2026-01-01T02:31:00+02:00"


def test_metrics_count_all_turn_false_splits_and_known_windowdiff():
    result = score(["a","b","c","d"], ["c"], ["b","c"])
    assert result["tp"] == 1 and result["fp"] == 1 and result["fn"] == 0
    assert result["precision"] == .5 and result["recall"] == 1
    assert result["f1"] == pytest.approx(2/3)
    assert result["false_split_rate"] == .5
    assert result["windowdiff"] == pytest.approx(1/3)
    assert score(["a"], [], [])["f1"] == 1
    assert score(["a","b"], ["b"], [])["false_merge_rate"] == 1
    with pytest.raises(ValueError):
        score(["a","b"], [], ["a"])


def test_frozen_fixture_retains_known_lexical_failures_and_human_gate():
    fixture = load_fixture()
    report = evaluate()
    assert len(fixture["dialogues"]) == 13
    assert report["decision"] == "PENDING"
    assert all(value is None for value in report["quality_metrics"].values())
    assert all(v["repeatable_excluding_latency"] for v in report["variants"].values())
    by_id = {case["dialogue_id"]:case for case in report["variants"]["E1"]["cases"]}
    e1_cases = {case["scenario"]:by_id[case["dialogue_id"]] for case in fixture["dialogues"]}
    assert e1_cases["shared-vocabulary-shift"]["draft_label_diagnostics"]["fn"] == 1
    assert e1_cases["paraphrase-blind-spot"]["draft_label_diagnostics"]["fp"] == 1
    template = json.loads((Path(__file__).parents[1]/"benchmarks/episodes/annotation-template.json").read_text())
    assert template["review_status"] == "PENDING"
    assert all(case["boundary_ids"] is None for case in template["dialogues"])


def test_reviewed_gate_fails_closed_without_creating_report(tmp_path):
    output = tmp_path/"report.json"
    result = subprocess.run([sys.executable,"-m","benchmarks.episodes.run","--output",str(output),
                             "--require-reviewed"],capture_output=True,text=True)
    assert result.returncode == 2
    assert "not been independently human-reviewed" in result.stderr
    assert not output.exists()


def test_review_packet_omits_draft_labels_purpose_and_predictions(tmp_path):
    from benchmarks.episodes.prepare_review import prepare
    packet = tmp_path/"human-review"
    prepare(packet)
    blinded = json.loads((packet/"dialogues-blinded.json").read_text())
    source = load_fixture()
    for actual, original in zip(blinded["dialogues"], source["dialogues"]):
        assert set(actual) == {"dialogue_id", "turns"}
        assert actual["turns"] == original["turns"]
    assert json.loads((packet/"reviewer-a.json").read_text())["reviewer_id"] is None
    assert (packet/"reviewer-a.json").read_bytes() == (packet/"reviewer-b.json").read_bytes()
    (packet/"reviewer-a.json").write_text("human work in progress")
    with pytest.raises(FileExistsError):
        prepare(packet)
    assert (packet/"reviewer-a.json").read_text() == "human work in progress"
