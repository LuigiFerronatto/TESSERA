"""Offline frozen-vector mechanics, not a real-corpus retrieval benchmark."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time
import tracemalloc

from tessera.vector_backend import (ExactFlatBackend, SemanticIndexSpec, VectorFilters,
                                    VectorRecord, VectorSearchRequest)
from tessera.vector_sqlite import SQLiteVectorBackend

PROFILE = "sha256:" + hashlib.sha256(b"synthetic-frozen-265-v1").hexdigest()
VERSION = "sha256:" + hashlib.sha256(b"synthetic-source-version-1").hexdigest()


def measure(call):
    start = time.perf_counter()
    result = call()
    return result, 1000 * (time.perf_counter() - start)


def evaluate():
    fixture = Path(__file__).with_name("frozen.json")
    data = json.loads(fixture.read_text())
    spec = SemanticIndexSpec(PROFILE, len(data["vectors"][0]))
    records = [VectorRecord(f"canonical-{i}", f"source-{i}", VERSION, PROFILE, lane, "1",
                            tuple(vector), source_path=f"docs/{i}.md", project_scope=f"p-{i % 2}",
                            drawer="facts" if lane == "atomic" else None,
                            document_type="memory" if lane == "atomic" else "guide")
               for i, vector in enumerate(data["vectors"]) for lane in ("atomic", "source", "segment")]
    requests = [VectorSearchRequest(tuple(vector), PROFILE, 10, filters)
                for vector in data["queries"] for filters in (
                    VectorFilters(representations=("atomic",)),
                    VectorFilters(representations=("source",)),
                    VectorFilters(representations=("atomic", "source", "segment")),
                    VectorFilters(project_scope="p-1", document_type="guide"))]
    results, outputs = {}, {}
    with tempfile.TemporaryDirectory(prefix="tessera-vectors-") as temporary:
        for label, backend in (("exact-flat", ExactFlatBackend()),
                               ("sqlite-exact", SQLiteVectorBackend(temporary))):
            tracemalloc.start()
            _, open_ms = measure(lambda: backend.open(spec))
            _, build_ms = measure(lambda: backend.rebuild(records))
            hits, latencies = [], []
            repeats = 0
            for request in requests:
                result, duration = measure(lambda: backend.search(request))
                signature = [(h.record.record_id, h.backend_score) for h in result.hits]
                repeated = backend.search(request)
                repeats += signature == [(h.record.record_id, h.backend_score) for h in repeated.hits]
                hits.append(signature)
                latencies.append(duration)
                assert all(request.filters.matches(h.record) for h in result.hits)
            outputs[label] = hits
            # Same authoritative edit, move and deletion on both candidates.
            edited = [replace(r, source_version_hash="sha256:" + "e" * 64,
                              vector=tuple(-v for v in r.vector)) for r in records if r.source_document_id == "source-0"]
            moved = [replace(r, source_path="moved/1.md") for r in records if r.source_document_id == "source-1"]
            def update():
                backend.replace_source("source-0", edited)
                backend.replace_source("source-1", moved)
                backend.replace_source("source-2", [])
            _, update_ms = measure(update)
            clean = ExactFlatBackend()
            clean.open(spec)
            clean.rebuild([r for r in records if r.source_document_id not in ("source-0", "source-1", "source-2")] + edited + moved)
            equivalent = backend.stats().corpus_manifest_hash == clean.stats().corpus_manifest_hash
            ghosts = len(backend.search(VectorSearchRequest(tuple(data["queries"][0]), PROFILE, 100,
                                      VectorFilters(source_ids=("source-2",)))).hits)
            stats = backend.stats()
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            backend.close()
            reopen_ms = None
            if label == "sqlite-exact":
                _, reopen_ms = measure(lambda: backend.open(spec))
                assert backend.stats().corpus_manifest_hash == stats.corpus_manifest_hash
                backend.close()
            results[label] = {"build_ms": build_ms, "open_ms": open_ms, "reopen_ms": reopen_ms,
                              "incremental_edit_move_delete_ms": update_ms,
                              "query_ms_p50": statistics.median(latencies),
                              "query_ms_p95": sorted(latencies)[int(len(latencies) * .95)],
                              "disk_bytes": stats.disk_bytes, "peak_python_tracemalloc_bytes": peak,
                              "repeatability_rate": repeats / len(requests), "ghost_vectors": ghosts,
                              "clean_incremental_equivalent": equivalent, "filtered_search_correctness": 1.0}
            assert equivalent and ghosts == 0
    for label, hits in outputs.items():
        agreement = sum(a == b for a, b in zip(hits, outputs["exact-flat"])) / len(requests)
        recall = statistics.mean(len(set(i for i, _ in a) & set(i for i, _ in b)) / len(b)
                                 for a, b in zip(hits, outputs["exact-flat"]))
        results[label].update(recall_at_10_against_flat=recall, exact_score_and_order_agreement=agreement)
        assert recall == agreement == 1.0
    root = Path(__file__).resolve().parents[2]
    files = ("tessera/vector_backend.py", "tessera/vector_sqlite.py",
             "benchmarks/vector_backends/evaluate.py", "benchmarks/vector_backends/frozen.json")
    return {"schema_version": 1, "issue": 265, "decision": "ITERATE",
            "scope": "frozen synthetic backend mechanics; no model or semantic-quality claim",
            "checkout_head_at_measurement": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "candidate_files_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files},
            "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "python": platform.python_version(), "platform": platform.platform(),
            "record_count": len(records), "dimensions": spec.dimensions, "queries_with_filters": len(requests),
            "top_k": 10, "timing_instrumentation": "Python allocation tracing enabled equally for both backends", "backends": results,
            "limitations": ["SQLite and flat share an exact scoring kernel; analytic metric tests are the independent scoring oracle",
                            "tracemalloc excludes native SQLite allocations and is not process peak RSS",
                            "small fixture, serialized writes, O(ND) search, no ANN-scale claim",
                            "real English/Portuguese/mixed corpora and model quality remain open; independent ANN and bounded native-RSS/scale observations are in the separate preregistered sweep"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
