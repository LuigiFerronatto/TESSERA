"""MCP Python SDK 1.x/2.x compatibility boundary (#363)."""
import asyncio
import importlib.metadata
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HAS_MCP = importlib.util.find_spec("mcp") is not None and sys.version_info >= (3, 10)


def test_runtime_imports_the_sdk_only_through_one_boundary():
    offenders = []
    for path in sorted((ROOT / "tessera").rglob("*.py")):
        if path.name == "mcp_sdk.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if re.match(r"\s*(from mcp[ .]|import mcp\b)", line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    # diagnostics.py only probes availability; everything else uses mcp_sdk.
    assert offenders == ["tessera/diagnostics.py:172: import mcp  # noqa: F401"]


@pytest.mark.skipif(not HAS_MCP, reason="requires the MCP extra")
def test_boundary_reports_the_installed_sdk_major():
    from tessera import mcp_sdk

    installed = importlib.metadata.version("mcp")
    assert mcp_sdk.SDK_VERSION == installed
    assert mcp_sdk.SDK_MAJOR == int(installed.split(".")[0])
    assert mcp_sdk.SDK_MAJOR in {1, 2}


def test_unsupported_sdk_error_names_the_detected_version(tmp_path):
    fake = tmp_path / "site"
    (fake / "mcp").mkdir(parents=True)
    (fake / "mcp" / "__init__.py").write_text("", encoding="utf-8")
    (fake / "mcp" / "types.py").write_text("", encoding="utf-8")
    dist = fake / "mcp-3.0.0.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: mcp\nVersion: 3.0.0\n", encoding="utf-8")
    script = (
        "import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]]\n"
        "try:\n"
        "    import tessera.mcp_sdk\n"
        "except ImportError as exc:\n"
        "    print(exc)\n"
        "else:\n"
        "    print('imported')\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(fake), str(ROOT)],
        capture_output=True, text=True, check=True,
    )
    message = result.stdout.strip()
    assert "3.0.0" in message
    assert "mcp>=1.30.0,<3.0.0" in message
    assert "pip install" not in message  # the extra is installed; the version is the problem


@pytest.mark.skipif(not HAS_MCP, reason="requires the MCP extra")
def test_in_process_round_trip_uses_versioned_contract_on_installed_sdk(tmp_path):
    from tessera import mcp_sdk
    from tessera.config import ConfigurationResolver
    from tessera.mcp_server import create_server

    async def run():
        server = create_server(ConfigurationResolver(environ={}).resolve(explicit=str(tmp_path / "store")))
        await server.runtime.start()
        tools = {tool.name: tool for tool in await server.list_tools()}
        schema = mcp_sdk.tool_input_schema(tools["query_memories"])
        assert schema["$id"] == "urn:tessera:mcp:1.0:query_memories:request"
        assert schema["additionalProperties"] is False
        assert mcp_sdk.tool_output_schema(tools["query_memories"])["$id"] == "urn:tessera:mcp:1.0:response"
        written = await server.call_tool("write_memory", {
            "mem_id": "project/compat", "mem_type": "factual", "episode_id": "compat",
            "content": "The compatibility boundary supports two SDK majors.",
        })
        assert mcp_sdk.structured_content(written)["data"]["persisted"]
        found = await server.call_tool("query_memories", {"query": "compatibility boundary"})
        assert mcp_sdk.structured_content(found)["error"] is None
        assert mcp_sdk.is_error(found) is False
        unknown = await server.call_tool("no_such_tool", {})
        assert mcp_sdk.structured_content(unknown)["error"]["code"] == "UNKNOWN_TOOL"
        assert mcp_sdk.is_error(unknown) is True
        contents = list(await server.read_resource("server://health"))
        assert contents and contents[0].mime_type == "application/json"

    asyncio.run(run())
