"""Issue #95 regression matrix for the generic runtime/compatibility boundary."""

import json
import importlib
import re
import subprocess
import sys
import types
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

from tessera import TesseraEngine
from tessera.cli import build_parser, main
from tessera.config import (
    LegacyStorageConfigurationWarning,
    resolve_storage_dir,
)
from tessera.diagnostics import build_quickstart_plan, run_doctor
from tessera.llm_bridge import LlmBridgeError, resolve_llm_fn
from tessera.legacy_compat import LegacyBackendWarning


ROOT = Path(__file__).resolve().parents[1]
LEGACY_IDENTITY_TOKENS = ("lao", "blip", "lab autonomous officer")


@pytest.mark.parametrize(
    ("explicit", "environ", "expected", "warned"),
    [
        ("/explicit", {"TESSERA_STORAGE_DIR": "/canonical", "LAO_MEM_DIR": "/legacy"}, "/explicit", False),
        (None, {"TESSERA_STORAGE_DIR": "/canonical"}, "/canonical", False),
        (None, {"TESSERA_STORAGE_DIR": "/canonical", "LAO_MEM_DIR": "/legacy"}, "/canonical", False),
        (None, {"LAO_MEM_DIR": "/legacy"}, "/legacy", True),
        (None, {}, "./memories", False),
    ],
)
def test_storage_precedence_matrix(explicit, environ, expected, warned):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert resolve_storage_dir(explicit, environ=environ) == expected
    legacy = [item for item in caught if issubclass(item.category, LegacyStorageConfigurationWarning)]
    assert bool(legacy) is warned
    assert len(legacy) <= 1


def test_existing_claude_memory_is_not_discovered_but_explicit_path_is_valid(tmp_path, monkeypatch):
    legacy_dir = tmp_path / ".claude" / "memory"
    legacy_dir.mkdir(parents=True)
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)
    plan = build_quickstart_plan(project_root=str(tmp_path))
    assert Path(plan.storage_dir) == tmp_path / "memories"
    explicit = build_quickstart_plan(project_root=str(tmp_path), storage_dir=str(legacy_dir))
    assert Path(explicit.storage_dir) == legacy_dir


