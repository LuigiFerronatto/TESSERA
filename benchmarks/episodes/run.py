"""Run the frozen unreviewed synthetic #138 diagnostic, offline and opt-in."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from typing import Dict, List, Sequence

from tessera.episode_boundary import EpisodeBoundaryTracker
from benchmarks.episodes.experiment import ExperimentTurn, parse_timestamp, segment, validate_turns

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("dialogues.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixture() -> Dict:
    # Hash checked before parsing: diagnostics may not silently relabel this draft.
    expected = Path(__file__).with_name("dialogues.sha256").read_text().split()[0]
    if sha256(FIXTURE) != expected:
        raise ValueError("frozen fixture checksum mismatch; use a new reviewed version")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if fixture["label_status"] != "synthetic_author_draft_not_human_reviewed":
        raise ValueError("this runner is only for draft synthetic diagnostics")
    ids = [case["dialogue_id"] for case in fixture["dialogues"]]
    if len(ids) != len(set(ids)):
        raise ValueError("dialogue IDs must be unique")
    for case in fixture["dialogues"]:
        turns = [ExperimentTurn(**row) for row in case["turns"]]
        validate_turns(turns)
        legal = {t.turn_id for t in turns[1:] if t.role == "user"}
        boundaries = case["draft_boundary_ids"]
        if len(boundaries) != len(set(boundaries)) or not set(boundaries) <= legal:
            raise ValueError("draft boundaries must be unique noninitial user turn IDs")
    return fixture


def score(turn_ids: Sequence[str], expected: Sequence[str], predicted: Sequence[str]) -> Dict:
    """All-turn boundary slots, not only user slots: assistant false splits count.

    WindowDiff uses k=max(1, round(N / (2 * reference episodes))) adjacent
    boundary slots per window, clipped to available slots, and equal-count errors.
    False split=FP/reference negatives; false merge=FN/reference positives.
    Empty denominators are null, except perfect empty-boundary P/R/F1 = 1.
    """
    slots = list(turn_ids[1:])
    for values in (expected, predicted):
        if len(values) != len(set(values)) or not set(values) <= set(slots):
            raise ValueError("invalid boundary IDs")
    truth, guess = set(expected), set(predicted)
    tp, fp, fn = len(truth & guess), len(guess - truth), len(truth - guess)
    precision = tp / len(guess) if guess else (1.0 if not truth else 0.0)
    recall = tp / len(truth) if truth else 1.0
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0
    negatives = len(slots) - len(truth)
    k = min(len(slots), max(1, round(len(turn_ids) / (2 * (len(truth) + 1)))))
    windows = [slots[i:i + k] for i in range(len(slots) - k + 1)] if k else []
    errors = sum(sum(x in truth for x in window) != sum(x in guess for x in window)
                 for window in windows)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": f1, "false_split_rate": fp / negatives if negatives else None,
            "false_merge_rate": fn / len(truth) if truth else None,
            "windowdiff": errors / len(windows) if windows else 0.0,
            "window_size": k, "reference_negative_slots": negatives}


def baseline(turns: Sequence[ExperimentTurn]) -> Dict:
    """Execute E0 unchanged, detecting closes without inspecting its private state."""
    validate_turns(turns)
    if any(t.timestamp is None for t in turns):
        raise ValueError("E0 comparison requires explicit timestamps; no invented times")
    tracker = EpisodeBoundaryTracker()
    episodes: List[List[str]] = []
    current: List[str] = []
    for turn in turns:
        if tracker.add_turn(turn.content, parse_timestamp(turn.timestamp)) is not None:
            episodes.append(current)
            current = []
        current.append(turn.turn_id)
    if tracker.flush() is not None:
        episodes.append(current)
    return {"episodes": episodes, "boundary_ids": [e[0] for e in episodes[1:]],
            "decisions": None, "note": "actual unchanged E0; no separated reason API"}


def candidate(turns: Sequence[ExperimentTurn], variant: str) -> Dict:
    result = segment(turns, variant=variant)
    assert tuple(t for episode in result.episodes for t in episode) == tuple(turns)
    return {"episodes": [[t.turn_id for t in episode] for episode in result.episodes],
            "boundary_ids": list(result.boundary_ids),
            "decisions": [asdict(decision) for decision in result.decisions]}


def evaluate() -> Dict:
    fixture = load_fixture()
    report = {"schema_version": 1, "fixture_sha256": sha256(FIXTURE),
              "label_status": fixture["label_status"], "decision": "PENDING",
              "acceptance_gate": "BLOCKED: independent human review and downstream evaluation",
              "quality_metrics": {"human_boundary_precision": None, "human_boundary_recall": None,
                                  "human_boundary_f1": None, "downstream_decomposition_delta": None},
              "environment": {"python": platform.python_version(),
                              "scikit_learn": importlib.metadata.version("scikit-learn")},
              "git_head_at_run": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                         cwd=ROOT, text=True).strip(),
              "git_dirty_at_run": bool(subprocess.check_output(
                  ["git", "status", "--porcelain"], cwd=ROOT, text=True)),
              "parameters": {"similarity_threshold": 0.03, "timeout_minutes": 30,
                             "E3_gap_basis": "adjacent_user_timestamps"},
              "source_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in (
                  ROOT / "tessera/episode_boundary.py", Path(__file__).resolve(),
                  Path(__file__).with_name("experiment.py"), Path(__file__).with_name("prepare_review.py"))},
              "variants": {}}
    for variant in ("E0", "E1", "E3"):
        rows, timings, lengths = [], [], []
        repeatable = True
        for case in fixture["dialogues"]:
            turns = [ExperimentTurn(**row) for row in case["turns"]]
            start = perf_counter()
            result = baseline(turns) if variant == "E0" else candidate(turns, variant)
            timings.append((perf_counter() - start) * 1000 / len(turns))
            repeated = baseline(turns) if variant == "E0" else candidate(turns, variant)
            repeatable = repeatable and result == repeated
            lengths.extend(len(episode) for episode in result["episodes"])
            rows.append({"dialogue_id": case["dialogue_id"], **result,
                         "draft_label_diagnostics": score([t.turn_id for t in turns],
                             case["draft_boundary_ids"], result["boundary_ids"])})
        tp = sum(row["draft_label_diagnostics"]["tp"] for row in rows)
        fp = sum(row["draft_label_diagnostics"]["fp"] for row in rows)
        fn = sum(row["draft_label_diagnostics"]["fn"] for row in rows)
        negatives = sum(row["draft_label_diagnostics"]["reference_negative_slots"] for row in rows)
        total_turns = sum(len(case["turns"]) for case in fixture["dialogues"])
        report["variants"][variant] = {
            "draft_label_diagnostics": {"tp": tp, "fp": fp, "fn": fn,
                "precision": tp / (tp + fp) if tp + fp else 0.0,
                "recall": tp / (tp + fn) if tp + fn else 1.0,
                "f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0,
                "false_split_rate": fp / negatives if negatives else None,
                "false_merge_rate": fn / (tp + fn) if tp + fn else None,
                "macro_windowdiff": sum(row["draft_label_diagnostics"]["windowdiff"] for row in rows) / len(rows)},
            "repeatable_excluding_latency": repeatable, "episode_lengths_in_turns": lengths,
            "latency_ms_per_turn_weighted_mean": sum(t * len(c["turns"]) for t, c in zip(
                timings, fixture["dialogues"])) / total_turns,
            "cases": rows}
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", action="store_true", help="Omit per-case traces from the saved report")
    parser.add_argument("--require-reviewed", action="store_true",
                        help="Fail closed: this frozen draft has no independent human labels")
    args = parser.parse_args()
    if args.require_reviewed:
        parser.exit(2, "BLOCKED: the frozen synthetic fixture has not been independently human-reviewed\n")
    report = evaluate()
    if args.summary:
        report["detail"] = "aggregate_only"
        for variant in report["variants"].values():
            del variant["cases"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "decision": report["decision"],
                      "acceptance_gate": report["acceptance_gate"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
