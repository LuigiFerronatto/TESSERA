"""Frozen #137 structural audit. Test-double output is never quality evidence.

The same runner can load an unmodified canonical checkout through
--implementation-root. It uses the pre-existing type/content API on that
checkout and the turn-aware API when available. Neither run uses a provider.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run(implementation_root: Path, fixture: Path) -> dict:
    sys.path.insert(0, str(implementation_root.resolve()))
    import tessera
    from tessera.source_formats import split_markdown

    cases = json.loads(fixture.read_text(encoding="utf-8"))
    turn_aware = hasattr(tessera, "EpisodeTurn")
    count = support_count = retained_supports = linked = roundtrip = span_count = 0
    before = {}
    prompt_bytes = 0
    with tempfile.TemporaryDirectory(prefix="tessera-lineage-audit-") as directory:
        engine = tessera.TesseraEngine(directory)
        files = []
        for index, case in enumerate(cases["episodes"]):
            if turn_aware:
                episode = tessera.Episode.from_turns([tessera.EpisodeTurn(**turn) for turn in case["turns"]])
            else:
                # Canonical baseline cannot represent turns. Preserve all input
                # text in its legacy sections; do not implement lineage for it.
                episode = tessera.Episode("", "\n".join(turn["content"] for turn in case["turns"]), "")
            response = json.dumps(case["candidates"])
            def test_double(system_prompt, user_prompt):
                nonlocal prompt_bytes
                prompt_bytes += len(system_prompt.encode("utf-8")) + len(user_prompt.encode("utf-8"))
                return response
            written = engine.decompose_and_write_episode(f"audit/{index}", case["id"], episode, test_double)
            files.extend(written)
            support_count += sum(len(candidate["supporting_turns"]) for candidate in case["candidates"])
            for filename in written:
                metadata, _ = split_markdown(Path(filename).read_text(encoding="utf-8"))
                count += 1
                retained_supports += len(metadata.get("provenance_turns", []))
                before[metadata["id"]] = {
                    key: metadata.get(key) for key in
                    ("episode_id", "provenance_turns", "temporal_position", "episode_source", "source_evidence")
                }
                if metadata.get("episode_source"):
                    source = engine.inspect_source_episode(metadata["episode_id"])
                    linked += source["source"] == metadata["episode_source"]
                span_count += sum(
                    evidence.get("span", {}).get("start_line") is not None
                    for evidence in metadata.get("source_evidence", [])
                )
        engine.build_index(use_cache=False)
        first_results = {hit["id"]: hit.get("lineage") for hit in engine.retrieve_context("project database SQLite weekly summary reports region", top_n=20)}
        fresh = tessera.TesseraEngine(directory)
        fresh.build_index(use_cache=False)
        second_results = {hit["id"]: hit.get("lineage") for hit in fresh.retrieve_context("project database SQLite weekly summary reports region", top_n=20)}
        for memory_id, expected in before.items():
            actual = fresh.graph.nodes[memory_id]["frontmatter"]
            parity = all(actual.get(key) == value for key, value in expected.items())
            if parity and expected["episode_source"] and first_results.get(memory_id) == second_results.get(memory_id):
                roundtrip += 1
        total_bytes = sum(path.stat().st_size for path in Path(directory).rglob("*.md"))
        memory_bytes = sum(Path(file).stat().st_size for file in files)
    fixture_bytes = fixture.read_bytes()
    runtime_hash = hashlib.sha256()
    for file in sorted((implementation_root / "tessera").glob("*.py")):
        runtime_hash.update(file.name.encode())
        runtime_hash.update(file.read_bytes())
    measured_revision = subprocess.check_output(["git", "-C", str(implementation_root), "rev-parse", "HEAD"], text=True).strip()
    metrics = {
        "memory_count": count,
        "decomposition_prompt_utf8_bytes": prompt_bytes,
        "source_episode_linkage_completeness": linked / count,
        "support_reference_retention": retained_supports / support_count,
        "provable_support_span_completeness": span_count / support_count,
        "lineage_write_index_rebuild_result_parity": roundtrip / count,
        "post_persistence_lineage_loss_rate": (linked - roundtrip) / linked if linked else None,
        "source_storage_bytes": total_bytes - memory_bytes,
        "atomic_memory_storage_bytes": memory_bytes,
        "total_storage_bytes": total_bytes,
    }
    if turn_aware:
        assert linked == count == roundtrip == 5
        assert retained_supports == span_count == support_count == 6
    return {
        "schema_version": 1, "benchmark_issue": 137,
        "fixture_kind": cases["fixture_kind"],
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "runtime_python_sha256": runtime_hash.hexdigest(),
        "checkout_revision": measured_revision,
        "turn_aware_api": turn_aware,
        "provider_calls": 0,
        "extraction_input": "frozen_test_double_candidates_not_model_predictions",
        "metrics": metrics,
        "quality_metrics": {
            "supporting_turn_precision": None, "supporting_turn_recall": None,
            "downstream_preference_trajectory_accuracy": None,
            "status": "not_measured_requires_reviewed_labels_and_real_extraction",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-root", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, default=Path(__file__).resolve().parents[2] / "tests/fixtures/episode_lineage_v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.implementation_root, args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