def test_alias_warning_stays_off_machine_readable_stdout(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.setenv("LAO_MEM_DIR", str(tmp_path))
    result = main([
        "write", "--id", "project/json-contract", "--type", "factual",
        "--episode", "ep-95", "--content", "Machine output stays valid.", "--json",
    ])
    captured = capsys.readouterr()
    assert result == 0
    assert json.loads(captured.out)["persisted"] is True
    assert "LAO_MEM_DIR is deprecated" in captured.err


def test_help_doctor_and_quickstart_are_project_neutral(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["start", "--help"])
    help_text = capsys.readouterr().out.lower()
    report_text = json.dumps(run_doctor(str(tmp_path)).to_dict(), ensure_ascii=False).lower()
    plan_text = json.dumps(build_quickstart_plan(str(tmp_path)).to_dict(), ensure_ascii=False).lower()
    for token in LEGACY_IDENTITY_TOKENS:
        assert token not in help_text
        assert token not in report_text
        assert token not in plan_text
    assert "TESSERA_STORAGE_DIR" in json.dumps(build_quickstart_plan(str(tmp_path)).mcp_config_block)


def test_default_backend_resolution_has_no_environment_or_file_probing(monkeypatch):
    def forbidden_getenv(*_args, **_kwargs):
        raise AssertionError("provider credentials must not be inspected")
    def forbidden_is_file(*_args, **_kwargs):
        raise AssertionError("project-specific files must not be probed")
    monkeypatch.setattr("os.getenv", forbidden_getenv)
    monkeypatch.setattr(Path, "is_file", forbidden_is_file)
    assert resolve_llm_fn(return_backend_name=True) == (None, None)


def test_no_hardcoded_gateway_or_parent_router_discovery_in_generic_bridge():
    text = (ROOT / "tessera" / "llm_bridge.py").read_text(encoding="utf-8").lower()
    assert "ai-gateway-int.azure-api.net" not in text
    assert ".parents" not in text
    assert "lao_core" not in text


def test_explicit_compatibility_backend_selection_is_controlled(monkeypatch):
    monkeypatch.setattr(
        "tessera.legacy_compat.blip_gateway_llm_fn", lambda **kwargs: ("adapter", kwargs)
    )
    adapter, name = resolve_llm_fn(
        backend="legacy-blip-gateway", endpoint="https://example.invalid/chat",
        api_key="test", contact_id="contact", subscription_id="subscription",
        tenant_id="tenant", return_backend_name=True,
    )
    assert name == "legacy-blip-gateway"
    assert adapter[1]["endpoint"] == "https://example.invalid/chat"


def test_unavailable_compatibility_backend_is_actionable_and_never_echoes_prompt(tmp_path, monkeypatch):
    with pytest.raises(LlmBridgeError, match="requires explicit endpoint"):
        resolve_llm_fn(backend="legacy-blip-gateway")
    router = tmp_path / "router.py"
    router.write_text("# fixture", encoding="utf-8")
    monkeypatch.setattr(
        subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=7, stderr="offline", stdout=""),
    )
    with pytest.warns(LegacyBackendWarning):
        fn = resolve_llm_fn(backend="legacy-lao-engine-router", router_path=str(router))
    with pytest.raises(RuntimeError, match="exited 7") as exc:
        fn("system", "RAW PROMPT")
    assert str(exc.value) != "RAW PROMPT"

    fake_requests = SimpleNamespace(
        RequestException=RuntimeError,
        post=lambda *_args, **_kwargs: SimpleNamespace(status_code=503, text="offline"),
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    with pytest.warns(LegacyBackendWarning):
        gateway = resolve_llm_fn(
            backend="legacy-blip-gateway", endpoint="https://example.invalid/chat",
            api_key="test", contact_id="contact", subscription_id="subscription", tenant_id="tenant",
        )
    with pytest.raises(RuntimeError, match="HTTP 503"):
        gateway("system", "RAW PROMPT")


def test_generic_import_and_deterministic_retrieval_need_no_optional_provider(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    engine.write_memory_note(
        mem_id="research/provider-independence", mem_type="factual", episode_id="ep-95",
        content="Deterministic retrieval has no network dependency.", tags=["deterministic"], entities=[],
    )
    engine.build_index(use_cache=False)
    assert engine.retrieve_context("network dependency", top_n=1)[0]["id"] == "research/provider-independence"


def test_mcp_import_does_not_resolve_an_optional_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("TESSERA_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(
        "tessera.llm_bridge.resolve_llm_fn",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("provider resolution during import")),
    )
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
    sys.modules.pop("tessera.mcp_server", None)
    module = importlib.import_module("tessera.mcp_server")
    assert module._hook._orchestrator is None


def test_generic_foreign_frontmatter_remains_supported(tmp_path):
    (tmp_path / "foreign.md").write_text(
        "---\nname: external-learning\ndescription: Generic schema fixture\n"
        "metadata:\n  type: learning\n---\nA reusable operational lesson.\n",
        encoding="utf-8",
    )
    engine = TesseraEngine(str(tmp_path))
    engine.build_index(use_cache=False)
    assert engine.graph.nodes["foreign"]["node_type"] == "procedural_anchor"


def test_reference_inventory_allowlist_contains_only_compatibility_or_history():
    pattern = re.compile(
        r"LAO|Lab Autonomous Officer|Blip|LAO_MEM_DIR|\.claude/memory|"
        r"lao_core|engine_router|ai-gateway-int\.azure-api\.net|/lao-|lao/",
        re.IGNORECASE,
    )
    allowed_files = {
        "README.md", "CHANGELOG.md", "docs/PR_EVOLUTION_95.md",
        "docs/CODE_EXPLANATION.md", "docs/COMO-FUNCIONA-E-PROXIMOS-PASSOS.md",
        "docs/PROCEDURAL_ANCHORS.md", "docs/QUMEM-GAP-ANALYSIS.md",
        "docs/ROTEIRO-DEMO-VIDEO.md", "docs/adr/0001-core-vs-optional-llm-boundary.md",
        "docs/slides/README.md", "docs/slides/tessera-apresentacao.html",
        "docs/slides/assets/LOGO_PRIMARIA_fundo_claro.svg",
        "docs/slides/assets/LOGO_SECUNDARIA_fundo_escuro.svg",
        "docs/test-cards/112-tessera-ascii-banner.md",
        "docs/test-cards/93-storage-configuration-parity.md",
            "docs/test-cards/95-remove-legacy-runtime-coupling.md",
            "docs/PR_EVOLUTION_93.md",
            "docs/PR_EVOLUTION_117.md",
            "docs/adr/0003-configuration-and-store-discovery.md",
            "docs/test-cards/117-configuration-init-discovery.md",
            "tessera/config.py", "tessera/legacy_compat.py", "tessera/llm_bridge.py",
            "tests/test_canonical_compatibility.py", "tests/test_issue_95_runtime_boundary.py",
            "tests/test_issue_93_storage_config_parity.py",
            "tests/test_issue_117_config_init_discovery.py",
    }
    unexpected = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".codex" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if ".egg-info/" in relative:
            continue
        if relative.startswith("archive/") or relative.startswith("docs/slides/assets/mascots/"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if pattern.search(text) and relative not in allowed_files:
            unexpected.append(relative)
    assert unexpected == []
