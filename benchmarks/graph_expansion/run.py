"""Reproducible A0/A1/A2 retrieval ablation on evaluator-owned synthetic labels."""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

from tessera import TesseraEngine
from benchmarks.longmemeval_v1.metrics import ndcg_at_k, recall_at_k, reciprocal_rank


FIXTURE_SHA256 = "32e26f015092430b2d31b5bd40f4c4a019794d819fb645756ebd02527ec2c3b8"
POLICY = {"max_expansions": 5, "max_edges": 128, "token_budget": 1500, "min_edge_score": 0.45}
VARIANTS = {"A0": "none", "A1": "one_hop", "A2": "query_aware"}


def write_corpus(notes, directory):
    """Only documents/relations enter retrieval. Query labels stay in evaluator."""
    for note in notes:
        path = directory / (note["id"] + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = {"id": note["id"], "node_type": "factual", "tags": [],
                       "entities": [], "active_connections": note["connections"],
                       "created_at": "2026-01-01", "last_updated_at": "2026-01-01"}
        path.write_text("---\n" + yaml.safe_dump(frontmatter) + "---\n" + note["body"] + "\n", encoding="utf-8")


def _p95(values):
    import math
    return sorted(values)[max(0, math.ceil(0.95 * len(values)) - 1)]


def _aggregate(rows):
    positives = [row for row in rows if row["relevant_count"]]
    names = ("recall_at_5", "ndcg_at_5", "mrr", "evidence_hit_rate", "evidence_density", "document_precision")
    result = {name: statistics.fmean(row[name] for row in positives) for name in names}
    for name in ("context_tokens", "added_context_tokens", "nodes_visited", "edges_visited",
                 "edge_slots_examined", "subgraph_nodes", "subgraph_edges"):
        values = [row[name] for row in rows if row.get(name) is not None]
        result["mean_" + name] = statistics.fmean(values) if values else None
        result["max_" + name] = max(values) if values else None
    latencies = [value for row in rows for value in row["latencies_ms"]]
    result["latency_p50_ms"] = statistics.median(latencies)
    result["latency_p95_ms"] = _p95(latencies)
    result["empty_result_count"] = sum(not row["retrieved_ids"] for row in rows)
    return result


def run(fixture_path, output_dir, repeats=7, baseline=False):
    raw = fixture_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ValueError("frozen graph fixture checksum mismatch")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    fixture = json.loads(raw)
    variants = {"A1": "one_hop"} if baseline else VARIANTS
    if baseline:
        policies = {"A1": None}
    else:
        from tessera import GraphExpansionPolicy
        policies = {name: GraphExpansionPolicy(mode=mode, **POLICY) for name, mode in variants.items()}
    rows = []
    with tempfile.TemporaryDirectory(prefix="tessera-graph-ablation-") as temporary:
        corpus = Path(temporary) / "corpus"
        write_corpus(fixture["notes"], corpus)
        engine = TesseraEngine(str(corpus))
        started = time.perf_counter()
        engine.build_index(use_cache=False, persist=False)
        indexing_ms = (time.perf_counter() - started) * 1000
        for case in fixture["queries"]:
            timings = {name: [] for name in variants}
            signatures = {}
            hits_by_variant = {}
            # One warm-up followed by interleaved orders, fixed independently of labels.
            for repeat in range(repeats + 1):
                order = list(variants)
                order = order[repeat % len(order):] + order[:repeat % len(order)]
                for name in order:
                    kwargs = {} if baseline else {"graph_expansion": policies[name]}
                    started = time.perf_counter()
                    hits = engine.retrieve_context_contract(case["query"], top_n=fixture["top_k"], **kwargs)
                    elapsed = (time.perf_counter() - started) * 1000
                    signature = [(hit["id"], hit["score"]) for hit in hits]
                    if name in signatures and signatures[name] != signature:
                        raise RuntimeError("nondeterministic retrieval in " + name)
                    signatures[name] = signature
                    hits_by_variant[name] = hits
                    if repeat:
                        timings[name].append(elapsed)
            seeds = None
            for name, hits in hits_by_variant.items():
                trace = {}
                if not baseline:
                    traced = engine.retrieve_context_contract(case["query"], top_n=fixture["top_k"],
                                                             graph_expansion=policies[name], expansion_debug=trace)
                    if [(hit["id"], hit["score"]) for hit in traced] != signatures[name]:
                        raise RuntimeError("debug changed retrieval")
                    if seeds is not None and seeds != trace["seed_ids"]:
                        raise RuntimeError("candidate generator changed across variants")
                    seeds = trace["seed_ids"]
                ids = [hit["id"] for hit in hits]
                relevant = case["relevant_ids"]
                context_tokens = sum(len(hit["body"].split()) for hit in hits)
                relevant_tokens = sum(len(hit["body"].split()) for hit in hits if hit["id"] in relevant)
                rows.append({
                    "query_id": case["id"], "kind": case["kind"], "variant": name,
                    "relevant_count": len(relevant), "retrieved_ids": ids,
                    "scores": [hit["score"] for hit in hits],
                    "recall_at_5": recall_at_k(ids, relevant, 5),
                    "ndcg_at_5": ndcg_at_k(ids, relevant, 5), "mrr": reciprocal_rank(ids, relevant),
                    "evidence_hit_rate": float(bool(set(ids) & set(relevant))),
                    "evidence_density": relevant_tokens / context_tokens if context_tokens else 0.0,
                    "document_precision": len(set(ids) & set(relevant)) / len(ids) if ids else 0.0,
                    "context_tokens": context_tokens, "latencies_ms": timings[name],
                    **{key: trace.get(key) for key in ("added_context_tokens", "nodes_visited", "edges_visited",
                        "edge_slots_examined", "subgraph_nodes", "subgraph_edges")},
                    "trace": trace,
                })
    aggregates = {name: _aggregate([row for row in rows if row["variant"] == name]) for name in variants}
    groups = {kind: {name: _aggregate([row for row in rows if row["variant"] == name and row["kind"] == kind])
                    for name in variants}
              for kind in sorted({row["kind"] for row in rows if row["relevant_count"]})}
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], text=True).strip())
    summary = {"fixture_sha256": FIXTURE_SHA256, "runtime_commit": sha, "runtime_dirty": dirty,
               "python": platform.python_version(), "platform": platform.platform(),
               "query_count": len(fixture["queries"]), "notes": len(fixture["notes"]),
               "repeats": repeats, "warmups_per_query_variant": 1, "policy": POLICY,
               "candidate_generator": "unchanged TF-IDF top-30, similarity > 0.01",
               "reader": None, "qa_accuracy": None, "token_method": "whitespace",
               "indexing_ms": indexing_ms, "variants": aggregates, "groups": groups,
               "limitations": ["Synthetic mechanism evidence, not an external quality estimate",
                   "No reader or downstream QA accuracy", "Budgets limit added evidence, not seed context",
                   "Graph visits count expansion only; indexing, ranking and result navigation are separate",
                   "Unknown relation and two-hop cases expose deliberate coverage limitations",
                   "A3 edge-confidence variant requires #26"],
               "latency_budget": "A2 p95 <= A1 p95 + 10 ms on the same run",
               "decision": "PENDING"}
    if not baseline:
        a0,a1,a2 = [aggregates[name] for name in ("A0", "A1", "A2")]
        summary["gates"] = {
            "quality_over_both": all(a2["recall_at_5"] > prior["recall_at_5"] or a2["ndcg_at_5"] > prior["ndcg_at_5"] for prior in (a0,a1)),
            "density_over_a1": a2["evidence_density"] > a1["evidence_density"],
            "latency": a2["latency_p95_ms"] <= a1["latency_p95_ms"] + 10,
            "added_context": a2["max_added_context_tokens"] <= POLICY["token_budget"],
            "edge_budget": a2["max_edge_slots_examined"] <= POLICY["max_edges"],
        }
        # Synthetic evidence alone does not authorize changing the production default.
        summary["decision"] = "ITERATE; preserve default A1; A2 remains opt-in"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output_dir / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=Path(__file__).with_name("fixture.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--baseline", action="store_true", help="Measure exact unmodified A1 runtime, including older commits")
    args = parser.parse_args()
    print(json.dumps(run(args.fixture, args.output_dir, args.repeats, args.baseline), indent=2))


if __name__ == "__main__":
    main()
