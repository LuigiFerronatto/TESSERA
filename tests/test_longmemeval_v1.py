import hashlib
import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmarks.longmemeval_v1 import RETRIEVAL_CONTRACT_COMMIT, run as run_module
from benchmarks.longmemeval_v1.adapter import (
    project_instance,
    stable_memory_id,
    write_instance_corpus,
)
from benchmarks.longmemeval_v1.dataset import (
    deterministic_subset,
    is_abstention,
    load_dataset,
    question_type_counts,
    selected_question_records,
    validate_dataset,
)
from benchmarks.longmemeval_v1.metrics import (
    calculate_metrics,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from benchmarks.longmemeval_v1.run import (
    compare_runs,
    resolve_git_provenance,
    run_baseline,
)
from benchmarks.longmemeval_v1.schemas import validate_artifact_bundle
from tessera import TesseraEngine


def instance(question_id="q-1", question_type="single-session-user", answer=True):
    return {
        "question_id": question_id,
        "question_type": question_type,
        "question": "Where is the verified alpha evidence?",
        "question_date": "2025-01-03",
        "answer": "alpha" if answer else "",
        "answer_session_ids": [f"session-{question_id}-a"] if answer else [],
        "haystack_dates": ["2025-01-01", "2025-01-02"],
        "haystack_session_ids": [f"session-{question_id}-a", f"session-{question_id}-b"],
        "haystack_sessions": [
            [
                {"role": "user", "content": "Please retain the alpha evidence."},
                {"role": "assistant", "content": "The verified alpha evidence is in Porto."},
            ],
            [
                {"role": "user", "content": "Unrelated beta note."},
                {"role": "assistant", "content": "Beta acknowledged."},
            ],
        ],
    }


def metric_result(qid, ground_truth, retrieved, abstention=False, provenance=True):
    return {
        "question_id": qid,
        "question_type": "multi-session",
        "is_abstention": abstention,
        "question": "question",
        "ground_truth_session_ids": ground_truth,
        "retrieved": [
            {
                "rank": rank,
                "memory_id": f"memory/{session_id}",
                "session_id": session_id,
                "score": 1.0 / rank,
                "is_relevant": session_id in ground_truth,
                "provenance_present": provenance,
                "context_characters": 100,
                "context_tokens": 20,
            }
            for rank, session_id in enumerate(retrieved, 1)
        ],
        "latency_ms": 2.0,
        "indexing_latency_ms": 4.0,
    }


def test_official_schema_shape_is_accepted():
    validate_dataset([instance()], expected_instances=1)
    abstention = instance("q-abs_abs", answer=False)
    abstention["answer_session_ids"] = ["answer-sentinel-abs"]
    validate_dataset([abstention], expected_instances=1)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda value: value.pop("question"), "missing fields"),
        (lambda value: value.update(question_id=""), "invalid question_id"),
        (lambda value: value["haystack_dates"].pop(), "misaligned session arrays"),
        (lambda value: value["haystack_sessions"][0][0].pop("role"), "role and content"),
    ],
)
def test_invalid_dataset_is_rejected(mutation, message):
    value = instance()
    mutation(value)
    with pytest.raises(ValueError, match=message):
        validate_dataset([value], expected_instances=1)


def test_json_loader_rejects_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid LongMemEval dataset"):
        load_dataset(path, expected_instances=1)


def test_subset_is_deterministic_stratified_and_has_abstention():
    data = []
    for question_type, count in (("multi-session", 60), ("temporal-reasoning", 30), ("knowledge-update", 10)):
        for index in range(count):
            suffix = "_abs" if index == 0 else ""
            data.append(instance(f"{question_type}-{index}{suffix}", question_type, not suffix))
    shuffled = list(data)
    random.Random(123).shuffle(shuffled)
    first, quotas = deterministic_subset(data, limit=20)
    second, second_quotas = deterministic_subset(shuffled, limit=20)
    assert [item["question_id"] for item in first] == [item["question_id"] for item in second]
    assert quotas == second_quotas == {
        "knowledge-update": 2, "multi-session": 12, "temporal-reasoning": 6
    }
    assert question_type_counts(first) == quotas
    assert any(is_abstention(item) for item in first)
    assert selected_question_records(first) == selected_question_records(second)


