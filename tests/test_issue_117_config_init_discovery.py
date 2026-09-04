"""Executable Test Card for Issue #117 configuration/init/discovery."""

from __future__ import annotations

import json
import os
import uuid
import warnings
from pathlib import Path

import pytest
import yaml

from tessera import TesseraEngine
from tessera import cli
from tessera.diagnostics import build_quickstart_plan, run_doctor
from tessera.config import (
    ConfigurationError,
    ConfigurationResolver,
    GlobalRegistry,
    LegacyStorageConfigurationWarning,
    ProjectConfig,
    StoreRecord,
    _safe_atomic_yaml_write,
    apply_init_plan,
    build_init_plan,
    discover_project_config,
    global_registry_path,
    unregister_global_store,
    write_global_registry,
    write_project_config,
)


STORE_A = "11111111-1111-4111-8111-111111111111"
STORE_B = "22222222-2222-4222-8222-222222222222"


def _project(root: Path, store: str = "memories", store_id: str = STORE_A) -> ProjectConfig:
    root.mkdir(parents=True, exist_ok=True)
    config = ProjectConfig(
        root.resolve(),
        root / ".tessera" / "config.yaml",
        StoreRecord(store_id, str((root / store).resolve())),
    )
    write_project_config(config)
    return config


def _resolver(tmp_path: Path, cwd: Path, environ=None) -> ConfigurationResolver:
    return ConfigurationResolver(
        cwd=cwd,
        home=tmp_path / "home",
        environ=environ or {},
        registry_path=tmp_path / "config" / "tessera" / "registry.yaml",
    )


