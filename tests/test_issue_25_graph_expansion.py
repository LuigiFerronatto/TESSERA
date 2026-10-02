"""Boundary and invariance tests, separate from evaluator-owned relevance labels."""

import copy
import json

import networkx as nx
import pytest

from tessera import GraphExpansionPolicy, TesseraEngine
from tessera.graph_expansion import ExpansionIndex, select_expansion


def graph_fixture():
    graph = nx.DiGraph()
    for name, body in (("seed", "service operation"), ("new", "Durable workers"),
                       ("old", "Ephemeral jobs"), ("noise", "unrelated lunch roster"),
                       ("deep", "Never traverse here")):
        graph.add_node(name, node_type="factual", body=body)
    graph.add_edge("new", "seed", relation_type="supersedes")
    graph.add_edge("seed", "old", relation_type="supersedes")
    graph.add_edge("seed", "noise", relation_type="related_to")
    graph.add_edge("new", "deep", relation_type="caused_by")
    return graph


def select(graph, query="current service", **kwargs):
    debug = {}
    result = select_expansion(graph, ExpansionIndex(graph), query, ["seed"], {"seed": 1.0}, GraphExpansionPolicy(**kwargs), debug)
    return result, debug


@pytest.mark.parametrize("kwargs", [
    {"mode": "bad"}, {"max_hops": 2}, {"max_hops": True}, {"max_expansions": -1},
    {"max_edges": 1.5}, {"max_edges": True}, {"token_budget": -2},
    {"min_edge_score": float("nan")}, {"min_edge_score": float("inf")},
    {"min_edge_score": True}, {"min_edge_score": "0.45"}, {"min_edge_score": 1.1},
])
def test_policy_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        GraphExpansionPolicy(**kwargs)


def test_default_policy_is_bounded_and_immutable():
    policy = GraphExpansionPolicy()
    assert (policy.max_hops, policy.max_expansions, policy.max_edges, policy.token_budget) == (1, 5, 128, 1500)
    with pytest.raises(AttributeError):
        policy.max_hops = 2


def test_supersession_is_query_and_direction_aware_without_claiming_truth():
    graph = graph_fixture()
    (current, _), trace = select(graph)
    (historical, _), _ = select(graph, "previous service")
    assert current == {"seed", "new"}
    assert historical == {"seed", "old"}
    assert any(row["candidate"] == "old" and row["decision"] == "below_threshold" for row in trace["decisions"])
    assert "confidence" not in json.dumps(trace)


def test_only_original_seeds_are_followed_and_graph_is_not_mutated():
    graph = graph_fixture()
    before = copy.deepcopy(nx.node_link_data(graph))
    (nodes, edges), trace = select(graph, "current service why", min_edge_score=0)
    assert "deep" not in nodes
    assert all("seed" in pair for pair in edges)
    assert trace["expanded_node_count"] == 3
    assert nx.node_link_data(graph) == before


def test_no_expansion_keeps_seeds_without_visiting_edges():
    (nodes, edges), trace = select(graph_fixture(), mode="none")
    assert nodes == {"seed"} and edges is None
    assert trace["edges_visited"] == trace["edge_slots_examined"] == 0


def test_a1_ignores_a2_budgets_and_remains_indiscriminate():
    (nodes, edges), trace = select(graph_fixture(), mode="one_hop", max_expansions=0, max_edges=0, token_budget=0)
    assert nodes == {"seed", "new", "old", "noise"} and edges is None
    assert trace["expanded_node_count"] == 3


@pytest.mark.parametrize("limit", [0, 1, 2, 128])
def test_edges_are_bounded_before_high_degree_traversal(limit):
    graph = graph_fixture()
    for i in range(2000):
        graph.add_node(f"fan-{i:04d}", node_type="factual", body="payload")
        graph.add_edge("seed", f"fan-{i:04d}", relation_type="caused_by")
    (_, _), trace = select(graph, "why service", max_edges=limit)
    assert trace["edge_slots_examined"] <= limit
    assert trace["edges_visited"] <= limit
    assert trace["nodes_visited"] <= 1 + limit
    assert trace["traversal_truncated"]
    assert len(trace["decisions"]) <= limit


