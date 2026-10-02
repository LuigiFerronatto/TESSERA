"""Run with python -m benchmarks.hooks.run --output artifacts/hooks-parity.json."""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import subprocess

from tessera.hook_adapters import FrozenHookAdapter, Invocation
from tessera.lifecycle import (CapturePolicy, ContextCatalog, ContextSection, EventType,
                               HookCore, ProjectBinding, RunBuffer, canonical_json)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/hooks/providers-v1.json"


def semantic_run(runtime):
    """Equivalent two-runtime run including failure, child/echo, compaction, learning text."""
    cases = json.loads(FIXTURES.read_text())["cases"]
    cases = [c for c in cases if c["runtime"] == runtime]
    # Resume variants are independently covered as frozen fixtures. The benchmark
    # run includes one startup, one turn and one session termination.
    cases = [c for c in cases if c["payload"].get("source") not in ("resume", "compact")
             and c["event"] not in ("StopFailure", "Interrupt", "errorOccurred")]
    scope = ProjectBinding("fixture-project", "/fixture/project")
    buffer = RunBuffer("run-main", scope, capture_policy=CapturePolicy(include_content=True))
    core = HookCore(buffer, catalog=ContextCatalog(scope.scope_id, (
        ContextSection("rules", "Check documented release evidence.", "evidence/rules"),)))
    adapter = FrozenHookAdapter(runtime)
    results, events = [], []
    # A child report and parent tool echo explicitly reference the SAME origin.
    # No text-similarity heuristic invents this link.
    expanded = []
    for case in cases:
        expanded.append(case)
        if case["event"] == "SubagentStop":
            echoed = next(c for c in cases if c["event"] == "PostToolUse" and not c["payload"].get("tool_response", {}).get("isError"))
            echoed = json.loads(json.dumps(echoed))
            echoed["invocation"]["evidence_origin_id"] = "origin-child-result"
            expanded.append(echoed)
    for number, case in enumerate(expanded):
        invocation = Invocation("delivery-" + str(number), number, "2026-10-02T00:00:00Z",
                                "run-main", "turn-1", provider_task_id="task-1", **case["invocation"])
        normalized = adapter.normalize(case["event"], case["payload"], invocation, scope)
        for event in normalized.events:
            events.append(event)
            results.append(core.receive(event))
    # Semantic projection removes provider/session/delivery identifiers only;
    # type, order, turn/task/run identity, evidence content and lineage remain.
    def project_event(event):
        data = event.to_dict()
        for field in ("event_id", "runtime", "provider_event", "adapter_version", "runtime_version", "capabilities"):
            data.pop(field)
        data["identities"].pop("runtime_session_id")
        return data
    projected = [project_event(e) for e in buffer.events]
    event_positions = {e.event_id: i for i, e in enumerate(buffer.events)}
    inputs = []
    for group in buffer.episode_inputs():
        group = json.loads(canonical_json(group))
        if group["origin_id"] in event_positions:
            group["origin_id"] = "event-position-" + str(event_positions[group["origin_id"]])
        group["event_ids"] = [event_positions[x] for x in group["event_ids"]]
        for identity in group["lineage"]:
            identity.pop("runtime_session_id")
        inputs.append(group)
    child = next(g for g in inputs if g["origin_id"] == "origin-child-result")
    reads = [i for i, r in enumerate(results) if "READ_BEFORE_REASONING" in r.milestones]
    first_tool = next(i for i, e in enumerate(events) if e.canonical_type == EventType.TOOL_STARTED)
    return {
        "canonical_events": projected, "episode_input_groups": inputs,
        "milestones": [list(r.milestones) for r in results],
        "context_load_positions": reads,
        "boundary_signals": [r.learning_boundary for r in results if r.learning_boundary],
        "metrics": {"event_count": len(projected), "episode_input_group_count": len(inputs),
                    "tool_failures": sum(e.canonical_type == EventType.TOOL_FAILED for e in events),
                    "parent_child_links": sum(e.identities.parent_run_id is not None for e in events),
                    "duplicate_origin_group_count": sum(g["origin_id"] == "origin-child-result" for g in inputs),
                    "child_echo_references": len(child["event_ids"]),
                    "read_before_first_tool": bool(reads) and all(p < first_tool for p in reads),
                    "durable_writes": sum(r.persisted for r in results),
                    "checkpoint_count": sum(r.checkpoint is not None for r in results)},
    }


