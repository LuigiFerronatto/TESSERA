"""Reproducible synthetic preparation report; no official execution command."""

import argparse
import json
from importlib.metadata import version
from pathlib import Path
import platform
import subprocess
import tempfile

from . import DATASET_REVISION, PROFILE, UPSTREAM_COMMIT
from .adapter import SyntheticTesseraMemory
from .contracts import UnsupportedProtocol, bound_context, canonical_json, digest, invoke_query
from .fixture import trajectories, write_assets


def _require(condition):
    if not condition:
        raise RuntimeError("synthetic conformance observation failed")


def run_synthetic():
    reports = []
    with tempfile.TemporaryDirectory(prefix="v2-fixture-") as temporary:
        root = Path(temporary) / "assets"
        write_assets(root)
        for trajectory in trajectories():
            with SyntheticTesseraMemory(root, profile=PROFILE, context_budget=100) as memory:
                memory.insert(trajectory)
                _require(memory.trajectory_snapshot() == [trajectory])
                query = trajectory["goal"]
                items = memory.query(query)
                audit = memory.audit()
                normalized = [{**item, "value": Path(item["value"]).relative_to(root).as_posix()}
                              if item["type"] == "image" else item for item in items]
                _require(normalized and audit["final_units"] <= audit["budget"])
                _require(len(audit["provenance"]) == len(items))
                _require(memory.query(query, "question_screenshots/synthetic.png") == items)
                # Poison evaluator-only fields without copying/serializing them.
                private = object()
                record = {"question": query, "id": private, "question_type": private,
                          "answer": private, "eval_function": private, "evaluator_config": private,
                          "raw_question": private}
                _require(invoke_query(memory, record, "first-trace") == items)
                _require(memory.get_query_context() == {} and memory.audit() is None)
                reports.append({"domain": trajectory["domain"], "trajectory_sha256": digest(trajectory),
                                "states": len(trajectory["states"]), "context_items": len(items),
                                "text_items": sum(i["type"] == "text" for i in items),
                                "image_items": sum(i["type"] == "image" for i in items),
                                "context_sha256": digest(normalized), "audit": audit})
        with SyntheticTesseraMemory(root, profile=PROFILE) as empty:
            _require(empty.query("blue toolkit") == [])
    try:
        bound_context([], 100)
    except UnsupportedProtocol as exc:
        official_budget = str(exc)
    else:
        raise AssertionError("official budget must remain blocked")
    return {"schema_version": 1, "profile": PROFILE,
            "status": "partial_synthetic_preparation", "official_conformance": False,
            "official_evaluation": "NOT_RUN", "provider_calls": 0, "cost_usd": 0,
            "source": "original_invented_fixture", "domains": reports,
            "official_budget": {"status": "UNSUPPORTED", "diagnostic": official_budget},
            "save_load": "UNSUPPORTED", "visual_retrieval": "UNSUPPORTED",
            "fixture_sha256": digest(trajectories())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-dirty-worktree", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    output = args.output_dir.resolve()
    allowed = root / "artifacts/longmemeval-v2"
    if output.is_relative_to(root) and not output.is_relative_to(allowed):
        raise ValueError("output must be outside checkout or under artifacts/longmemeval-v2")
    if output.exists():
        raise FileExistsError("output directory already exists; use a new run directory")
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True).strip())
    if dirty and not args.allow_dirty_worktree:
        raise RuntimeError("dirty worktree; commit changes or explicitly allow dirty preparation")
    report = run_synthetic()
    manifest = {"profile": PROFILE, "tessera_commit": head, "repository_dirty": dirty,
                "upstream_commit": UPSTREAM_COMMIT, "dataset_revision": DATASET_REVISION,
                "dataset_loaded": False, "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": {name: version(name) for name in ("numpy", "scipy", "scikit-learn", "networkx", "PyYAML")},
                "synthetic_conformance_sha256": digest(report),
                "protocol_sha256": digest(json.loads((Path(__file__).parent / "protocol.json").read_text())),
                "reader_configuration": None, "judge_configuration": None,
                "official_context_token_budget": None, "quality_acceptance": None}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("manifest.json", manifest), ("conformance.json", report)):
        (output / name).write_text(canonical_json(value) + "\n", encoding="utf-8")
    print(canonical_json({"profile": PROFILE, "status": report["status"],
                          "official_conformance": False, "sha256": digest(report)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
