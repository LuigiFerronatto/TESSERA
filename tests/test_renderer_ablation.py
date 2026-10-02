import copy
import json
import socket
from pathlib import Path

import pytest

from benchmarks.rendering.cli import _read, main
from benchmarks.rendering.fixture import synthetic_capture
from benchmarks.rendering.frozen import (
    FORBIDDEN_KEYS, canonical_json, capture_evidence, digest, validate_capture,
)
from benchmarks.rendering.replay import (
    RENDERERS, SYSTEM_PROMPT, compact_summary, neutral_reference, replay, token_count,
)


def reseal(capture):
    capture["capture_sha256"] = digest({key: value for key, value in capture.items()
                                        if key != "capture_sha256"})
    return capture


def capture_again(queries, configuration=None):
    return capture_evidence(queries, tessera_commit="a" * 40,
                            retrieval_contract_commit="b" * 40,
                            retrieval_configuration=configuration or {"top_k": 10})


def test_capture_is_deep_copied_ordered_and_preserves_scores():
    queries = synthetic_capture()["queries"]
    queries.reverse()
    queries[-1]["hits"].reverse()
    queries[-1]["hits"][0]["score"] = -0.125
    captured = capture_again(queries)
    assert captured["queries"] == queries
    before = canonical_json(captured)
    queries[-1]["hits"][0]["provenance"]["source"]["path"] = "changed.md"
    assert canonical_json(captured) == before
    validate_capture(captured)


@pytest.mark.parametrize("label", sorted(FORBIDDEN_KEYS))
def test_capture_rejects_evaluator_labels_even_in_discarded_frontmatter(label):
    queries = synthetic_capture()["queries"]
    queries[0]["hits"][0]["frontmatter"] = {"nested": [{label.upper(): "DO NOT LEAK"}]}
    with pytest.raises(ValueError, match="evaluator labels"):
        capture_again(queries)


def test_capture_rejects_labels_in_configuration():
    with pytest.raises(ValueError, match="evaluator labels"):
        capture_again(synthetic_capture()["queries"], {"expected_answer": "secret"})


def test_capture_requires_configuration_object():
    with pytest.raises(ValueError, match="configuration must be an object"):
        capture_again(synthetic_capture()["queries"], ["top_k", 10])


@pytest.mark.parametrize("field,value", [
    ("id", "changed-id"), ("score", 0.333), ("body", "changed body"),
    ("relevant_evidence", None), ("related_ids", ["changed-related"]),
])
def test_any_frozen_retrieval_change_requires_new_capture(field, value):
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0][field] = value
    with pytest.raises(ValueError):
        replay(capture, input_token_budget=512)


def test_query_text_ids_order_and_evidence_identity_are_frozen():
    original = synthetic_capture()
    for change in (
        lambda c: c["queries"].reverse(),
        lambda c: c["queries"][0]["hits"].reverse(),
        lambda c: c["queries"][0].update(query="Different question?"),
        lambda c: c["queries"][0].update(query_id="Different ID"),
        lambda c: c["queries"][0]["hits"][0]["evidence"].update(evidence_id="changed"),
    ):
        candidate = copy.deepcopy(original)
        change(candidate)
        with pytest.raises(ValueError, match="checksum mismatch"):
            replay(candidate, input_token_budget=512)


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), "0.5", None])
def test_invalid_scores_rejected(bad):
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["score"] = bad
    with pytest.raises(ValueError, match="finite|numeric|JSON compliant"):
        capture_again(capture["queries"])


def test_extra_capture_fields_cannot_bypass_closed_schema():
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["temporal_status"] = "current"
    with pytest.raises(ValueError, match="expected exactly"):
        replay(reseal(capture), input_token_budget=512)


def test_future_statuses_and_frontmatter_are_not_projected_or_invented():
    queries = synthetic_capture()["queries"]
    queries[0]["hits"][0].update(
        temporal_status="FUTURE-CURRENT", evidence_status="FUTURE-SUFFICIENT",
        arbitration={"winner": "FUTURE-WINNER"}, frontmatter={"question_type": "HIDDEN-CATEGORY"},
        filepath="/private/file.md", score_explain={"recency_boost": 1.0},
    )
    captured = capture_again(queries)
    rendered = canonical_json(replay(captured, input_token_budget=10000))
    assert not any(value in rendered for value in (
        "FUTURE-CURRENT", "FUTURE-SUFFICIENT", "FUTURE-WINNER", "HIDDEN-CATEGORY", "/private/file.md",
    ))
    assert "temporal_status" not in rendered
    assert "evidence_status" not in rendered