def run():
    runs = {provider: semantic_run(provider) for provider in ("claude", "codex")}
    baseline, candidate = runs.values()
    gates = {
        "canonical_semantic_sequence_equal": baseline["canonical_events"] == candidate["canonical_events"],
        "episode_inputs_equal": baseline["episode_input_groups"] == candidate["episode_input_groups"],
        "milestones_equal": baseline["milestones"] == candidate["milestones"],
        "context_timing_equal": baseline["context_load_positions"] == candidate["context_load_positions"],
        "boundary_signals_equal": baseline["boundary_signals"] == candidate["boundary_signals"],
        "parent_child_lineage_complete": all(r["metrics"]["parent_child_links"] == 2 for r in runs.values()),
        "child_parent_echo_single_origin": all(r["metrics"]["duplicate_origin_group_count"] == 1 and r["metrics"]["child_echo_references"] == 2 for r in runs.values()),
        "read_before_reasoning": all(r["metrics"]["read_before_first_tool"] for r in runs.values()),
        "failure_evidence_preserved": all(r["metrics"]["tool_failures"] == 1 for r in runs.values()),
        "no_automatic_durable_write": all(r["metrics"]["durable_writes"] == 0 for r in runs.values()),
        "compaction_checkpoint": all(r["metrics"]["checkpoint_count"] == 1 for r in runs.values()),
    }
    # Non-vacuous negative controls: semantic corruptions must change projection.
    corrupt = json.loads(canonical_json(candidate))
    corrupt["canonical_events"][-2]["canonical_type"] = "runtime_session_ended"
    gates["detect_wrong_stop_mapping"] = baseline["canonical_events"] != corrupt["canonical_events"]
    corrupt = json.loads(canonical_json(candidate))
    corrupt["episode_input_groups"] = corrupt["episode_input_groups"][:-1]
    gates["detect_missing_evidence"] = baseline["episode_input_groups"] != corrupt["episode_input_groups"]
    repeated = {p: semantic_run(p) for p in runs}
    gates["same_input_repeatable"] = runs == repeated
    try:
        measured = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.SubprocessError):
        measured = "unavailable"
    source_paths = ("tessera/lifecycle.py", "tessera/hook_adapters.py", "benchmarks/hooks/run.py",
                    "tests/test_issue_196_hook_core.py", "tests/fixtures/hooks/providers-v1.json")
    source_hash = hashlib.sha256(canonical_json({p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                               for p in source_paths}).encode()).hexdigest()
    try:
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--", *source_paths], cwd=ROOT, text=True))
    except (OSError, subprocess.SubprocessError):
        dirty = None
    return {"schema_version": 1, "benchmark_issue": 196,
            "source_sha256": source_hash, "worktree_dirty": dirty,
            "profile": "synthetic-lifecycle-parity-v1", "measured_commit": measured,
            "fixture_sha256": hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
            "threshold": "all declared semantic gates pass; no tolerances",
            "passed": all(gates.values()), "gates": gates,
            "metrics": {p: r["metrics"] for p, r in runs.items()},
            "semantic_sha256": {p: hashlib.sha256(canonical_json(r).encode()).hexdigest() for p, r in runs.items()},
            "baseline": "equivalent Claude canonical run; pre-change main has no Hook Core",
            "unexecuted": {"memory_candidates": "NOT_EXECUTED: #138/#135/#136 integration absent",
                           "admission_and_ltm": "NOT_EXECUTED: zero writes is a safety invariant, not quality evidence",
                           "working_context": "NOT_EXECUTED: prepared bounded catalog substitutes no compiler",
                           "gemini_copilot_full_parity": "NOT_CLAIMED: native event/content/identity gaps; separate frozen mapping tests",
                           "live_provider_installation": "NOT_EXECUTED: #177/#190"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run()
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
