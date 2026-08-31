"""Golden executable contract for Issue #93 storage/corpus parity."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from tessera import TesseraEngine
from tessera.config import LegacyStorageConfigurationWarning, resolve_storage_dir
from tessera.diagnostics import build_quickstart_plan, run_doctor


ROOT = Path(__file__).resolve().parents[1]
STORAGE_ENV_KEYS = ("TESSERA_STORAGE_DIR", "LAO_MEM_DIR")
GOLDEN_ID = "issue-93/golden-storage-parity"
GOLDEN_QUERY = "quartz 930126 canonical storage beacon"
GOLDEN_CONTENT = "Quartz 930126 is the canonical TESSERA storage parity beacon."


def _subprocess_env(values: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    for key in STORAGE_ENV_KEYS:
        env.pop(key, None)
    env.update(values)
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(ROOT), env.get("PYTHONPATH")) if part
    )
    return env


def _run_mcp_probe(cwd: Path, environ: dict[str, str], query: str | None = None):
    code = """
import json
from pathlib import Path
import tessera.mcp_server as server
query = %r
payload = {
    "storage_dir": str(Path(server._engine.storage_dir).resolve()),
    "provider_initialized": server._hook._orchestrator is not None,
}
if query is not None:
    payload["results"] = server.query_memories(query, top_n=3)