def test_node_and_token_budgets_apply_once_per_new_node():
    graph = graph_fixture()
    (nodes, _), trace = select(graph, "service", min_edge_score=0, max_expansions=1, token_budget=2)
    assert len(nodes) == 2 and trace["added_context_tokens"] == 2
    (nodes, _), trace = select(graph, "current service", token_budget=1)
    assert nodes == {"seed"} and trace["added_context_tokens"] == 0
    assert any(row["decision"] == "token_budget" for row in trace["decisions"])
    for kwargs in ({"max_expansions": 0}, {"max_edges": 0}, {"token_budget": 0}):
        assert select(graph, **kwargs)[0][0] == {"seed"}


def test_duplicate_candidates_do_not_consume_tokens_twice():
    graph = graph_fixture()
    graph.add_node("second", node_type="factual", body="other seed")
    graph.add_edge("second", "new", relation_type="caused_by")
    trace = {}
    nodes, _ = select_expansion(graph, ExpansionIndex(graph), "current why", ["seed", "second"],
                                {"seed": 1.0, "second": 0.5}, GraphExpansionPolicy(token_budget=2), trace)
    assert nodes == {"seed", "second", "new"}
    assert trace["added_context_tokens"] == 2
    assert sum(row["decision"] == "selected" for row in trace["decisions"]) == 1


def test_segments_are_never_expansion_candidates():
    from tessera.segmentation import SEGMENT_NODE_TYPE
    graph = graph_fixture()
    graph.add_node("segment", node_type=SEGMENT_NODE_TYPE, body="current service")
    graph.add_edge("seed", "segment", relation_type="caused_by")
    (nodes, _), trace = select(graph, "why", min_edge_score=0)
    assert "segment" not in nodes
    assert any(row["decision"] == "segment_excluded" for row in trace["decisions"])


def test_truncation_and_tie_break_are_insertion_order_independent():
    graph = graph_fixture()
    reverse = nx.DiGraph()
    reverse.add_nodes_from(reversed(list(graph.nodes(data=True))))
    reverse.add_edges_from(reversed(list(graph.edges(data=True))))
    assert select(graph, max_edges=2, min_edge_score=0) == select(reverse, max_edges=2, min_edge_score=0)


def test_round_robin_gives_second_seed_a_chance():
    graph = graph_fixture()
    graph.add_node("second", node_type="factual", body="signal")
    graph.add_node("answer", node_type="factual", body="explanation")
    graph.add_edge("second", "answer", relation_type="caused_by")
    trace = {}
    nodes, _ = select_expansion(graph, ExpansionIndex(graph), "why", ["seed", "second"],
                                {"seed": 1.0, "second": 0.5}, GraphExpansionPolicy(max_edges=2), trace)
    assert "answer" in nodes
    assert trace["edge_slots_examined"] == 2


def write_note(tmp_path, name, text, connections=()):
    import yaml
    path = tmp_path / f"{name}.md"
    fm = {"id": name, "node_type": "factual", "active_connections": list(connections)}
    path.write_text("---\n" + yaml.safe_dump(fm) + "---\n" + text + "\n")


def test_engine_default_a1_debug_and_public_contract_are_identical(tmp_path):
    write_note(tmp_path, "seed", "Service runtime strategy", [{"target_memory_id": "extra", "relation_type": "related_to"}])
    write_note(tmp_path, "extra", "Lunch roster")
    engine = TesseraEngine(str(tmp_path))
    engine.build_index()
    default = engine.retrieve_context_contract("Service runtime", top_n=5)
    trace = {"stale": True}
    explicit = engine.retrieve_context_contract("Service runtime", top_n=5,
        graph_expansion=GraphExpansionPolicy(mode="one_hop"), expansion_debug=trace)
    assert explicit == default
    assert trace["selected_ids"] == ["extra"] and "stale" not in trace
    assert not any("expansion_debug" in hit for hit in explicit)
    assert all(hit.get("provenance") for hit in explicit)
    engine.retrieve_context("no_matching_lexeme", expansion_debug=trace)
    assert trace["seed_ids"] == [] and trace["decisions"] == []
    with pytest.raises(TypeError):
        engine.retrieve_context("Service", graph_expansion="none")


