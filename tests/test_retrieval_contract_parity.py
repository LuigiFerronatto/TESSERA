import json
import importlib
import subprocess
import sys
import types

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


def test_mcp_query_matches_engine_contract_fields_and_order(tmp_path, monkeypatch):
    engine = TesseraEngine(storage_dir=str(tmp_path / "corpus"))
    for mem_id, content in (
        ("project/charter", "The project provides auditable memory."),
        ("project/process", "The project process records verified evidence."),
    ):
        engine.write_memory_note(
            mem_id=mem_id, mem_type="factual", episode_id=f"ep-{mem_id}",
            content=content, tags=["project"], entities=[],
        )
    engine.build_index()

    # The MCP package only registers decorators around these functions. A
    # minimal deterministic stand-in keeps this contract test independent of
    # the optional transport dependency and of #93 runtime configuration.
    class FakeFastMCP:
        def __init__(self, _name):
            pass

        @staticmethod
        def tool():
            return lambda function: function

        @staticmethod
        def resource(_uri):
            return lambda function: function

    fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    fastmcp_module.FastMCP = FakeFastMCP
    server_module = types.ModuleType("mcp.server")
    server_module.fastmcp = fastmcp_module
    mcp_module = types.ModuleType("mcp")
    mcp_module.server = server_module
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_module)
    monkeypatch.setenv("TESSERA_STORAGE_DIR", str(tmp_path / "mcp-bootstrap"))
    monkeypatch.setenv("TESSERA_AZURE_GATEWAY_API_KEY", "test-only-placeholder")
    sys.modules.pop("tessera.mcp_server", None)
    mcp_server = importlib.import_module("tessera.mcp_server")
    monkeypatch.setattr(mcp_server, "_engine", engine)

    expected = engine.retrieve_context("project evidence", top_n=2)
    actual = mcp_server.query_memories("project evidence", top_n=2)

    assert actual == expected
    assert [item["id"] for item in actual] == [item["id"] for item in expected]
    assert [list(item) for item in actual] == [list(item) for item in expected]
