"""Offline capture/replay CLI. No datasets, source reads, retrieval, or providers."""

import argparse
import json
import platform
from pathlib import Path

from benchmarks.longmemeval_v1.run import resolve_git_provenance

from .fixture import synthetic_capture
from .frozen import canonical_json, capture_evidence, validate_capture
from .replay import compact_summary, replay


ROOT = Path(__file__).resolve().parents[2]
MAX_INPUT_BYTES = 64 * 1024 * 1024


def _read(path):
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("input exceeds the 64 MiB offline capture limit")
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)


def _output_dir(path):
    resolved = path.resolve()
    allowed = ROOT / "artifacts" / "rendering"
    if ROOT == resolved or (ROOT in resolved.parents and allowed not in resolved.parents):
        raise ValueError("source-bearing artifacts must be outside the checkout or under artifacts/rendering/<run>")
    # Exclusive new directory: never overwrite frozen evidence or prior attempts.
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write(path, value):
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fixture = subparsers.add_parser("fixture", help="write an invented frozen capture")
    fixture.add_argument("--output-dir", type=Path, required=True)
    capture = subparsers.add_parser("capture", help="freeze label-free raw Engine hit arrays")
    capture.add_argument("--input", type=Path, required=True)
    capture.add_argument("--output-dir", type=Path, required=True)
    replay_parser = subparsers.add_parser("replay", help="render a frozen capture with zero retrieval calls")
    replay_parser.add_argument("--capture", type=Path, required=True)
    replay_parser.add_argument("--input-token-budget", type=int, default=512)
    replay_parser.add_argument("--output-dir", type=Path, required=True)
    replay_parser.add_argument("--allow-dirty-worktree", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "fixture":
        payload = synthetic_capture()
    elif args.command == "capture":
        raw = _read(args.input)
        fields = {"queries", "tessera_commit", "retrieval_contract_commit", "retrieval_configuration"}
        if not isinstance(raw, dict) or set(raw) != fields:
            raise ValueError("capture input requires exactly queries and the three retrieval provenance fields")
        payload = capture_evidence(**raw)
    else:
        payload = _read(args.capture)
        validate_capture(payload)
        result = replay(payload, input_token_budget=args.input_token_budget)
        git = resolve_git_provenance(ROOT, allow_dirty=args.allow_dirty_worktree)
        result["manifest"]["renderer_environment"] = {
            "renderer_commit": git["tessera_commit"],
            "repository_dirty": git["repository_dirty"],
            "reproducible_source": not git["repository_dirty"],
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        }
        summary = compact_summary(result)
        output = _output_dir(args.output_dir)
        _write(output / "manifest.json", result["manifest"])
        _write(output / "inputs.json", result["inputs"])
        _write(output / "summary.json", summary)
        print(canonical_json({"capture_sha256": payload["capture_sha256"],
                              "inputs_sha256": result["manifest"]["inputs_sha256"],
                              "decision": "ITERATE", "provider_calls": 0}))
        return
    output = _output_dir(args.output_dir)
    _write(output / "capture.json", payload)
    print(canonical_json({"capture_sha256": payload["capture_sha256"],
                          "query_count": len(payload["queries"])}))


if __name__ == "__main__":
    main()