print(json.dumps(payload, ensure_ascii=False, default=str))
""" % query
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env=_subprocess_env(environ),
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("case", "explicit_key", "environ_keys", "expected_key", "warned"),
    [
        ("explicit", "explicit", {}, "explicit", False),
        ("canonical", None, {"TESSERA_STORAGE_DIR": "canonical"}, "canonical", False),
        (
            "canonical-over-legacy",
            None,
            {"TESSERA_STORAGE_DIR": "canonical", "LAO_MEM_DIR": "legacy"},
            "canonical",
            False,
        ),
        ("legacy", None, {"LAO_MEM_DIR": "legacy"}, "legacy", True),
        ("default", None, {}, "default", False),
        ("implicit-claude-ignored", None, {}, "default", False),
        ("explicit-claude", "claude", {}, "claude", False),
    ],
)
def test_executable_storage_resolution_matrix(
    tmp_path, monkeypatch, case, explicit_key, environ_keys, expected_key, warned
):
    project = tmp_path / "project"
    paths = {
        "explicit": tmp_path / "explicit-store",
        "canonical": tmp_path / "canonical-store",
        "legacy": tmp_path / "legacy-store",
        "default": project / "memories",
        "claude": project / ".claude" / "memory",
    }
    project.mkdir()
    paths["claude"].mkdir(parents=True)
    paths[expected_key].mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(project)
    for key in STORAGE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    environ = {key: str(paths[value]) for key, value in environ_keys.items()}
    for key, value in environ.items():
        monkeypatch.setenv(key, value)
    explicit = str(paths[explicit_key]) if explicit_key else None
    expected = paths[expected_key].resolve()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = resolve_storage_dir(explicit)
    legacy_warnings = [
        item for item in caught if issubclass(item.category, LegacyStorageConfigurationWarning)
    ]
    assert Path(resolved).resolve() == expected
    assert len(legacy_warnings) == int(warned)
    assert Path(TesseraEngine(resolved).storage_dir).resolve() == expected

    report = run_doctor(resolved)
    assert Path(report.storage_dir).resolve() == expected
    assert expected.as_posix() in json.dumps(report.to_dict(), ensure_ascii=False)

    with warnings.catch_warnings(record=True) as quickstart_caught:
        warnings.simplefilter("always")
        plan = build_quickstart_plan(project_root=str(project), storage_dir=explicit)
    quickstart_legacy_warnings = [
        item
        for item in quickstart_caught
        if issubclass(item.category, LegacyStorageConfigurationWarning)
    ]
    assert len(quickstart_legacy_warnings) == int(warned)
    assert Path(plan.storage_dir).resolve() == expected
    mcp_env = plan.mcp_config_block["mcpServers"]["tessera"]["env"]
    assert mcp_env == {"TESSERA_STORAGE_DIR": str(expected)}
    assert "LAO_MEM_DIR" not in json.dumps(plan.mcp_config_block)

    cli_args = [sys.executable, "-m", "tessera.cli", "doctor"]
    if explicit:
        cli_args.append(explicit)
    cli_args.append("--plain")
    cli = subprocess.run(
        cli_args,
        cwd=project,
        env=_subprocess_env(environ),
        check=True,
        capture_output=True,
        text=True,
    )
    assert expected.as_posix() in cli.stdout
    assert cli.stderr.count("LAO_MEM_DIR is deprecated") == int(warned)

    # MCP has no positional bootstrap path: generated configuration supplies
    # its explicit server path through the canonical environment variable.
    mcp = _run_mcp_probe(project, mcp_env)
    assert json.loads(mcp.stdout)["storage_dir"] == str(expected)
    assert "LAO_MEM_DIR is deprecated" not in mcp.stderr


@pytest.mark.parametrize(
    ("environ_keys", "expected_key", "warning_count"),
    [
        ({"TESSERA_STORAGE_DIR": "canonical"}, "canonical", 0),
        ({"TESSERA_STORAGE_DIR": "canonical", "LAO_MEM_DIR": "legacy"}, "canonical", 0),
        ({"LAO_MEM_DIR": "legacy"}, "legacy", 1),
        ({}, "default", 0),
    ],
)
def test_mcp_bootstrap_precedence_and_warning_channel(
    tmp_path, environ_keys, expected_key, warning_count
):
    project = tmp_path / "project"
    project.mkdir()
    paths = {
        "canonical": tmp_path / "canonical-store",
        "legacy": tmp_path / "legacy-store",
        "default": project / "memories",
    }
    environ = {key: str(paths[value]) for key, value in environ_keys.items()}
    completed = _run_mcp_probe(project, environ)
    payload = json.loads(completed.stdout)
    assert payload["storage_dir"] == str(paths[expected_key].resolve())
    assert payload["provider_initialized"] is False
    assert completed.stderr.count("LAO_MEM_DIR is deprecated") == warning_count


def test_index_is_strictly_contained_to_the_configured_store(tmp_path):
    storage = tmp_path / "project" / "memories"
    storage.mkdir(parents=True)
    (tmp_path / "outside.md").write_text(
        "---\nid: outside/corpus\nnode_type: factual\nepisode_id: outside\n"
        "tags: []\nentities: []\nactive_connections: []\n---\n"
        "This note is outside the configured canonical store.\n",
        encoding="utf-8",
    )
    engine = TesseraEngine(str(storage))
    engine.write_memory_note(
        mem_id=GOLDEN_ID,
        mem_type="factual",
        episode_id="issue-93",
        content=GOLDEN_CONTENT,
        tags=["storage-parity"],
        entities=[],
    )
    engine.build_index(use_cache=False)
    assert GOLDEN_ID in engine.file_registry
    assert "outside/corpus" not in engine.file_registry
    assert all(Path(path).resolve().is_relative_to(storage.resolve()) for path in engine.file_registry.values())


def test_write_once_read_everywhere_golden_contract(tmp_path, monkeypatch):
    project = tmp_path / "project"
    storage = project / "canonical-store"
    project.mkdir()
    (tmp_path / "unselected.md").write_text(
        "---\nid: outside/unselected\nnode_type: factual\nepisode_id: outside\n"
        "tags: []\nentities: []\nactive_connections: []\n---\n"
        "Quartz 930126 must never leak from outside the selected store.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TESSERA_STORAGE_DIR", str(storage))
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)

    resolved = resolve_storage_dir()
    engine = TesseraEngine(resolved)
    result = engine.write_memory_note_result(
        mem_id=GOLDEN_ID,
        mem_type="factual",
        episode_id="issue-93",
        content=GOLDEN_CONTENT,
        tags=["storage-parity", "golden"],
        entities=[],
    )
    assert result.persisted is True
    assert result.memory_id == GOLDEN_ID
    engine.build_index(use_cache=False)
    python_results = engine.retrieve_context(GOLDEN_QUERY, top_n=3)
    python_contract = json.loads(json.dumps(python_results, ensure_ascii=False, default=str))

    plan = build_quickstart_plan(project_root=str(project))
    generated_env = plan.mcp_config_block["mcpServers"]["tessera"]["env"]
    assert generated_env == {"TESSERA_STORAGE_DIR": str(storage.resolve())}

    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "tessera.cli",
            "query",
            GOLDEN_QUERY,
            "--top-n",
            "3",
            "--json",
        ],
        cwd=project,
        env=_subprocess_env(generated_env),
        check=True,
        capture_output=True,
        text=True,
    )
    cli_results = json.loads(cli.stdout)
    mcp = _run_mcp_probe(project, generated_env, GOLDEN_QUERY)
    mcp_payload = json.loads(mcp.stdout)
    mcp_results = mcp_payload["results"]

    expected_store = str(storage.resolve())
    assert Path(engine.storage_dir).resolve().as_posix() == expected_store
    assert f"storage_dir: {expected_store}" in cli.stderr
    assert mcp_payload["storage_dir"] == expected_store
    assert mcp_payload["provider_initialized"] is False
    assert mcp.stderr == ""

    assert python_contract == cli_results == mcp_results
    assert [item["id"] for item in python_contract] == [GOLDEN_ID]
    hit = python_contract[0]
    assert {
        "id",
        "score",
        "score_explain",
        "relevant_evidence",
        "evidence_info",
        "filepath",
        "provenance",
        "evidence",
    } <= hit.keys()
    assert hit["relevant_evidence"]
    assert hit["evidence"]
    assert Path(hit["filepath"]).resolve().is_relative_to(storage.resolve())
