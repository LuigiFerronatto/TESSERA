"""Preregistered synthetic sweep with a fresh native-memory process per cell."""
import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = Path(__file__).with_name("sweep-plan.json")
PROFILE = "sha256:" + hashlib.sha256(b"synthetic-scale-265-v1").hexdigest()
VERSION = "sha256:" + hashlib.sha256(b"source-version-1").hexdigest()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def coordinate(seed, label, row, column):
    payload = f"{seed}:{label}:{row}:{column}".encode()
    integer = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") >> 11
    return 2 * integer / (2 ** 53) - 1


def generate_fixture(plan, size, dimensions):
    def vector(label, row):
        noise = [coordinate(plan["seed"], label, row, c) for c in range(dimensions)]
        if row % 5 != 4:
            center = [coordinate(plan["seed"], "center", row % 4, c) for c in range(dimensions)]
            return [round(a + .08 * b, 8) for a, b in zip(center, noise)]
        return [round(x, 8) for x in noise]
    return {"kind": "synthetic clustered/uniform mixture; not embeddings",
            "size": size, "dimensions": dimensions,
            "vectors": [vector("record", i) for i in range(size)],
            "queries": [vector("query", i) for i in range(plan["queries_per_filter"])]}


def rss_now():
    if sys.platform.startswith("linux"):
        return int(Path("/proc/self/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    return None


def rss_peak():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform.startswith("linux"):
        return int(value * 1024)
    if sys.platform == "darwin":
        return int(value)
    raise RuntimeError("native RSS units are only defined here for Linux and macOS")


def measure(call):
    start = time.perf_counter()
    value = call()
    return value, (time.perf_counter() - start) * 1000


def worker(backend_name, fixture_path, state_root):
    start = time.perf_counter()
    from tessera.vector_backend import (ExactFlatBackend, SemanticIndexSpec, VectorFilters,
                                        VectorRecord, VectorSearchRequest, corpus_hash)
    from tessera.vector_sqlite import SQLiteVectorBackend
    from tessera.vector_ckdtree import CKDTreeVectorBackend
    import numpy
    import scipy
    import sklearn
    import_ms = (time.perf_counter() - start) * 1000
    baseline_rss, baseline_peak = rss_now(), rss_peak()
    plan = json.loads(PLAN_PATH.read_text())
    data = json.loads(Path(fixture_path).read_text())
    def materialize():
        return [VectorRecord(f"canonical-{i // 3}", f"source-{i // 3}", VERSION, PROFILE,
                             ("atomic", "source", "segment")[i % 3], "1", tuple(vector),
                             source_path=f"docs/{i // 3}.md", project_scope=f"p-{(i // 3) % 2}",
                             drawer="facts" if i % 3 == 0 else None,
                             document_type="memory" if i % 3 == 0 else "guide")
                for i, vector in enumerate(data["vectors"])]
    rows, materialize_ms = measure(materialize)
    queries = tuple(tuple(v) for v in data["queries"])
    del data
    points_rss = rss_now()
    spec = SemanticIndexSpec(PROFILE, len(rows[0].vector))
    factories = {"exact-flat": ExactFlatBackend,
                 "sqlite-exact": lambda: SQLiteVectorBackend(state_root),
                 "ckdtree-exact": lambda: CKDTreeVectorBackend(epsilon=0),
                 "ckdtree-ann": lambda: CKDTreeVectorBackend(epsilon=plan["ann_epsilon"])}
    backend = factories[backend_name]()
    _, open_ms = measure(lambda: backend.open(spec))
    _, ingest_ms = measure(lambda: backend.rebuild(rows))
    build_rss, build_peak = rss_now(), rss_peak()
    filters = {"all": VectorFilters(), "atomic": VectorFilters(representations=("atomic",)),
               "scoped-source": VectorFilters(representations=("source",), project_scope="p-1")}
    requests = {label: [VectorSearchRequest(q, PROFILE, plan["top_k"], filters[label]) for q in queries]
                for label in plan["filters"]}
    cold_ms = {}
    for label, group in requests.items():
        _, cold_ms[label] = measure(lambda: backend.search(group[0]))
    cold_rss, cold_peak = rss_now(), rss_peak()
    signatures, timings, repeats = {}, {}, 0
    query_count = sum(len(group) for group in requests.values())
    for repetition in range(plan["warm_repetitions"]):
        for label, group in requests.items():
            for i, request in enumerate(group):
                result, duration = measure(lambda: backend.search(request))
                assert all(request.filters.matches(h.record) for h in result.hits)
                signature = [[h.record.record_id, h.backend_score] for h in result.hits]
                key = f"{label}:{i}"
                if repetition == 0:
                    signatures[key] = signature
                else:
                    repeats += signature == signatures[key]
                timings.setdefault(label, []).append(duration)
    query_rss, query_peak = rss_now(), rss_peak()
    edited = [replace(r, source_version_hash="sha256:" + "e" * 64,
                      vector=tuple(-v for v in r.vector)) for r in rows if r.source_document_id == "source-0"]
    moved = [replace(r, source_path="moved/1.md") for r in rows if r.source_document_id == "source-1"]
    def update():
        backend.replace_source("source-0", edited)
        backend.replace_source("source-1", moved)
        backend.replace_source("source-2", [])
    _, update_ms = measure(update)
    _, post_update_cold_ms = measure(lambda: backend.search(requests["all"][0]))
    ghosts = len(backend.search(VectorSearchRequest(queries[0], PROFILE, 100,
                              VectorFilters(source_ids=("source-2",)))).hits)
    final_rows = [r for r in rows if r.source_document_id not in ("source-0", "source-1", "source-2")] + edited + moved
    incremental_hash = backend.stats().corpus_manifest_hash
    assert incremental_hash == corpus_hash(final_rows)
    before_clean = backend.search(requests["all"][0]).hits
    backend.close()
    backend = SQLiteVectorBackend(Path(state_root) / "fresh-clean") if backend_name == "sqlite-exact" else factories[backend_name]()
    backend.open(spec)
    _, clean_rebuild_ms = measure(lambda: backend.rebuild(final_rows))
    equivalent = backend.stats().corpus_manifest_hash == incremental_hash
    assert backend.search(requests["all"][0]).hits == before_clean
    stats = backend.stats()
    backend.close()
    peak_bytes = rss_peak()
    assert equivalent and ghosts == 0 and repeats == query_count * (plan["warm_repetitions"] - 1)
    return {"backend": backend_name, "fixture_sha256": digest(fixture_path), "records": len(rows),
            "dimensions": spec.dimensions, "top_k": plan["top_k"], "queries_per_repetition": query_count,
            "thread_environment": {key: os.environ.get(key) for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
            "versions": {"python": platform.python_version(), "numpy": numpy.__version__,
                         "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
            "platform": platform.platform(), "pid": os.getpid(),
            "import_ms": import_ms, "record_materialization_ms": materialize_ms,
            "open_ms": open_ms, "record_ingest_ms": ingest_ms, "cold_query_ms_by_filter": cold_ms,
            "warm_query_ms_by_filter": {label: {"p50": statistics.median(values),
                "p95": sorted(values)[math.ceil(len(values) * .95) - 1]} for label, values in timings.items()},
            "incremental_edit_move_delete_ms": update_ms, "post_update_cold_query_ms": post_update_cold_ms,
            "clean_rebuild_ms": clean_rebuild_ms, "disk_bytes": stats.disk_bytes,
            "native_memory_bytes": {"baseline_current_rss": baseline_rss, "baseline_peak_rss": baseline_peak,
                "after_materialization_current_rss": points_rss, "after_ingest_current_rss": build_rss,
                "after_ingest_peak_rss": build_peak, "after_cold_current_rss": cold_rss,
                "after_cold_peak_rss": cold_peak, "after_warm_current_rss": query_rss,
                "after_warm_peak_rss": query_peak, "full_lifecycle_peak_rss": peak_bytes,
                "peak_above_baseline_peak": max(0, peak_bytes - baseline_peak)},
            "repeatability": repeats / (query_count * (plan["warm_repetitions"] - 1)),
            "filter_correctness": 1.0, "ghost_vectors": ghosts, "clean_incremental_equivalence": equivalent,
            "signatures": signatures}


def compare(candidate, oracle, plan):
    same_inputs = (candidate.get("fixture_sha256") == oracle.get("fixture_sha256") and
                   candidate.get("top_k") == oracle.get("top_k") and
                   candidate.get("queries_per_repetition") == oracle.get("queries_per_repetition"))
    recalls, agreements, score_errors, ratios = [], [], [], []
    for key, expected in oracle["signatures"].items():
        actual = candidate["signatures"][key]
        ids = {i for i, _ in expected}
        recalls.append(len(ids & {i for i, _ in actual}) / len(ids))
        agreements.append([i for i, _ in actual] == [i for i, _ in expected])
        expected_scores = dict(expected)
        score_errors.extend(abs(s - expected_scores[i]) for i, s in actual if i in expected_scores)
        for (_, a), (_, b) in zip(actual, expected):
            actual_distance = math.sqrt(max(0, 2 - 2 * a))
            exact_distance = math.sqrt(max(0, 2 - 2 * b))
            ratios.append(actual_distance / exact_distance if exact_distance else (1 if actual_distance < 1e-12 else float("inf")))
    result = {"identical_frozen_inputs_and_budget": same_inputs, "mean_recall_at_10": statistics.mean(recalls), "minimum_query_recall_at_10": min(recalls),
              "query_id_order_agreement": statistics.mean(agreements),
              "max_common_hit_score_error": max(score_errors, default=0),
              "max_ranked_unit_l2_distance_ratio": max(ratios),
              "query_count_below_recall_review_threshold": sum(x < plan["correctness_gates"]["ann_recall_review_threshold"] for x in recalls)}
    result["mechanics_gate"] = (same_inputs and result["max_common_hit_score_error"] <= plan["correctness_gates"]["score_absolute_tolerance"]
        and (result["mean_recall_at_10"] == 1.0 if candidate["backend"] != "ckdtree-ann" else
             result["max_ranked_unit_l2_distance_ratio"] <= plan["correctness_gates"]["ann_l2_distance_bound_factor"] + 1e-12))
    return result


def run_sweep(output):
    plan = json.loads(PLAN_PATH.read_text())
    report = {"schema_version": 1, "issue": 265, "plan": plan, "plan_sha256": digest(PLAN_PATH),
              "scope": plan["scope"], "decision": "ITERATE", "cells": [],
              "candidate_source_sha256": {name: digest(ROOT / name) for name in (
                  "tessera/vector_backend.py", "tessera/vector_sqlite.py", "tessera/vector_ckdtree.py",
                  "benchmarks/vector_backends/scale_sweep.py")},
              "limitations": ["bounded synthetic observations; no semantic quality or production-scale guarantee",
                  "cKDTree can degrade above about 20 dimensions; epsilon is an L2 distance approximation bound, not a recall guarantee",
                  "full API timing includes different verification/caching policies, not just nearest-neighbor kernels",
                  "cold queries include filtered-tree construction; all cold costs and native peaks are reported",
                  "RSS includes runtime, inputs, native dependencies and lifecycle validation; peak-minus-baseline is descriptive, not isolated allocation accounting",
                  "local timings are unpinned observational measurements; no speed winner or threshold is inferred"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    failed = False
    with tempfile.TemporaryDirectory(prefix="tessera-vector-sweep-") as temp:
        root = Path(temp)
        for size in plan["sizes"]:
            for dimensions in plan["dimensions"]:
                fixture = root / f"frozen-{size}-{dimensions}.json"
                fixture.write_text(json.dumps(generate_fixture(plan, size, dimensions), separators=(",", ":")))
                results = []
                for name in plan["backends"]:
                    child_output = root / f"result-{size}-{dimensions}-{name}.json"
                    command = [sys.executable, str(Path(__file__).resolve()), "--worker", name,
                               "--fixture", str(fixture), "--state-root", str(root / f"state-{size}-{dimensions}-{name}"),
                               "--output", str(child_output)]
                    try:
                        child_env = dict(os.environ)
                        child_env.update({key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
                        subprocess.run(command, capture_output=True, text=True, env=child_env,
                                             timeout=plan["child_timeout_seconds"], check=True)
                        result = json.loads(child_output.read_text())
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                        result = {"backend": name, "records": size, "dimensions": dimensions,
                                  "error": type(exc).__name__, "details": str(exc.stderr)[-2000:]}
                        failed = True
                    results.append(result)
                    print(f"completed records={size} dimensions={dimensions} backend={name} error={result.get('error')}", flush=True)
                oracle = results[0]
                for result in results:
                    if "error" not in result and "error" not in oracle:
                        result["comparison"] = compare(result, oracle, plan)
                        failed = failed or not result["comparison"]["mechanics_gate"]
                for result in results:
                    result.pop("signatures", None)
                report["cells"].extend(results)
                output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    report["all_mechanics_gates_passed"] = not failed
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if failed:
        raise SystemExit("one or more preregistered mechanics gates failed; inspect the complete report")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=("exact-flat", "sqlite-exact", "ckdtree-exact", "ckdtree-ann"))
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--state-root", type=Path)
    args = parser.parse_args()
    if args.worker:
        args.output.write_text(json.dumps(worker(args.worker, args.fixture, args.state_root), allow_nan=False))
    else:
        run_sweep(args.output)


if __name__ == "__main__":
    main()