def test_unknown_nested_evidence_fields_rejected():
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["evidence"]["source"]["authority"] = "high"
    with pytest.raises(ValueError, match="expected exactly"):
        replay(reseal(capture), input_token_budget=512)


@pytest.mark.parametrize("start,end", [(None, 1), (3, 2), (0, 2), (True, 2), ("1", 2)])
def test_invalid_source_spans_rejected(start, end):
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["evidence"]["span"] = {"start_line": start, "end_line": end}
    with pytest.raises(ValueError, match="positive lines"):
        replay(reseal(capture), input_token_budget=512)


def test_ambiguous_null_source_span_is_preserved_not_guessed():
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["evidence"]["span"] = {"start_line": None, "end_line": None}
    result = replay(reseal(capture), input_token_budget=10000)
    r2 = result["inputs"][2]
    assert "Start line: None\nEnd line: None" in r2["messages"][1]["content"]
    assert r2["metrics"]["available_exact_span_provenance_records"] == 3
    assert r2["metrics"]["retained_exact_span_provenance_records"] == 3


def test_capture_rejects_duplicate_query_memory_and_related_ids():
    for change, error in (
        (lambda c: c["queries"].append(c["queries"][0]), "duplicate query"),
        (lambda c: c["queries"][0]["hits"].append(c["queries"][0]["hits"][0]), "duplicate memory"),
        (lambda c: c["queries"][0]["hits"][0].update(related_ids=["x", "x"]), "duplicate related"),
    ):
        capture = synthetic_capture()
        change(capture)
        with pytest.raises(ValueError, match=error):
            replay(reseal(capture), input_token_budget=512)


def test_capture_requires_selected_span_to_belong_to_its_own_body():
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["relevant_evidence"] = "invented evidence"
    with pytest.raises(ValueError, match="occur verbatim"):
        replay(reseal(capture), input_token_budget=512)


@pytest.mark.parametrize("budget", [1, 40, 0, -1, True, 2.5])
def test_small_or_invalid_budget_fails_instead_of_truncating_query(budget):
    with pytest.raises(ValueError, match="budget"):
        replay(synthetic_capture(), input_token_budget=budget)


