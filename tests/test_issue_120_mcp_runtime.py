"""MCP ownership regressions plus a real stdio subprocess protocol experiment."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_MCP = importlib.util.find_spec("mcp") is not None and sys.version_info >= (3, 10)


def test_import_has_no_configuration_filesystem_or_optional_adapter_activity(tmp_path):
    code = '''
import os
from pathlib import Path
import sys
import socket

def forbidden(*args, **kwargs):
    raise AssertionError("Import must not make a network connection")
socket.socket.connect = forbidden
import tessera.mcp_server as server
assert server._default_runtime.engine is None
assert server._hook is None
assert not Path(os.environ["TESSERA_STORAGE_DIR"]).exists()
for name in ("tessera.hooks", "tessera.orchestrator", "tessera.llm_bridge",
             "tessera.legacy_compat", "mcp", "openai", "anthropic", "benchmarks"):
    assert name not in sys.modules, name
# The old public package exports remain accessible on explicit demand.
from tessera import TesseraTaskHook, TesseraOrchestrator
assert TesseraTaskHook and TesseraOrchestrator
'''
    env = dict(os.environ, TESSERA_STORAGE_DIR=str(tmp_path / "must-not-exist"))
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                   capture_output=True, text=True, check=True, timeout=20)
    subprocess.run([sys.executable, "-m", "tessera.mcp_server", "--help"], cwd=tmp_path,
                   env=env, capture_output=True, text=True, check=True, timeout=20)
    assert not (tmp_path / "must-not-exist").exists()


@pytest.mark.skipif(not HAS_MCP, reason="real transport requires the MCP extra on Python 3.10+")
def test_two_factory_runtimes_do_not_share_configuration_or_engine(tmp_path):
    # Run in a fresh interpreter: historical adapter tests deliberately replace
    # mcp modules with decorator stand-ins and are not transport evidence.
    code = '''
import asyncio
import socket
import sys
from pathlib import Path

def forbidden(*args, **kwargs):
    raise AssertionError("Deterministic startup/retrieval must not contact the network")
socket.socket.connect = forbidden
from tessera.config import ConfigurationResolver
from tessera.mcp_server import create_server

async def run():
    roots = [Path(sys.argv[1]) / name for name in ("first", "second")]
    servers = [create_server(ConfigurationResolver(environ={}).resolve(explicit=str(root))) for root in roots]
    assert all(not root.exists() for root in roots)
    await asyncio.gather(*(server.runtime.start() for server in servers))
    assert servers[0].runtime.engine is not servers[1].runtime.engine
    result = await servers[0].call_tool("write_memory", {
        "mem_id": "project/only-first", "mem_type": "factual", "episode_id": "factory",
        "content": "SQLite is only in the first store.",
    })
    assert result.structuredContent["data"]["persisted"]
    first, second = await asyncio.gather(*(server.call_tool("query_memories", {"query": "SQLite"}) for server in servers))
    assert first.structuredContent["data"]
    assert second.structuredContent["data"] == []
    assert "tessera.orchestrator" not in sys.modules
    assert "tessera.llm_bridge" not in sys.modules
asyncio.run(run())
'''
    subprocess.run([sys.executable, "-c", code, str(tmp_path)], cwd=tmp_path,
                   capture_output=True, text=True, check=True, timeout=30)


@pytest.mark.skipif(not HAS_MCP, reason="real transport requires the MCP extra on Python 3.10+")
def test_real_stdio_contract(tmp_path):
    report = tmp_path / "protocol.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "clean_room" / "check_mcp.py"), "--output", str(report)],
        cwd=tmp_path, capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(report.read_text())
    assert data["passed"] is True
    assert data["check_count"] >= 15


@pytest.mark.skipif(not HAS_MCP, reason="startup lifespan requires the MCP extra")
def test_invalid_store_startup_fails_on_stderr_without_fallback(tmp_path):
    invalid = tmp_path / "regular-file"
    invalid.write_text("fixture-sensitive-value")
    result = subprocess.run(
        [sys.executable, "-m", "tessera.mcp_server", "--store", str(invalid)],
        input="", cwd=tmp_path, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["error"]["code"] == "SERVER_FAILED"
    assert "fixture-sensitive-value" not in result.stderr
    assert not (tmp_path / "memories").exists()
    assert invalid.read_text() == "fixture-sensitive-value"
