"""Offline R0/R1/R2/R3 source-history experiment for issue #73.

R3 is a benchmark-only current-hash pointer, not a temporal-validity model.
The pointer does not authorize overriding current source text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import shutil
import tempfile
import time

from tessera import TesseraEngine
from tessera.canonical import compute_sha256


def source_text(topic: int, version: int, mode: str) -> str:
    memory_id = f"project/topic{topic:03d}"
    relation = ""
    if mode == "R1":
        memory_id += f"-v{version}"
        if version:
            relation = f"active_connections:\n  - target_memory_id: project/topic{topic:03d}-v{version - 1}\n    relation_type: supersedes\n"
    return (f"---\nid: {memory_id}\nnode_type: preference\ntags: [browser, topic{topic:03d}]\n"
            f"{relation}---\n\nTopic{topic:03d} browser capture preference is recorder{version}.\n\n"
            + "A deterministic audit trail preserves the source and its context.\n" * 20)


def measure(mode: str, root: Path, documents: int, versions: int) -> dict:
    store = root / mode
    store.mkdir()
    history_enabled = mode in ("R2", "R3")
    engine = TesseraEngine(str(store), revision_history=history_enabled)
    old_records = []
    snapshots = []
    index_seconds, parsed, unchanged = 0.0, 0, 0
    for version in range(versions):
        for topic in range(documents):
            suffix = f"-v{version}" if mode == "R1" else ""
            path = store / f"topic{topic:03d}{suffix}.md"
            text = source_text(topic, version, mode)
            path.write_text(text, encoding="utf-8")
        start = time.perf_counter()
        engine.build_index()
        index_seconds += time.perf_counter() - start
        parsed += engine.last_index_stats["parsed"]
        unchanged += engine.last_index_stats["unchanged"]
        if version < versions - 1:
            for topic in range(documents):
                memory_id = f"project/topic{topic:03d}" + (f"-v{version}" if mode == "R1" else "")
                record = engine.evidence_ledger.for_memory(memory_id)[0].to_dict()
                old_records.append(record)
                snapshots.append((record["source"]["document_id"], record["source"]["document_hash"]))
    pointer = {}
    if mode == "R3":
        pointer = {record.memory_id: record.source.document_hash for record in
                   (engine.evidence_ledger.get(item["evidence_id"]) for item in engine.evidence_ledger.to_list())}
        (store / "current-pointers.json").write_text(json.dumps(pointer, sort_keys=True), encoding="utf-8")
    # A no-op incremental scan must neither reparse nor emit history transitions.
    engine.build_index()
    noop_parsed = engine.last_index_stats["parsed"]
    accuracy = 0
    query_start = time.perf_counter()
    for topic in range(documents):
        hits = engine.retrieve_context(f"topic{topic:03d} browser capture preference", top_n=1)
        correct = bool(hits) and f"recorder{versions - 1}" in hits[0]["body"]
        if mode == "R3" and hits:
            correct = correct and pointer.get(hits[0]["id"]) == hits[0]["provenance"]["source"]["document_hash"]
        accuracy += int(correct)
    query_seconds = time.perf_counter() - query_start
    live_documents = len(engine.file_registry)
    supersedes_edges = sum(data.get("relation_type") == "supersedes" for _, _, data in engine.graph.edges(data=True))
    if mode == "R1":
        assert supersedes_edges == documents * (versions - 1)

    current_bytes = sum(len(source_text(topic, versions - 1, "R0").encode()) for topic in range(documents))
    durable_bytes = sum(path.stat().st_size for path in store.rglob("*")
                        if path.is_file() and ".tessera_index" not in path.parts)
    # Remove *all* derived state before asking to resolve history.
    shutil.rmtree(engine.index_cache_dir)
    engine = TesseraEngine(str(store), revision_history=history_enabled)
    engine.build_index()
    historical_bodies = provenance = 0
    for record in old_records:
        if engine.revision_history is not None:
            resolved = engine.revision_history.resolve_evidence(record["evidence_id"])
            valid = bool(resolved) and compute_sha256(resolved["revision"]["raw_text"]) == record["source"]["document_hash"]
            historical_bodies += int(valid)
            provenance += int(valid and resolved["evidence"]["fingerprint"] == record["fingerprint"])
        else:
            rebuilt = engine.evidence_ledger.get(record["evidence_id"])
            valid = rebuilt is not None and rebuilt.fingerprint == record["fingerprint"]
            if valid:
                raw = Path(engine.file_registry[rebuilt.memory_id]).read_text(encoding="utf-8")
                valid = compute_sha256(raw) == record["source"]["document_hash"]
            historical_bodies += int(valid)
            provenance += int(valid)
    return {
        "mode": mode, "explicit_supersedes_edges": supersedes_edges, "logical_documents": documents, "versions_per_document": versions,
        "old_versions_tested": len(old_records), "live_documents": live_documents,
        "historical_reconstructability": historical_bodies / len(old_records),
        "old_canonical_evidence_completeness": provenance / len(old_records),
        "duplicate_live_memory_rate": (live_documents - documents) / live_documents,
        "current_state_top1_accuracy": accuracy / documents,
        "durable_storage_bytes": durable_bytes, "current_source_reference_bytes": current_bytes,
        "storage_ratio_to_current_only": durable_bytes / current_bytes,
        "incremental_parsed_total": parsed, "incremental_unchanged_total": unchanged,
        "noop_parsed": noop_parsed, "index_seconds": index_seconds,
        "query_seconds": query_seconds,
        "pointer_semantics": "benchmark_only_current_hash" if mode == "R3" else None,
    }


def run(documents: int = 8, versions: int = 4) -> dict:
    if documents < 1 or versions < 2:
        raise ValueError("documents must be positive and versions must be at least two")
    with tempfile.TemporaryDirectory(prefix="tessera-revisions-") as directory:
        measurements = [measure(mode, Path(directory), documents, versions) for mode in ("R0", "R1", "R2", "R3")]
    return {"schema_version": 1, "issue": 73, "fixture": "synthetic-browser-preferences-v1",
            "python": platform.python_version(), "platform": platform.system(),
            "limitations": ["Synthetic lifecycle evidence, not competitive retrieval evaluation.",
                            "R3 is only a benchmark-local hash pointer; temporal validity remains unimplemented.",
                            "Old evidence metric uses canonical document records; issued paragraph IDs have separate contract tests.",
                            "Durable bytes exclude disposable indexes; SQLite fixed overhead dominates small corpora.",
                            "Latency is observational, not a deterministic pass/fail gate."],
            "results": measurements}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents", type=int, default=8)
    parser.add_argument("--versions", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.documents, args.versions)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