def test_stable_ids_and_session_projection_preserve_timestamp_roles_and_order():
    value = instance()
    documents = project_instance(value, "a" * 64)
    first = documents[0]
    assert first.memory_id == stable_memory_id(value["question_id"], value["haystack_session_ids"][0])
    assert "Session timestamp: 2025-01-01" in first.body
    assert first.body.index("user: Please retain") < first.body.index("assistant: The verified")
    assert first.frontmatter["session_id"] == "session-q-1-a"


def test_duplicate_session_ids_are_deduplicated_by_first_occurrence():
    value = instance()
    value["haystack_session_ids"].append(value["haystack_session_ids"][0])
    value["haystack_dates"].append("2025-01-04")
    value["haystack_sessions"].append(value["haystack_sessions"][0])
    documents = project_instance(value, "a" * 64)
    assert len(documents) == 2
    assert documents[0].frontmatter["session_date"] == "2025-01-01"


def test_answer_labels_are_absent_from_source_storage_index_and_raw_results(tmp_path):
    value = instance()
    value["answer"] = "EVALUATOR-ONLY-ANSWER-SENTINEL"
    document = project_instance(value, "b" * 64)[0]
    forbidden_fields = {
        "has_answer", "answer_session_ids", "answer", "expected_answer", "is_relevant"
    }
    assert forbidden_fields.isdisjoint(document.frontmatter)
    for forbidden in forbidden_fields:
        assert forbidden not in document.text
    assert value["answer"] not in document.text
    assert document.frontmatter["tags"] == []
    assert document.frontmatter["entities"] == []
    corpus = tmp_path / "corpus"
    write_instance_corpus(value, corpus, "b" * 64)
    markdown_files = sorted(corpus.glob("*.md"))
    assert len(markdown_files) == 2
    for markdown_path in markdown_files:
        stored = markdown_path.read_text(encoding="utf-8")
        for forbidden in forbidden_fields:
            assert forbidden not in stored
        assert value["answer"] not in stored
    engine = TesseraEngine(storage_dir=str(corpus))
    engine.build_index(use_cache=False, persist=False)
    indexed_text = engine.node_corpus[document.memory_id]
    for forbidden in forbidden_fields:
        assert forbidden not in indexed_text
    assert value["answer"] not in indexed_text
    engine_record = engine.graph.nodes[document.memory_id]
    assert forbidden_fields.isdisjoint(engine_record["frontmatter"])
    assert value["answer"] not in repr(engine_record)
    raw_hits = engine.retrieve_context_contract(value["question"], top_n=2)
    assert raw_hits
    for hit in raw_hits:
        assert forbidden_fields.isdisjoint(hit)
        assert forbidden_fields.isdisjoint(hit["frontmatter"])
        assert value["answer"] not in repr(hit)


def test_question_corpora_are_isolated(tmp_path):
    corpus = tmp_path / "corpus"
    first = write_instance_corpus(instance("q-one"), corpus, "c" * 64)
    assert {doc.frontmatter["question_id"] for doc in first} == {"q-one"}
    with pytest.raises(ValueError, match="must be empty"):
        write_instance_corpus(instance("q-two"), corpus, "c" * 64)


def test_recall_mrr_and_ndcg():
    retrieved = ["wrong", "a", "b"]
    relevant = ["a", "b"]
    assert recall_at_k(retrieved, relevant, 1) == 0.0
    assert recall_at_k(retrieved, relevant, 3) == 1.0
    assert reciprocal_rank(retrieved, relevant) == 0.5
    assert ndcg_at_k(retrieved, relevant, 10) == pytest.approx(0.6934264)


def test_scorecard_metrics_evidence_provenance_and_abstention():
    results = [
        metric_result("positive", ["a"], ["wrong", "a"]),
        metric_result("no-hit", ["z"], ["wrong"], provenance=False),
        metric_result("q_abs", [], [], abstention=True),
    ]
    metrics = calculate_metrics(results)
    assert metrics["recall_at_1"] == 0.0
    assert metrics["recall_at_3"] == 0.5
    assert metrics["mrr"] == 0.25
    assert metrics["evidence_hit_rate"] == 0.5
    assert metrics["first_evidence_position"] == 2.0
    assert metrics["provenance_coverage"] == pytest.approx(2 / 3)
    assert metrics["abstention_retrieval_empty_rate"] == 1.0


def test_empty_corpus_and_query_without_result(tmp_path):
    empty = TesseraEngine(storage_dir=str(tmp_path / "empty"))
    empty.build_index(use_cache=False, persist=False)
    assert empty.retrieve_context_contract("anything") == []
    corpus = tmp_path / "corpus"
    write_instance_corpus(instance(), corpus, "d" * 64)
    engine = TesseraEngine(storage_dir=str(corpus))
    engine.build_index(use_cache=False, persist=False)
    assert engine.retrieve_context_contract("zzzxxyy unmatched gibberish") == []


