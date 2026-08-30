import json
import subprocess
import sys

from tessera import TesseraEngine
from tessera.evidence import retrieval_results_contract


def test_shared_contract_is_lossless(tmp_path):
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.write_memory_note(
        mem_id="project/charter", mem_type="factual", episode_id="ep-1",
        content="The project provides auditable memory.", tags=["project"], entities=[],
    )
    engine.build_index()
    results = engine.retrieve_context("auditable memory", top_n=1)
    assert retrieval_results_contract(results) == results
    assert {"id", "type", "score", "score_explain", "relevant_evidence",
            "evidence_info", "body", "frontmatter", "filename", "filepath",
            "related_ids", "provenance", "evidence"} <= set(results[0])


def test_cli_json_matches_engine_contract(tmp_path):
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.write_memory_note(
        mem_id="project/charter", mem_type="factual", episode_id="ep-1",
        content="The project provides auditable memory.", tags=["project"], entities=[],
    )
    engine.build_index()
    expected = engine.retrieve_context("auditable memory", top_n=1)
    completed = subprocess.run(
        [sys.executable, "-m", "tessera.cli", "query", str(tmp_path),
         "auditable memory", "--top-n", "1", "--json"],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(completed.stdout) == expected
