"""Offline #263 outcome/repair smoke and informational latency (not retrieval quality)."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tessera import TesseraEngine


def run(samples=12):
    timings = {"legacy_persist_only_ms": [], "legacy_write_and_refresh_ms": [],
               "receipt_write_and_refresh_ms": [], "repair_ms": []}
    false_success = duplicate_revisions = 0
    repairs = 0
    for _ in range(samples):
        for mode in tuple(timings)[:3]:
            with tempfile.TemporaryDirectory() as root:
                engine = TesseraEngine(root)
                args = dict(mem_id="project/smoke", mem_type="factual", episode_id="smoke",
                            content="Local deterministic write and repair.", tags=[], entities=[])
                start = time.perf_counter()
                result = engine.write_memory_note_result(**args, **(
                    {"operation_id": "smoke-operation"} if mode.startswith("receipt") else {}))
                if mode == "legacy_write_and_refresh_ms":
                    engine.build_index()
                timings[mode].append((time.perf_counter() - start) * 1000)
                if mode.startswith("receipt"):
                    before = Path(result.filepath).read_bytes()
                    retry = TesseraEngine(root).write_memory_note_result(**args, operation_id="smoke-operation")
                    duplicate_revisions += before != Path(retry.filepath).read_bytes()
                    def fail():
                        raise OSError("synthetic projection failure")
                    engine._persist_evidence_summary = fail
                    failed = engine.write_memory_note_result(**dict(args, mem_id="project/partial"),
                                                              operation_id="partial-operation")
                    false_success += not (failed.persisted and failed.write_receipt.evidence_ledger == "failed")
                    before = Path(failed.filepath).read_bytes()
                    start = time.perf_counter()
                    receipt = TesseraEngine(root).repair_write_receipt("partial-operation")
                    timings["repair_ms"].append((time.perf_counter() - start) * 1000)
                    repairs += not receipt.repair_required
                    duplicate_revisions += before != Path(failed.filepath).read_bytes()
    return {"schema_version": 1, "issue": 263, "samples_per_mode": samples,
            "benchmark_applicability": "SMOKE_ONLY", "network_required": False,
            "generative_model_required": False, "false_success_count": false_success,
            "duplicate_write_or_revision_count": duplicate_revisions,
            "successful_repairs": repairs, "repair_attempts": samples,
            "median_ms": {key: round(statistics.median(value), 3) for key, value in timings.items()},
            "latency_scope": "local temporary filesystem, one-note writes and two-note repair; informational only"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    assert result["false_success_count"] == result["duplicate_write_or_revision_count"] == 0
    assert result["successful_repairs"] == result["repair_attempts"]
