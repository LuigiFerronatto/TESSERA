"""Executable Test Card for Issue #153 store/source/index separation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tessera import TesseraEngine
from tessera import cli
from tessera.config import (
    apply_init_plan,
    build_init_plan,
    ConfigurationError,
    ConfigurationResolver,
    PROJECT_SCHEMA_VERSION,
    ProjectConfig,
    SourceRootRecord,
    StoreRecord,
    write_project_config,
)


ROOT = Path(__file__).resolve().parents[1]
STORE_ID = "3fdde7d1-deb7-4937-856a-a65cb6afeda7"
QUERY = "cobalt configuration boundary beacon"


def _write_v2(project: Path, roots=None) -> ProjectConfig:
    project.mkdir(parents=True, exist_ok=True)
    store = project / "memories"
    store.mkdir(exist_ok=True)
    config = ProjectConfig(
        project,
        project / ".tessera" / "config.yaml",
        StoreRecord(STORE_ID, str(store.resolve())),
        tuple(roots or (SourceRootRecord(str(project), (
            "README.md", "docs/**/*.md", "research/**/*.md", "memories/**/*.md",
        )),)),
    )
    write_project_config(config)
    return ProjectConfig.load(config.config_path)


def _clear_storage_env(monkeypatch) -> None:
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)


def test_v2_indexes_explicit_project_sources_and_writes_only_to_store(tmp_path, monkeypatch):
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    (project / "research").mkdir()
    readme = project / "README.md"
    guide = project / "docs" / "guide.md"
    research = project / "research" / "finding.md"
    readme.write_text(f"# README\n\n{QUERY}\n", encoding="utf-8")
    guide.write_text("# Guide\n\nConfigured docs source.\n", encoding="utf-8")
    research.write_text("# Finding\n\nConfigured research source.\n", encoding="utf-8")
    config = _write_v2(project)
    _clear_storage_env(monkeypatch)
    selection = ConfigurationResolver(cwd=project).resolve()

    assert selection.config_schema_version == PROJECT_SCHEMA_VERSION
    assert selection.storage_dir == str((project / "memories").resolve())
    assert selection.index_dir == str((project / ".tessera" / "index").resolve())
    engine = TesseraEngine(configuration=selection)
    before = {path: path.read_bytes() for path in (readme, guide, research)}
    engine.write_memory_note(
        "issue-153/generated", "factual", "153", "Generated durable memory.", [], []
    )
    engine.build_index(use_cache=False)

    assert {"README", "docs/guide", "research/finding", "issue-153/generated"} <= set(engine.file_registry)
    assert Path(engine.file_registry["issue-153/generated"]).is_relative_to(project / "memories")
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not any(path.is_relative_to(project / "memories") for path in (readme, guide, research))


def test_read_only_sources_work_with_writable_store(tmp_path, monkeypatch):
    project = tmp_path / "project"
    source = project / "docs"
    source.mkdir(parents=True)
    note = source / "readonly.md"
    note.write_text(f"# Read only\n\n{QUERY}\n", encoding="utf-8")
    config = _write_v2(
        project,
        roots=(
            SourceRootRecord(str(source), ("**/*.md",)),
            SourceRootRecord(str(project / "memories"), ("**/*.md",)),
        ),
    )
    _clear_storage_env(monkeypatch)
    original = note.read_bytes()
    source.chmod(0o555)
    note.chmod(0o444)
    try:
        selection = ConfigurationResolver(cwd=project).resolve()
        engine = TesseraEngine(configuration=selection)
        engine.build_index(use_cache=False)
        result = engine.write_memory_note_result(
            "issue-153/writable", "factual", "153", "Writable store beacon.", [], []
        )
        assert result.persisted is True
        assert Path(result.filepath).is_relative_to(project / "memories")
        assert note.read_bytes() == original
    finally:
        note.chmod(0o644)
        source.chmod(0o755)


def test_index_is_disposable_rebuildable_and_never_a_source(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text(f"# Beacon\n\n{QUERY}\n", encoding="utf-8")
    _write_v2(project)
    _clear_storage_env(monkeypatch)
    selection = ConfigurationResolver(cwd=project).resolve()
    first = TesseraEngine(configuration=selection)
    first.build_index(use_cache=False)
    before = first.retrieve_context_contract(QUERY, top_n=3)
    index = Path(selection.index_dir)
    assert (index / "graph.pkl").is_file()
    synthetic = index / "must-not-index.md"
    synthetic.write_text(f"# Derived\n\n{QUERY}\n", encoding="utf-8")

    for child in sorted(index.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    index.rmdir()
    rebuilt = TesseraEngine(configuration=selection)
    rebuilt.build_index(use_cache=True)
    after = rebuilt.retrieve_context_contract(QUERY, top_n=3)
    assert before == after
    assert "must-not-index" not in rebuilt.file_registry
    assert (index / "evidence.json").is_file()


def test_source_root_traversal_and_symlink_escape_fail_safely(tmp_path, monkeypatch):
    project = tmp_path / "project"
    config_dir = project / ".tessera"
    config_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("must remain outside", encoding="utf-8")
    config = config_dir / "config.yaml"
    config.write_text(
        f"""schema_version: 2