def test_p0_p1_p2_and_p7_exact_precedence(tmp_path):
    project = _project(tmp_path / "project")
    nested = project.project_root / "src"
    nested.mkdir()
    registry_path = tmp_path / "registry.yaml"
    write_global_registry(GlobalRegistry(registry_path, {"research": StoreRecord(STORE_B, str(tmp_path / "global"))}))
    environ = {"TESSERA_STORAGE_DIR": str(tmp_path / "environment"), "LAO_MEM_DIR": str(tmp_path / "legacy")}
    resolver = ConfigurationResolver(cwd=nested, home=tmp_path / "home", environ=environ, registry_path=registry_path)
    assert resolver.resolve(explicit=str(tmp_path / "explicit"), global_name="research").source == "explicit"
    assert resolver.resolve(global_name="research").storage_dir == str((tmp_path / "environment").resolve())
    legacy = ConfigurationResolver(cwd=nested, home=tmp_path / "home", environ={"LAO_MEM_DIR": str(tmp_path / "legacy")}, registry_path=registry_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        selection = legacy.resolve(global_name="research")
    assert selection.source == "environment"
    assert any(issubclass(item.category, LegacyStorageConfigurationWarning) for item in caught)
    assert _resolver(tmp_path, nested).resolve().source == "project_config"


def test_p3_p4_nearest_nested_project_config_and_symlink_root(tmp_path):
    outer = _project(tmp_path / "outer", "outer-memory", STORE_A)
    inner = _project(outer.project_root / "apps" / "api", "inner-memory", STORE_B)
    cwd = inner.project_root / "src" / "deep"
    cwd.mkdir(parents=True)
    assert discover_project_config(cwd) == inner.config_path
    link = tmp_path / "linked-project"
    link.symlink_to(inner.project_root, target_is_directory=True)
    assert discover_project_config(link / "src") == inner.config_path
    selection = _resolver(tmp_path, cwd).resolve()
    assert selection.store_id == STORE_B
    assert selection.storage_dir == str((inner.project_root / "inner-memory").resolve())


def test_p5_p6_named_global_is_exact_and_missing_never_falls_back(tmp_path):
    path = tmp_path / "registry.yaml"
    research = tmp_path / "research"
    personal = tmp_path / "personal"
    write_global_registry(GlobalRegistry(path, {
        "personal": StoreRecord(STORE_A, str(personal)),
        "research": StoreRecord(STORE_B, str(research)),
    }))
    resolver = ConfigurationResolver(cwd=tmp_path / "nowhere", home=tmp_path / "home", environ={}, registry_path=path)
    selected = resolver.resolve(global_name="research")
    assert selected.registry_name == "research"
    assert selected.storage_dir == str(research.resolve())
    with pytest.raises(ConfigurationError, match="does-not-exist"):
        resolver.resolve(global_name="does-not-exist")
    assert not research.exists() and not personal.exists()


def test_p8_tty_init_shows_plan_and_confirms(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["1", "", "1", "yes"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert cli.main(["init", "--plain"]) == 0
    output = capsys.readouterr().out
    assert "Initialization plan:" in output
    assert "Store id:" in output
    assert (tmp_path / ".tessera" / "config.yaml").is_file()


def test_p9_noninteractive_missing_choice_has_no_input_or_mutation(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("input must not be called"))
    assert cli.main(["init", "--non-interactive"]) == 2
    assert "needs --project" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
    assert cli.main(["init", "--project", ".", "--store", "store", "--sources", "memory-only", "--non-interactive", "--json"]) == 0
    assert (tmp_path / ".tessera" / "config.yaml").is_file()


@pytest.mark.parametrize("kind", ["project", "registry"])
def test_p10_p11_failed_atomic_replace_keeps_previous_valid_file(tmp_path, monkeypatch, kind):
    target = tmp_path / f"{kind}.yaml"
    old = {"schema_version": 1, "old": True}
    _safe_atomic_yaml_write(target, old)
    before = target.read_bytes()
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(OSError("interrupted")))
    with pytest.raises(OSError, match="interrupted"):
        _safe_atomic_yaml_write(target, {"schema_version": 1, "new": True})
    assert target.read_bytes() == before
    assert yaml.safe_load(target.read_text()) == old


def test_p12_unregister_removes_only_metadata(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    note = store / "note.md"
    note.write_text("source memory", encoding="utf-8")
    registry_path = tmp_path / "registry.yaml"
    write_global_registry(GlobalRegistry(registry_path, {"research": StoreRecord(STORE_A, str(store))}))
    removed = unregister_global_store("research", registry_path)
    assert removed.path == str(store.resolve())
    assert GlobalRegistry.load(registry_path).stores == {}
    assert note.read_text(encoding="utf-8") == "source memory"


def test_p13_moved_store_preserves_id_and_p14_missing_is_not_recreated(tmp_path):
    registry_path = tmp_path / "registry.yaml"
    original = tmp_path / "original"
    moved = tmp_path / "moved"
    first = build_init_plan(mode="global", store_path=str(original), registry_name="research", registry_path=registry_path, id_factory=lambda: uuid.UUID(STORE_A))
    apply_init_plan(first)
    original.rename(moved)
    second = build_init_plan(mode="global", store_path=str(moved), registry_name="research", registry_path=registry_path, id_factory=lambda: uuid.UUID(STORE_B))
    assert second.store_id == STORE_A
    apply_init_plan(second)
    assert GlobalRegistry.load(registry_path).stores["research"] == StoreRecord(STORE_A, str(moved.resolve()))
    assert not original.exists()
    moved.rename(tmp_path / "deleted-elsewhere")
    assert not Path(GlobalRegistry.load(registry_path).stores["research"].path).exists()


@pytest.mark.parametrize(
    "text,match",
    [
        ("schema_version: 2\nstore: {}\n", "requires id and path"),
        ("- not\n- a\n- mapping\n", "root"),
        (f"schema_version: 1\nstore:\n  id: {STORE_A}\n", "requires id and path"),
        (f"schema_version: 1\nstore:\n  id: {STORE_A}\n  path: memories\n  api_key: secret\n", "unsupported key"),
        (f"schema_version: 1\nstore:\n  id: {STORE_A}\n  path: ../outside\n", "may not contain"),
    ],
)
def test_p15_p16_p17_closed_schema_and_invalid_path(tmp_path, text, match):
    path = tmp_path / ".tessera" / "config.yaml"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=match):
        ProjectConfig.load(path)


def test_duplicate_yaml_names_ids_and_conflicting_paths_are_rejected(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text(f"""schema_version: 1
stores:
  duplicate:
    id: {STORE_A}
    path: {tmp_path / 'a'}
  duplicate:
    id: {STORE_B}
    path: {tmp_path / 'b'}
""", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="duplicate"):
        GlobalRegistry.load(path)
    with pytest.raises(ConfigurationError, match="conflicting"):
        write_global_registry(GlobalRegistry(path, {
            "a": StoreRecord(STORE_A, str(tmp_path / "same")),
            "b": StoreRecord(STORE_B, str(tmp_path / "same")),
        }))


def test_p19_config_symlink_mutation_refused_and_storage_symlink_canonicalized(tmp_path):
    target = tmp_path / "target.yaml"
    target.write_text("unchanged", encoding="utf-8")
    link = tmp_path / "registry.yaml"
    link.symlink_to(target)
    with pytest.raises(ConfigurationError, match="symlink"):
        _safe_atomic_yaml_write(link, {"schema_version": 1, "stores": {}})
    assert target.read_text(encoding="utf-8") == "unchanged"
    valid_target = tmp_path / "valid-registry.yaml"
    write_global_registry(GlobalRegistry(valid_target, {"research": StoreRecord(STORE_A, str(tmp_path / "research"))}))
    registry_link = tmp_path / "linked-registry.yaml"
    registry_link.symlink_to(valid_target)
    with pytest.raises(ConfigurationError, match="symlink"):
        unregister_global_store("research", registry_link)
    assert "research" in GlobalRegistry.load(valid_target).stores
    real = tmp_path / "real-store"
    real.mkdir()
    store_link = tmp_path / "store-link"
    store_link.symlink_to(real, target_is_directory=True)
    selected = _resolver(tmp_path, tmp_path).resolve(explicit=str(store_link))
    assert selected.storage_dir == str(real.resolve())


def test_p20_os_paths_json_no_home_scan_and_two_stores_remain_independent(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    assert global_registry_path(platform="linux", home=home, environ={"XDG_CONFIG_HOME": str(tmp_path / "xdg")}) == (tmp_path / "xdg/tessera/registry.yaml").resolve()
    assert global_registry_path(platform="linux", home=home, environ={}) == (home / ".config/tessera/registry.yaml").resolve()
    assert global_registry_path(platform="darwin", home=home, environ={}) == (home / "Library/Application Support/tessera/registry.yaml").resolve()
    assert global_registry_path(platform="win32", home=home, environ={"APPDATA": str(tmp_path / "appdata")}) == (tmp_path / "appdata/tessera/registry.yaml").resolve()

    project = _project(tmp_path / "project")
    monkeypatch.chdir(project.project_root)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert cli.main(["config", "show", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert set(payload["storage_selection"]) == {
        "store_id", "storage_dir", "source", "project_root", "config_path",
        "registry_name", "registry_path", "sources", "index_dir",
        "identity_root", "config_schema_version",
    }

    # Discovery performs exact ancestor marker checks only; an unrelated home
    # config is beyond the explicit home boundary and cannot win.
    hidden = home / ".tessera"
    hidden.mkdir(parents=True)
    (hidden / "config.yaml").write_text("not: consulted", encoding="utf-8")
    assert discover_project_config(home / "unconfigured" / "deep", home=home) is None


def test_p22_p23_no_project_merge_and_configured_cli_reads_python_write(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)
    project = _project(tmp_path / "project")
    selected_store = Path(project.store.path)
    other_store = tmp_path / "other"
    engine = TesseraEngine(str(selected_store))
    engine.write_memory_note(
        mem_id="issue-117/configured-parity", mem_type="factual", episode_id="117",
        content="Cobalt 117 configured parity beacon", tags=["config"], entities=[],
    )
    other = TesseraEngine(str(other_store))
    other.write_memory_note(
        mem_id="issue-117/other", mem_type="factual", episode_id="117",
        content="Must remain in another store", tags=[], entities=[],
    )
    monkeypatch.chdir(project.project_root)
    assert cli.main(["query", "Cobalt 117 configured parity beacon", "--json"]) == 0
    results = json.loads(capsys.readouterr().out)
    assert [result["id"] for result in results] == ["issue-117/configured-parity"]
    assert not any(path.is_relative_to(other_store.resolve()) for path in selected_store.rglob("*.md"))


def test_dry_run_and_legacy_positional_compatibility(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["init", "legacy-store", "--dry-run", "--non-interactive", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] is False
    assert payload["plan"]["deletes"] == []
    assert not (tmp_path / "legacy-store").exists()
    assert not (tmp_path / ".tessera").exists()


def test_config_list_doctor_unregister_json_and_p24_runtime_doctor_quickstart(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    store = tmp_path / "research"
    assert cli.main([
        "init", "--global", "research", "--store", str(store),
        "--non-interactive", "--json",
    ]) == 0
    init_payload = json.loads(capsys.readouterr().out)
    assert init_payload["storage_selection"]["registry_name"] == "research"

    assert cli.main(["config", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["stores"] == [{
        "name": "research", "store_id": init_payload["storage_selection"]["store_id"],
        "storage_dir": str(store.resolve()),
    }]
    assert cli.main(["config", "doctor", "--global", "research", "--json"]) == 0
    doctor = json.loads(capsys.readouterr().out)
    assert doctor["healthy"] is True
    assert doctor["storage_selection"]["source"] == "global_registry"

    # The broader doctor remains a runtime smoke, and quickstart remains a
    # project-neutral compatibility planner that emits the canonical env var.
    assert run_doctor(str(store)).all_ok is True
    quickstart = build_quickstart_plan(project_root=str(tmp_path), storage_dir=str(store))
    assert quickstart.mcp_config_block["mcpServers"]["tessera"]["env"] == {
        "TESSERA_STORAGE_DIR": str(store.resolve())
    }

    assert cli.main(["config", "unregister", "research", "--json"]) == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["store_deleted"] is False
    assert store.is_dir()
    assert cli.main(["config", "show", "--global", "research", "--json"]) == 2
    assert "not registered" in capsys.readouterr().err
