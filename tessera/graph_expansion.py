"""Experimental, deterministic one-hop expansion; no relation-confidence claims.

The index orders incident edges at index time, so a query never enumerates a
high-degree node before applying its traversal budget. Candidate generation,
ranking and conflict containment remain the caller's responsibility.
"""

import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Set, Tuple

import networkx as nx

from .segmentation import SEGMENT_NODE_TYPE


@dataclass(frozen=True)
class GraphExpansionPolicy:
    """Opt-in A0/A1/A2 policy. Budgets apply to A2 additions, not seed evidence.

    Tokens are whitespace-delimited estimates, not model tokenizer tokens.
    max_edges counts incident edge slots examined (duplicates count too).
    """

    mode: str = "query_aware"
    max_hops: int = 1
    max_expansions: int = 5
    max_edges: int = 128
    token_budget: int = 1500
    min_edge_score: float = 0.45

    def __post_init__(self) -> None:
        if self.mode not in {"none", "one_hop", "query_aware"}:
            raise ValueError("graph expansion mode must be none, one_hop or query_aware")
        if type(self.max_hops) is not int or self.max_hops != 1:
            raise ValueError("only max_hops=1 is supported")
        for name in ("max_expansions", "max_edges", "token_budget"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if (isinstance(self.min_edge_score, bool)
                or not isinstance(self.min_edge_score, (int, float))
                or not math.isfinite(self.min_edge_score)
                or not 0 <= self.min_edge_score <= 1):
            raise ValueError("min_edge_score must be finite and between 0 and 1")


class ExpansionIndex:
    """Disposable stable adjacency order, rebuilt on every Engine build/load."""

    def __init__(self, graph: nx.DiGraph):
        self.incident = {}
        for node in graph:
            outgoing = [(node, target) for target in graph.successors(node)]
            incoming = [(source, node) for source in graph.predecessors(node)
                        if source != node]
            self.incident[node] = tuple(sorted(set(outgoing + incoming)))


def _relation_utility(query_tokens: Set[str], relation: str, incoming: bool) -> float:
    """Fixed bilingual intent lexicon, independent of corpus IDs/gold labels.

    This is a relevance prior, never an edge confidence or a truth assertion.
    Supersession direction is intentional: new --supersedes--> old.
    """
    current = bool(query_tokens & {"current", "latest", "now", "atual", "agora", "vigente"})
    history = bool(query_tokens & {"previous", "before", "historical", "anterior", "antes"})
    if relation == "supersedes":
        if current != history:
            return 1.0 if incoming == current else 0.0
        return 0.25
    if (query_tokens & {"why", "cause", "caused", "reason", "porque", "causa", "motivo"}
            and relation in {"caused_by", "causes", "explains"}):
        return 1.0
    if (query_tokens & {"depends", "dependency", "requires", "prerequisite", "depende", "requer"}
            and relation in {"depends_on", "requires", "prerequisite_for"}):
        return 1.0
    if (query_tokens & {"how", "deploy", "setup", "procedure", "como", "procedimento"}
            and relation in {"stabilizes_service", "standardizes_deployment", "generalization_of"}):
        return 1.0
    return {"supports": 0.45, "evidence_for": 0.45,
            "related_to": 0.15, "mentions": 0.10, "tagged_with": 0.10}.get(relation, 0.10)


def select_expansion(
    graph: nx.DiGraph,
    index: ExpansionIndex,
    query: str,
    seeds: Sequence[str],
    similarities: Mapping[str, float],
    policy: GraphExpansionPolicy,
    debug: Optional[Dict[str, Any]] = None,
) -> Tuple[Set[str], Optional[Set[Tuple[str, str]]]]:
    """Return nodes and optional allowed expansion edges; never follow new nodes.

    Seed order is relevance then ID. Incident lists are consumed round-robin to
    avoid spending the entire traversal budget on the first high-degree seed.
    Traversal uses only the bounded prefix; truncation is reported, not hidden.
    """
    seed_set = set(seeds)
    nodes = set(seeds)
    decisions = []
    visited_nodes = set(seeds)
    visited_edges = set()
    slots = 0
    added_tokens = 0
    selected_edges = set()
    trace = {
        "policy": asdict(policy), "token_count_method": "whitespace",
        "budget_scope": "new one-hop nodes; seed evidence is not truncated",
        "seed_ids": sorted(seed_set), "decisions": decisions,
    }
    if debug is not None:
        debug.clear()
        debug.update(trace)
    if policy.mode == "none":
        candidates = []
        available_slots = 0
    else:
        ordered_seeds = sorted(seed_set, key=lambda node: (-similarities.get(node, 0.0), node))
        available_slots = sum(len(index.incident.get(seed, ())) for seed in ordered_seeds)
        limit = available_slots if policy.mode == "one_hop" else policy.max_edges
        candidates = []
        offsets = {seed: 0 for seed in ordered_seeds}
        active = list(ordered_seeds)
        query_tokens = set(re.findall(r"\b\w+\b", query.lower()))
        while active and slots < limit:
            remaining = []
            for seed in active:
                edges = index.incident.get(seed, ())
                offset = offsets[seed]
                if offset >= len(edges):
                    continue
                source, target = edges[offset]
                offsets[seed] += 1
                slots += 1
                remaining.append(seed)
                other = target if source == seed else source
                visited_nodes.add(other)
                pair = (source, target)
                if pair not in visited_edges:
                    visited_edges.add(pair)
                    relation = graph[source][target].get("relation_type", "")
                    incoming = target == seed
                    utility = _relation_utility(query_tokens, relation, incoming)
                    score = round(0.55 * utility + 0.35 * float(similarities.get(other, 0.0))
                                  + 0.10 * float(similarities.get(seed, 0.0)), 12)
                    entry = {"source": source, "target": target, "seed": seed,
                             "candidate": other, "relation": relation,
                             "direction": "incoming" if incoming else "outgoing",
                             "relation_utility": utility, "score": score,
                             "context_tokens": len(graph.nodes[other].get("body", "").split())}
                    if other in seed_set:
                        entry["decision"] = "already_seed"
                    elif graph.nodes[other].get("node_type") == SEGMENT_NODE_TYPE:
                        entry["decision"] = "segment_excluded"
                    else:
                        candidates.append(entry)
                    if "decision" in entry:
                        decisions.append(entry)
                if slots >= limit:
                    break
            active = remaining
    for entry in sorted(candidates, key=lambda row: (-row["score"], row["candidate"], row["source"], row["target"])):
        candidate = entry["candidate"]
        if policy.mode == "one_hop":
            reason = "selected" if candidate not in nodes else "already_selected"
        elif entry["score"] < policy.min_edge_score:
            reason = "below_threshold"
        elif candidate in nodes:
            reason = "already_selected"
        elif len(nodes - seed_set) >= policy.max_expansions:
            reason = "node_budget"
        elif added_tokens + entry["context_tokens"] > policy.token_budget:
            reason = "token_budget"
        else:
            reason = "selected"
        entry["decision"] = reason
        decisions.append(entry)
        if reason in {"selected", "already_selected"}:
            selected_edges.add((entry["source"], entry["target"]))
        if reason == "selected":
            nodes.add(candidate)
            added_tokens += entry["context_tokens"]
    if debug is not None:
        debug.update({
            "edge_slots_examined": slots, "edges_visited": len(visited_edges),
            "nodes_visited": len(visited_nodes), "edge_slots_available": available_slots,
            "traversal_truncated": slots < available_slots,
            "selected_ids": sorted(nodes - seed_set), "added_context_tokens": added_tokens,
            "expanded_node_count": len(nodes - seed_set),
        })
    return nodes, selected_edges if policy.mode == "query_aware" else None