store:
  id: {STORE_ID}
  path: memories
sources:
  roots:
    - path: ../outside
      include: ["**/*.md"]
index:
  path: .tessera/index
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="may not contain"):
        ProjectConfig.load(config)

    link = project / "linked-outside"
    link.symlink_to(outside, target_is_directory=True)
    config.write_text(
        f"""schema_version: 2
store:
  id: {STORE_ID}
  path: memories
sources:
  roots:
    - path: linked-outside
      include: ["**/*.md"]
index:
  path: .tessera/index
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="escapes"):
        ProjectConfig.load(config)

    link.unlink()
    docs = project / "docs"
    docs.mkdir()
    (docs / "secret-link.md").symlink_to(outside / "secret.md")
    loaded = _write_v2(
        project, roots=(SourceRootRecord(str(docs), ("**/*.md",)),)
    )
    _clear_storage_env(monkeypatch)
    selection = ConfigurationResolver(cwd=loaded.project_root).resolve()
    with pytest.raises(ValueError, match="escapes its root through a symlink"):
        TesseraEngine(configuration=selection).build_index(use_cache=False)


def test_index_path_cannot_be_inside_the_writable_store(tmp_path):
    project = tmp_path / "project"
    config = _write_v2(project)
    mapping = config.to_mapping()
    mapping["index"]["path"] = "memories/derived"
    config.config_path.write_text(
        yaml.safe_dump(mapping, sort_keys=False), encoding="utf-8"
    )
    with pytest.raises(ConfigurationError, match="outside store.path"):
        ProjectConfig.load(config.config_path)


def test_named_global_store_never_absorbs_current_project_sources(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text(f"# Project\n\n{QUERY}\n", encoding="utf-8")
    global_store = tmp_path / "global-store"
    global_store.mkdir()
    (global_store / "global.md").write_text("# Global\n\nGlobal-only beacon.\n", encoding="utf-8")
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        f"""schema_version: 1
stores:
  shared:
    id: {STORE_ID}
    path: {global_store}
""",
        encoding="utf-8",
    )
    _clear_storage_env(monkeypatch)
    selection = ConfigurationResolver(cwd=project, registry_path=registry).resolve(global_name="shared")
    engine = TesseraEngine(configuration=selection)
    engine.build_index(use_cache=False)
    assert set(engine.file_registry) == {"global"}
    assert str(project.resolve()) not in json.dumps(engine.file_registry)


def test_schema_v1_migrates_conservatively_without_broadening(tmp_path, monkeypatch):
    project = tmp_path / "project"
    store = project / "memories"
    store.mkdir(parents=True)
    (store / "inside.md").write_text(f"# Inside\n\n{QUERY}\n", encoding="utf-8")
    (project / "README.md").write_text(f"# Outside\n\n{QUERY}\n", encoding="utf-8")
    config = project / ".tessera" / "config.yaml"
    config.parent.mkdir()
    config.write_text(
        f"schema_version: 1\nstore:\n  id: {STORE_ID}\n  path: memories\n",
        encoding="utf-8",
    )
    _clear_storage_env(monkeypatch)
    selection = ConfigurationResolver(cwd=project).resolve()
    engine = TesseraEngine(configuration=selection)
    engine.build_index(use_cache=False)
    before = engine.retrieve_context_contract(QUERY, top_n=3)
    assert selection.config_schema_version == 1
    assert selection.index_dir == str((project / ".tessera" / "index").resolve())
    assert set(engine.file_registry) == {"inside"}
    assert "README" not in engine.file_registry

    plan = build_init_plan(
        mode="project", store_path=None, project_root=str(project)
    )
    apply_init_plan(plan)
    migrated = ProjectConfig.load(config)
    assert migrated.loaded_schema_version == 2
    assert migrated.resolved_sources() == (SourceRootRecord(str(store.resolve()), ("**/*.md",)),)
    reloaded = TesseraEngine(configuration=ConfigurationResolver(cwd=project).resolve())
    reloaded.build_index(use_cache=False)
    assert reloaded.retrieve_context_contract(QUERY, top_n=3) == before


def test_legacy_and_v1_resolved_configuration_hold_retrieval_constant(tmp_path, monkeypatch):
    project = tmp_path / "project"
    store = project / "memories"
    store.mkdir(parents=True)
    excluded = store / "node_modules" / "dependency.md"
    excluded.parent.mkdir()
    excluded.write_text(f"# Dependency\n\n{QUERY}\n", encoding="utf-8")
    config = project / ".tessera" / "config.yaml"
    config.parent.mkdir()
    config.write_text(
        f"schema_version: 1\nstore:\n  id: {STORE_ID}\n  path: memories\n",
        encoding="utf-8",
    )
    legacy = TesseraEngine(storage_dir=str(store))
    legacy.write_memory_note(
        "issue-153/constant", "factual", "153", f"Generated {QUERY}.", [], []
    )
    legacy.build_index(use_cache=False)
    assert "Dependency" not in legacy.file_registry
    expected = legacy.retrieve_context_contract(QUERY, top_n=3)

    _clear_storage_env(monkeypatch)
    resolved = TesseraEngine(configuration=ConfigurationResolver(cwd=project).resolve())
    resolved.build_index(use_cache=False)
    assert "Dependency" not in resolved.file_registry
    assert resolved.retrieve_context_contract(QUERY, top_n=3) == expected


def test_python_cli_and_mcp_use_the_same_v2_sources(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text(f"# Shared\n\n{QUERY}\n", encoding="utf-8")
    _write_v2(project)
    _clear_storage_env(monkeypatch)
    monkeypatch.chdir(project)
    selection = ConfigurationResolver(cwd=project).resolve()
    python_engine = TesseraEngine(configuration=selection)
    python_engine.build_index(use_cache=False)
    expected = json.loads(json.dumps(
        python_engine.retrieve_context_contract(QUERY, top_n=3), default=str
    ))

    assert cli.main(["query", QUERY, "--top-n", "3", "--json"]) == 0
    cli_results = json.loads(capsys.readouterr().out)

    code = f"""
import json, sys, types
class FastMCP:
    def __init__(self, _name): pass
    @staticmethod
    def tool(): return lambda function: function
    @staticmethod
    def resource(_uri): return lambda function: function
fast = types.ModuleType('mcp.server.fastmcp'); fast.FastMCP = FastMCP
server = types.ModuleType('mcp.server'); server.fastmcp = fast
mcp = types.ModuleType('mcp'); mcp.server = server
sys.modules.update({{'mcp': mcp, 'mcp.server': server, 'mcp.server.fastmcp': fast}})
import tessera.mcp_server as tessera_mcp
print(json.dumps(tessera_mcp.query_memories({QUERY!r}, top_n=3), default=str))
"""
    env = os.environ.copy()
    env.pop("TESSERA_STORAGE_DIR", None)
    env.pop("LAO_MEM_DIR", None)
    env["PYTHONPATH"] = os.pathsep.join((str(ROOT), env.get("PYTHONPATH", "")))
    completed = subprocess.run(
        [sys.executable, "-c", code], cwd=project, env=env,
        check=True, capture_output=True, text=True,
    )
    assert json.loads(completed.stdout) == expected == cli_results