def test_expansion_index_is_rebuilt_after_cache_load_and_source_change(tmp_path):
    write_note(tmp_path, "seed", "Service runtime strategy")
    write_note(tmp_path, "new", "Durable workers", [{"target_memory_id": "seed", "relation_type": "supersedes"}])
    engine = TesseraEngine(str(tmp_path))
    engine.build_index()
    fresh = TesseraEngine(str(tmp_path))
    fresh.build_index()
    trace = {}
    fresh.retrieve_context("current service", graph_expansion=GraphExpansionPolicy(), expansion_debug=trace)
    assert trace["selected_ids"] == ["new"]
    (tmp_path / "new.md").unlink()
    fresh.build_index()
    fresh.retrieve_context("current service", graph_expansion=GraphExpansionPolicy(), expansion_debug=trace)
    assert trace["selected_ids"] == []


def test_empty_engine_debug_is_reset(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    trace = {"stale": True}
    assert engine.retrieve_context("nothing", expansion_debug=trace) == []
    assert trace["subgraph_nodes"] == 0 and trace["nodes_visited"] == 0
    assert "stale" not in trace


def test_fixture_is_frozen_and_relevance_labels_never_enter_corpus(tmp_path):
    import hashlib
    from benchmarks.graph_expansion.run import FIXTURE_SHA256, write_corpus
    from pathlib import Path
    fixture_path = Path(__file__).resolve().parents[1] / "benchmarks/graph_expansion/fixture.json"
    assert hashlib.sha256(fixture_path.read_bytes()).hexdigest() == FIXTURE_SHA256
    fixture = json.loads(fixture_path.read_text())
    write_corpus(fixture["notes"], tmp_path)
    for path in tmp_path.rglob("*.md"):
        assert "relevant_ids" not in path.read_text()
        assert "query" not in path.read_text()


def test_oversized_candidate_does_not_block_later_smaller_evidence():
    graph = nx.DiGraph()
    graph.add_node("seed", node_type="factual", body="seed")
    graph.add_node("a-long", node_type="factual", body="many repeated words over budget")
    graph.add_node("b-small", node_type="factual", body="fits")
    for candidate in ("a-long", "b-small"):
        graph.add_edge("seed", candidate, relation_type="caused_by")
    (nodes, _), trace = select(graph, "why", token_budget=1)
    assert nodes == {"seed", "b-small"}
    assert [row["decision"] for row in trace["decisions"]] == ["token_budget", "selected"]


def test_falsy_invalid_policy_is_rejected_even_on_empty_index(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    for value in (False, 0, ""):
        with pytest.raises(TypeError):
            engine.retrieve_context("query", graph_expansion=value)


def test_benchmark_executes_real_retrieval_and_reports_measured_invariants(tmp_path):
    from pathlib import Path
    from benchmarks.graph_expansion.run import run
    fixture = Path(__file__).resolve().parents[1] / "benchmarks/graph_expansion/fixture.json"
    summary = run(fixture, tmp_path / "results", repeats=1)
    assert summary["reader"] is None and summary["qa_accuracy"] is None
    assert set(summary["variants"]) == {"A0", "A1", "A2"}
    rows = json.loads((tmp_path / "results/results.json").read_text())
    assert len(rows) == 3 * summary["query_count"]
    for row in rows:
        assert len(row["latencies_ms"]) == 1
        assert row["context_tokens"] >= 0
        assert 0 <= row["evidence_density"] <= 1
        if row["variant"] == "A2":
            assert row["trace"]["expanded_node_count"] <= 5
            assert row["edge_slots_examined"] <= 128
            assert row["added_context_tokens"] <= 1500
