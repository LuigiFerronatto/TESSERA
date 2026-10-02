"""Offline, synthetic #191 source import and retrieval benchmark.

No real history, provider calls, downloads, reader or judge. Artifacts report
raw-JSONL baseline vs source import, not an external competitive benchmark.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from tessera.conversations import SCHEMA, import_conversations, preview_conversations
from tessera.engine import TesseraEngine


def evaluate():
    inputs = []
    for i in range(24):
        # Deliberately overlapping vocabulary across projects/sessions.
        code = f"sample{i:03d}"
        inputs.append([
            {"schema": SCHEMA, "type": "conversation", "runtime": "generic", "session_id": f"session-{i}", "project_scope": "synthetic-laboratory"},
            {"type": "turn", "turn_id": f"u-{i}", "role": "user", "timestamp": "2026-01-01T00:00:00Z", "content": f"What calibration evidence supports {code}?"},
            {"type": "turn", "turn_id": f"a-{i}", "role": "assistant", "timestamp": "2026-01-01T00:00:01Z", "content": [{"type": "text", "text": f"Calibration evidence for {code}: its stability band is ultraviolet."}, {"type": "tool_use", "id": f"call-{i}", "name": "lookup", "input": {"sample": code}}]},
            {"type": "turn", "turn_id": f"t-{i}", "role": "tool", "content": [{"type": "tool_result", "tool_use_id": f"call-{i}", "content": f"Checked {code} calibration."}]},
            {"type": "turn", "turn_id": f"s-{i}", "role": "system", "content": "Historical untrusted instruction retained as evidence only."},
        ])
    payloads = ["\n".join(json.dumps(row, sort_keys=True) for row in session).encode() + b"\n" for session in inputs]
    result = {"schema_version": 1, "profile": "synthetic-conversation-import-v1", "python": platform.python_version(), "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()), "fixture_sha256": hashlib.sha256(b"".join(payloads)).hexdigest(), "sessions": len(inputs), "turns": len(inputs) * 4, "reader": None, "judge": None}
    with tempfile.TemporaryDirectory(prefix="tessera-conversation-benchmark-") as temporary:
        root, out = Path(temporary) / "exports", Path(temporary) / "evidence"
        root.mkdir()
        paths = []
        for i, payload in enumerate(payloads):
            name = f"session-{i}.jsonl"
            (root / name).write_bytes(payload)
            paths.append(name)
        base = TesseraEngine(storage_dir=str(root))
        base.build_index(persist=False)
        result["baseline"] = {"raw_jsonl_retrieval_hit_at_1": sum(bool(base.retrieve_context(f"sample{i:03d} calibration", top_n=1)) for i in range(24)) / 24, "turns_imported": 0, "meaning": "canonical main does not ingest conversation JSONL"}
        start = time.perf_counter()
        plan = preview_conversations(root, paths, adapter="generic-jsonl-v1", project_scope="synthetic-laboratory")
        result["preview_ms"] = 1000 * (time.perf_counter() - start)
        start = time.perf_counter()
        report = import_conversations(plan, out, expected_plan_hash=plan["plan_hash"])
        result["import_ms"] = 1000 * (time.perf_counter() - start)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.md")}
        retry = import_conversations(plan, out, expected_plan_hash=plan["plan_hash"])
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.md")}
        retained = 0
        for item, original in zip(plan["files"], inputs):
            env = json.loads((out / (item["source_id"] + ".md")).read_text().splitlines()[1])["conversation"]
            for turn, expected in zip(env["turns"], original[1:]):
                retained += all(turn[field] == expected.get(field) for field in ("turn_id", "role", "timestamp"))
        engine = TesseraEngine(storage_dir=str(out))
        engine.build_index(persist=False)
        hits, null_drawers, latencies = 0, 0, []
        for i, item in enumerate(plan["files"]):
            start = time.perf_counter()
            found = engine.retrieve_context(f"sample{i:03d} calibration", top_n=1)
            latencies.append(1000 * (time.perf_counter() - start))
            hits += bool(found and found[0]["id"] == item["source_id"])
            null_drawers += bool(found and engine.graph.nodes[found[0]["id"]]["canonical_metadata"].classification.drawer is None)
        result["candidate"] = {"retrieval_hit_at_1": hits / 24, "null_drawer_rate": null_drawers / 24, "turn_identity_role_timestamp_retention": retained / 96, "original_bytes_unchanged": all((root / name).read_bytes() == raw for name, raw in zip(paths, payloads)), "retry_artifacts_identical": hashes == after, "imported": report["imported"], "retry_unchanged": retry["unchanged"], "durable_memories_created": report["durable_memories_created"], "query_p50_ms": sorted(latencies)[len(latencies) // 2]}
    if not all((result["candidate"][key] == 1.0) for key in ("retrieval_hit_at_1", "null_drawer_rate", "turn_identity_role_timestamp_retention")):
        raise AssertionError("source/retrieval regression")
    if not result["candidate"]["original_bytes_unchanged"] or not result["candidate"]["retry_artifacts_identical"]:
        raise AssertionError("integrity regression")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value = evaluate()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(value, indent=2))