def _git_runner(head, status):
    def run(command, **_kwargs):
        stdout = f"{head}\n" if command[-1] == "HEAD" else status
        return SimpleNamespace(stdout=stdout)

    return run


def test_git_provenance_resolves_clean_head_and_frozen_contract(tmp_path):
    run_commit = "c" * 40
    provenance = resolve_git_provenance(
        tmp_path, command_runner=_git_runner(run_commit, "")
    )
    assert provenance == {
        "repository_root": ".",
        "repository_dirty": False,
        "dirty_worktree_override": False,
        "tessera_commit": run_commit,
        "retrieval_contract_commit": RETRIEVAL_CONTRACT_COMMIT,
    }
    assert provenance["tessera_commit"] != provenance["retrieval_contract_commit"]


def test_git_provenance_rejects_dirty_repository_by_default(tmp_path):
    with pytest.raises(RuntimeError, match="worktree is dirty"):
        resolve_git_provenance(
            tmp_path,
            command_runner=_git_runner("d" * 40, " M benchmark.py\n"),
        )


def test_git_provenance_records_explicit_dirty_override(tmp_path):
    provenance = resolve_git_provenance(
        tmp_path,
        allow_dirty=True,
        command_runner=_git_runner("e" * 40, " M benchmark.py\n"),
    )
    assert provenance["repository_dirty"] is True
    assert provenance["dirty_worktree_override"] is True
    assert provenance["repository_root"] == "."


def test_artifact_schema_and_two_run_equivalence(tmp_path, monkeypatch):
    data = [instance("q-positive"), instance("q-abstention_abs", answer=False)]
    dataset_path = tmp_path / "synthetic.json"
    dataset_path.write_text(json.dumps(data), encoding="utf-8")
    checksum = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    monkeypatch.setattr(run_module, "DATASET_SHA256", checksum)
    monkeypatch.setattr(run_module, "load_dataset", lambda _path: data)
    first = tmp_path / "run-1"
    second = tmp_path / "run-2"
    run_commit = "f" * 40

    def provenance(_root, _allow_dirty):
        return {
            "repository_root": ".",
            "repository_dirty": False,
            "dirty_worktree_override": False,
            "tessera_commit": run_commit,
            "retrieval_contract_commit": RETRIEVAL_CONTRACT_COMMIT,
        }

    first_bundle = run_baseline(
        dataset_path, "deterministic-small", 2, 10, first,
        provenance_resolver=provenance,
    )
    run_baseline(
        dataset_path, "deterministic-small", 2, 10, second,
        provenance_resolver=provenance,
    )
    validate_artifact_bundle(first_bundle)
    assert first_bundle["manifest"]["tessera_commit"] == run_commit
    assert first_bundle["manifest"]["retrieval_contract_commit"] == RETRIEVAL_CONTRACT_COMMIT
    assert first_bundle["manifest"]["repository_dirty"] is False
    assert first_bundle["manifest"]["reproducible"] is True
    assert compare_runs(first, second)
    assert {path.name for path in first.iterdir()} == {
        "manifest.json", "selected_questions.json", "results.json",
        "scorecard.json", "scorecard.md",
    }
    results = json.loads((first / "results.json").read_text(encoding="utf-8"))
    assert results[0]["corpus_memory_ids"]
    assert [item["memory_id"] for item in results[0]["retrieved"]] == [
        item["memory_id"] for item in json.loads(
            (second / "results.json").read_text(encoding="utf-8")
        )[0]["retrieved"]
    ]

    def dirty_provenance(_root, allow_dirty):
        assert allow_dirty is True
        return {
            "repository_root": ".",
            "repository_dirty": True,
            "dirty_worktree_override": True,
            "tessera_commit": run_commit,
            "retrieval_contract_commit": RETRIEVAL_CONTRACT_COMMIT,
        }

    dirty_bundle = run_baseline(
        dataset_path,
        "deterministic-small",
        2,
        10,
        tmp_path / "dirty-run",
        allow_dirty_worktree=True,
        provenance_resolver=dirty_provenance,
    )
    assert dirty_bundle["manifest"]["reproducible"] is False
    assert "non-reproducible dirty-worktree" in dirty_bundle["scorecard"]["limitations"][-1]