@pytest.mark.parametrize("budget", [80, 140, 180, 512, 10000])
def test_same_budget_policy_query_retrieval_and_determinism_across_renderers(budget):
    capture = synthetic_capture()
    before = canonical_json(capture)
    first = replay(capture, input_token_budget=budget)
    assert first == replay(capture, input_token_budget=budget)
    assert canonical_json(capture) == before
    assert first["manifest"]["capture_sha256"] == capture["capture_sha256"]
    assert first["manifest"]["execution"]["provider_calls"] == 0
    assert len(first["inputs"]) == 9
    for offset, query in enumerate(capture["queries"]):
        rows = first["inputs"][offset * 3:(offset + 1) * 3]
        assert [row["renderer"] for row in rows] == list(RENDERERS)
        assert len({row["metrics"]["fixed_input_tokens"] for row in rows}) == 1
        for row in rows:
            assert row["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
            assert query["query"] in row["messages"][1]["content"]
            assert row["metrics"]["input_tokens"] <= budget
            assert row["input_sha256"] == digest(row["messages"])


def test_actual_context_prefix_budget_is_shared_and_does_not_repack():
    capture = synthetic_capture()
    short = replay(capture, input_token_budget=140)
    long = replay(capture, input_token_budget=10000)
    suffix = "\n\nGive your answer using only the evidence above."
    for partial, complete in zip(short["inputs"], long["inputs"]):
        short_text = partial["messages"][1]["content"][:-len(suffix)]
        full_text = complete["messages"][1]["content"][:-len(suffix)]
        assert full_text.startswith(short_text)
    # Early long R0 content consumes budget; the second hit is not cherry-picked.
    assert neutral_reference("memory", "workshop/spares") not in short["inputs"][0]["messages"][1]["content"]


def test_synthetic_late_span_tradeoff_is_reported_without_quality_claim():
    result = replay(synthetic_capture(), input_token_budget=180)
    raw, evidence, structured = result["inputs"][:3]
    assert raw["metrics"]["retained_selected_span_tokens"] == 0
    assert evidence["metrics"]["retained_selected_span_tokens"] > 0
    assert structured["metrics"]["retained_selected_span_tokens"] > 0
    assert raw["metrics"]["provenance_completeness"] == 0
    assert 0 < evidence["metrics"]["provenance_completeness"] < 1
    assert structured["metrics"]["unbounded_context_tokens"] > evidence["metrics"]["unbounded_context_tokens"]
    summary = compact_summary(result)
    assert summary["downstream_metrics"]["qa_accuracy"] is None
    assert summary["retrieval_metrics"] is None
    assert summary["manifest"]["decision"] == "ITERATE"
    assert summary["manifest"]["reader_configuration"] is None
    serialized = canonical_json(summary)
    assert "The workshop keeps" not in serialized
    assert "synthetic-late-span" not in serialized
    assert "workshop/tools" not in serialized


def test_unbounded_rendering_preserves_all_selected_evidence_and_audit_records():
    result = replay(synthetic_capture(), input_token_budget=10000)
    for row in result["inputs"]:
        assert not row["metrics"]["truncated"]
        if row["metrics"]["selected_span_count"]:
            assert row["metrics"]["selected_span_retention"] == 1.0
        if row["renderer"] != "R0" and row["metrics"]["available_provenance_records"]:
            assert row["metrics"]["provenance_completeness"] == 1.0
            assert "Evidence schema: 1" in row["messages"][1]["content"]


def test_mutating_replay_manifest_cannot_change_original_capture():
    capture = synthetic_capture()
    result = replay(capture, input_token_budget=512)
    result["manifest"]["source"]["tessera_commit"] = "c" * 40
    validate_capture(capture)


def test_doc_and_selected_span_provenance_are_not_conflated():
    capture = synthetic_capture()
    capture["queries"][0]["hits"][0]["provenance"] = None
    result = replay(reseal(capture), input_token_budget=10000)
    row = result["inputs"][1]
    assert row["metrics"]["available_provenance_records"] == 3
    assert row["metrics"]["retained_complete_provenance_records"] == 3
    assert row["messages"][1]["content"].count("Document provenance:") == 1
    assert row["messages"][1]["content"].count("Selected-span provenance:") == 2


def test_coincidental_span_in_another_memory_does_not_count_as_retained():
    queries = [{"query_id": "coincidence", "query": "Which words?", "hits": [
        {"id": "first", "score": 0.9, "body": "golden pear " + "filler " * 200},
        {"id": "second", "score": 0.8, "body": "golden pear", "relevant_evidence": "golden pear"},
    ]}]
    result = replay(capture_again(queries), input_token_budget=100)
    assert "golden pear" in result["inputs"][0]["messages"][1]["content"]
    assert result["inputs"][0]["metrics"]["retained_selected_span_tokens"] == 0


def test_missing_span_fallback_and_empty_results_are_not_sufficiency_labels():
    result = replay(synthetic_capture(), input_token_budget=10000)
    for row in result["inputs"][3:6]:
        assert row["metrics"]["selected_span_count"] == 0
        assert row["metrics"]["selected_span_retention"] is None
        assert row["metrics"]["missing_selected_span_count"] == 1
        assert "The workshop opens in the morning." in row["messages"][1]["content"]
    for row in result["inputs"][6:]:
        assert row["metrics"]["context_tokens"] == 0
        assert row["metrics"]["provenance_completeness"] is None
        assert row["metrics"]["first_selected_span_input_token"] is None


def test_query_ids_and_label_bearing_paths_are_not_reader_inputs():
    capture = synthetic_capture()
    capture["queries"][0]["query_id"] = "secret-question_abs"
    hit = capture["queries"][0]["hits"][0]
    hit["id"] = "longmemeval-v1/secret-question_abs/session"
    for field in ("provenance", "evidence"):
        hit[field]["memory_id"] = hit["id"]
        hit[field]["source"]["path"] = "secret-question_abs/session.md"
        hit[field]["source"]["document_id"] = "secret-question_abs/document"
        hit[field]["evidence_id"] = "secret-question_abs/evidence"
    hit["related_ids"] = ["secret-question_abs/related"]
    result = replay(reseal(capture), input_token_budget=10000)
    for row in result["inputs"]:
        assert "secret-question_abs" not in canonical_json(row["messages"])
    assert result["inputs"][0]["query_id"] == "secret-question_abs"


def test_unicode_whitespace_budget_and_position_are_exact():
    capture = capture_again([{"query_id": "unicode", "query": "Onde está a chave?", "hits": [{
        "id": "chave", "score": 0.3, "body": "Antes.\t\tA chave está aqui.\nDepois.",
        "relevant_evidence": "A chave está aqui.",
    }]}])
    result = replay(capture, input_token_budget=10000)
    raw = result["inputs"][0]
    assert raw["metrics"]["selected_span_tokens"] == 4
    assert raw["metrics"]["retained_selected_span_tokens"] == 4
    prefix = raw["messages"][1]["content"].split("A chave", 1)[0]
    assert raw["metrics"]["first_selected_span_input_token"] == token_count(SYSTEM_PROMPT) + token_count(prefix) + 1


def test_partial_selected_span_has_token_retention_but_not_complete_span():
    capture = capture_again([{"query_id": "one", "query": "Which words?", "hits": [{
        "id": "one", "score": 0.3, "body": "one two three four five six seven eight",
        "relevant_evidence": "one two three four five six seven eight",
    }]}])
    unbounded = replay(capture, input_token_budget=10000)["inputs"][1]
    budget = unbounded["metrics"]["fixed_input_tokens"] + 6  # 3 header + 3 evidence tokens
    bounded = replay(capture, input_token_budget=budget)["inputs"][1]
    assert bounded["metrics"]["retained_selected_span_tokens"] == 3
    assert bounded["metrics"]["retained_complete_span_count"] == 0
    assert bounded["metrics"]["selected_span_retention"] == 3 / 8


def test_replay_never_calls_network_or_engine(monkeypatch):
    from tessera import TesseraEngine
    def forbidden(*args, **kwargs):
        raise AssertionError("replay must not perform I/O or retrieval")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(TesseraEngine, "retrieve_context_contract", forbidden)
    monkeypatch.setattr(TesseraEngine, "build_index", forbidden)
    result = replay(synthetic_capture(), input_token_budget=180)
    assert result["manifest"]["execution"] == {
        "retrieval_calls": 0, "reader_calls": 0, "judge_calls": 0,
        "provider_calls": 0, "cost_usd": 0,
    }


def test_live_engine_contract_capture_replay_does_not_change_retrieval(tmp_path):
    from tessera import TesseraEngine
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "tools.md").write_text(
        "---\nid: workshop/tools\ntype: factual\n---\n"
        "The blue toolkit is kept beside the north door.\n", encoding="utf-8")
    engine = TesseraEngine(storage_dir=str(corpus))
    engine.build_index(use_cache=False, persist=False)
    query = "Where is the blue toolkit kept?"
    hits = engine.retrieve_context_contract(query, top_n=10)
    assert hits and hits[0]["evidence"]
    before = copy.deepcopy(hits)
    capture = capture_again([{"query_id": "live", "query": query, "hits": hits}])
    replay(capture, input_token_budget=512)
    assert hits == before
    assert engine.retrieve_context_contract(query, top_n=10) == before


