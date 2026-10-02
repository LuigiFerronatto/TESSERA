"""Offline R0/R2 parity and overhead probe for #258; synthetic data only."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import statistics
import tempfile
import time

import yaml

from tessera import TesseraEngine
from tessera.recipes import RecipeRunner, builtin_recipe


def snapshot(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def main():
    query = "auditable memory"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with contextlib.redirect_stdout(io.StringIO()):
            engine = TesseraEngine(storage_dir=str(root))
            for identifier, kind, body in (
                ("project/charter", "factual", "The project provides auditable memory."),
                ("project/report", "preference", "Prefer auditable memory reports."),
            ):
                engine.write_memory_note(mem_id=identifier, mem_type=kind,
                    episode_id="recipe-experiment", content=body, tags=["memory"], entities=[])
            engine.build_index()
        runner = RecipeRunner(engine)
        before = snapshot(root)

        def direct(name):
            if name == "search_and_provenance":
                hits = engine.retrieve_context_contract(query, top_n=1)
                return {"search": {"hits": hits}, "provenance": {"records": [
                    row.to_dict() for row in engine.evidence_ledger.for_memory(hits[0]["id"])]}}
            return {store: {"hits": engine.retrieve_from_store(query, store, top_n=1)}
                    for store in ("facts", "preferences")}

        rows = []
        for name in ("search_and_provenance", "compare_drawers"):
            recipe = builtin_recipe(name)
            direct_times, recipe_times = [], []
            mismatch, retry_mismatch = 0, 0
            direct(name)  # warm imported numerical code once before timing
            for _ in range(30):
                start = time.perf_counter()
                expected = direct(name)
                direct_times.append((time.perf_counter() - start) * 1000)
                start = time.perf_counter()
                actual = runner.run(recipe, {"query": query})
                recipe_times.append((time.perf_counter() - start) * 1000)
                mismatch += actual["status"] != "completed" or expected != actual["outputs"]
                retry_mismatch += actual != runner.run(recipe, {"query": query})
            rows.append({"workflow": name, "repeats": 30,
                "parity_failures": mismatch, "replay_mismatches": retry_mismatch,
                "direct_median_ms": round(statistics.median(direct_times), 3),
                "recipe_median_ms": round(statistics.median(recipe_times), 3),
                "declarative_yaml_lines": len(yaml.safe_dump(recipe.to_dict()).splitlines()),
                "primitive_calls_direct": 2, "primitive_calls_recipe": 2,
                "agent_tool_calls_saved": 0})
        result = {"schema_version": 1, "test_card": 258, "benchmark_applicability": "SMOKE_ONLY",
            "decision": "ITERATE", "workflows": rows,
            "filesystem_changed": before != snapshot(root),
            "production_orchestration_lines_removed": 0,
            "r1": "fixed typed registry exercised", "r2": "two opt-in read-only recipes exercised",
            "r3": "explicit fingerprint execution only; no discovery or automatic adoption",
            "candidate_and_write_recipes": "unavailable_pending_owning_contracts"}
        print(json.dumps(result, indent=2))
        if any(row["parity_failures"] or row["replay_mismatches"] for row in rows) or result["filesystem_changed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