def test_cli_capture_and_repeated_replay(tmp_path):
    fixture_dir, first, second = (tmp_path / name for name in ("fixture", "one", "two"))
    main(["fixture", "--output-dir", str(fixture_dir)])
    for output in (first, second):
        main(["replay", "--capture", str(fixture_dir / "capture.json"),
              "--input-token-budget", "180", "--output-dir", str(output), "--allow-dirty-worktree"])
    for name in ("manifest.json", "inputs.json", "summary.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    summary = json.loads((first / "summary.json").read_text())
    assert "renderer_environment" in summary["manifest"]
    with pytest.raises(FileExistsError):
        main(["fixture", "--output-dir", str(fixture_dir)])


def test_cli_raw_capture(tmp_path):
    source = tmp_path / "raw.json"
    source.write_text(canonical_json({
        "queries": synthetic_capture()["queries"], "tessera_commit": "a" * 40,
        "retrieval_contract_commit": "b" * 40, "retrieval_configuration": {"top_k": 10},
    }))
    main(["capture", "--input", str(source), "--output-dir", str(tmp_path / "capture")])
    capture = json.loads((tmp_path / "capture/capture.json").read_text())
    validate_capture(capture)


def test_cli_rejects_duplicate_json_keys(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text('{"query": "one", "query": "two"}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        _read(source)


def test_cli_rejects_checkout_output_before_writing():
    root = Path(__file__).resolve().parents[1]
    target = root / "benchmarks/rendering/should-not-exist"
    with pytest.raises(ValueError, match="outside the checkout"):
        main(["fixture", "--output-dir", str(target)])
    assert not target.exists()


def test_cli_invalid_capture_does_not_create_success_artifacts(tmp_path):
    source = tmp_path / "broken.json"
    capture = synthetic_capture()
    capture["queries"].reverse()
    source.write_text(canonical_json(capture))
    target = tmp_path / "result"
    with pytest.raises(ValueError, match="checksum mismatch"):
        main(["replay", "--capture", str(source), "--output-dir", str(target), "--allow-dirty-worktree"])
    assert not target.exists()
