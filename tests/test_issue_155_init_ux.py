"""Executable Test Card for Issue #155 initialization UX and parity."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tessera import cli
from tessera.config import ConfigurationResolver, ProjectConfig
from tessera.engine import TesseraEngine
from tessera.init_flow import InitRequest, build_initialization_plan


LEGACY_STORAGE_ENV = "".join(("L", "A", "O", "_MEM_DIR"))


def _write(path: Path, text: str = "# Source\n\nIssue 155 beacon.\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run_json(arguments, capsys):
    code = cli.main([*arguments, "--json"])
    captured = capsys.readouterr()
    return code, json.loads(captured.out), captured.err


def test_recommended_dry_run_is_complete_deterministic_and_zero_mutation(tmp_path, capsys):
    project = tmp_path / "project"
    readme = _write(project / "README.md")
    guide = _write(project / "docs" / "guide.md")
    optional = _write(project / "examples" / "optional.md")
    secret = _write(project / ".env", "TOKEN=secret\n")
    before = {path: path.read_bytes() for path in (readme, guide, optional, secret)}
    command = [
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive", "--dry-run",
    ]

    first_code, first, first_err = _run_json(command, capsys)
    second_code, second, second_err = _run_json(command, capsys)

    assert first_code == second_code == 0
    assert first_err == second_err == ""
    assert first == second
    plan = first["plan"]
    assert set(plan["sources"]["selected"]) == {"README.md", "docs/guide.md"}
    assert plan["sources"]["optional_count"] == 1
    assert plan["sources"]["forbidden_count"] == 1
    assert plan["planned_mutations"]["source_files"] == 0
    assert plan["source_files_modified"] == 0
    assert first["mode"] == "dry-run" and first["applied"] is False
    assert not (project / ".tessera").exists()
    assert not (project / "memories").exists()
    assert {path: path.read_bytes() for path in before} == before


def test_recommended_apply_persists_v2_then_indexes_only_selected_sources(tmp_path, capsys, monkeypatch):
    project = tmp_path / "project"
    readme = _write(project / "README.md", "# Root\n\nRoot beacon.\n")
    guide = _write(project / "docs" / "guide.md", "# Guide\n\nGuide beacon.\n")
    optional = _write(project / "examples" / "optional.md", "# Optional\n\nOptional beacon.\n")
    before = {path: path.read_bytes() for path in (readme, guide, optional)}
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv(LEGACY_STORAGE_ENV, raising=False)

    code, payload, stderr = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive",
    ], capsys)

    assert code == 0 and stderr == ""
    assert payload["applied"] is True
    config = ProjectConfig.load(project / ".tessera" / "config.yaml")
    assert config.loaded_schema_version == 2
    assert Path(config.store.path) == (project / "memories").resolve()
    assert Path(config.resolved_index().path) == (project / ".tessera" / "index").resolve()
    selection = ConfigurationResolver(cwd=project, environ={}).resolve()
    engine = TesseraEngine(configuration=selection)
    engine.build_index(use_cache=False, persist=False)
    indexed = {Path(path).resolve() for path in engine.file_registry.values()}
    assert indexed == {readme.resolve(), guide.resolve()}
    assert optional.resolve() not in indexed
    assert {path: path.read_bytes() for path in before} == before


def test_custom_directory_and_file_selection_and_forbidden_rejection(tmp_path, capsys):
    project = tmp_path / "project"
    guide = _write(project / "docs" / "guide.md")
    api = _write(project / "docs" / "api.md")
    readme = _write(project / "README.md")
    _write(project / "docs" / "private.key", "secret\n")

    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "custom", "--source", "docs", "--non-interactive",
    ], capsys)
    assert code == 0
    assert payload["plan"]["sources"]["selected"] == ["docs/api.md", "docs/guide.md"]
    indexed = {Path(path).resolve() for path in payload["result"]["indexed_sources"]}
    assert indexed == {guide.resolve(), api.resolve()}
    assert readme.resolve() not in indexed

    other = tmp_path / "other"
    _write(other / ".env", "secret\n")
    code, error, _ = _run_json([
        "init", "--project", str(other), "--store", "memories",
        "--sources", "custom", "--source", ".env", "--non-interactive",
    ], capsys)
    assert code == 2
    assert "forbidden source" in error["error"]["message"]
    assert not (other / ".tessera").exists()
    assert not (other / "memories").exists()


def test_memory_only_mode_keeps_external_project_sources_out(tmp_path, capsys, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "README.md")
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv(LEGACY_STORAGE_ENV, raising=False)

    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "generated",
        "--sources", "memory-only", "--non-interactive",
    ], capsys)
    assert code == 0
    assert payload["plan"]["sources"]["selected_count"] == 0
    selection = ConfigurationResolver(cwd=project, environ={}).resolve()
    assert len(selection.source_roots) == 1
    assert Path(selection.source_roots[0].path) == (project / "generated").resolve()
    assert payload["indexed_nodes"] == 0


def test_post_init_commands_resolve_custom_project_store_without_paths(tmp_path, capsys, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "README.md", "# Project\n\nPost init beacon.\n")
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv(LEGACY_STORAGE_ENV, raising=False)
    assert _run_json([
        "init", "--project", str(project), "--store", "knowledge/generated",
        "--sources", "recommended", "--non-interactive",
    ], capsys)[0] == 0
    monkeypatch.chdir(project)

    assert cli.main(["index", "--plain"]) == 0
    capsys.readouterr()
    assert cli.main(["query", "Post init beacon", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)
    assert cli.main(["doctor", "--plain"]) == 0
    assert str((project / "knowledge" / "generated").resolve()) in capsys.readouterr().out


def test_noninteractive_requires_explicit_source_policy_and_never_prompts(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("must not prompt"))
    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories", "--non-interactive",
    ], capsys)
    assert code == 2
    assert "requires --sources" in payload["error"]["message"]
    assert list(project.iterdir()) == []


def test_interactive_cancel_after_complete_plan_has_zero_mutation(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    source = _write(project / "README.md", "unchanged\n")
    before = source.read_bytes()
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["", "1", "no"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert cli.main(["init", "--project", str(project), "--plain"]) == 1
    output = capsys.readouterr().out
    assert "Initialization plan:" in output
    assert "cancelled" in output.lower()
    assert not (project / ".tessera").exists()
    assert not (project / "memories").exists()
    assert source.read_bytes() == before


def test_interactive_and_noninteractive_choices_build_the_same_plan(tmp_path, monkeypatch):
    project = tmp_path / "project"
    _write(project / "README.md")
    captured = {}
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    answers = iter(["", "1"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(
        cli, "_render_initialization_plan",
        lambda plan, *, dry_run: captured.update(plan=plan, dry_run=dry_run),
    )

    assert cli.main(["init", "--project", str(project), "--dry-run", "--plain"]) == 0
    scripted = build_initialization_plan(InitRequest(
        mode="project", project_root=str(project), store_path="memories",
        source_mode="recommended",
    ))
    assert captured["dry_run"] is True
    assert captured["plan"].to_dict() == scripted.to_dict()
    assert not (project / ".tessera").exists()


def test_existing_config_requires_explicit_material_update_and_noop_is_idempotent(tmp_path, capsys):
    project = tmp_path / "project"
    _write(project / "README.md")
    base = [
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive",
    ]
    assert _run_json(base, capsys)[0] == 0
    config = project / ".tessera" / "config.yaml"
    first_bytes = config.read_bytes()
    first_plan = build_initialization_plan(InitRequest(
        mode="project", project_root=str(project), store_path="memories",
        source_mode="recommended",
    ))
    assert first_plan.config_changes == ()
    assert first_plan.planned_mutations["config"] is False
    assert _run_json(base, capsys)[0] == 0
    assert config.read_bytes() == first_bytes

    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "knowledge",
        "--sources", "recommended", "--non-interactive",
    ], capsys)
    assert code == 2
    assert "--update-existing" in payload["error"]["message"]
    assert config.read_bytes() == first_bytes

    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "knowledge",
        "--sources", "recommended", "--non-interactive", "--update-existing",
    ], capsys)
    assert code == 0
    assert "change generated-memory store" in payload["plan"]["config_changes"]


def test_v1_migration_remains_store_only_unless_broadening_is_explicit(tmp_path, capsys):
    project = tmp_path / "project"
    _write(project / "memories" / "inside.md")
    _write(project / "README.md")
    config = project / ".tessera" / "config.yaml"
    _write(config, """schema_version: 1
store:
  id: 12345678-1234-4234-8234-123456789abc
  path: memories
""")

    code, payload, _ = _run_json([
        "init", "--project", str(project), "--sources", "memory-only",
        "--non-interactive", "--update-existing",
    ], capsys)
    assert code == 0
    assert "migrate configuration schema v1 to v2" in payload["plan"]["config_changes"]
    loaded = ProjectConfig.load(config)
    assert len(loaded.resolved_sources()) == 1
    assert Path(loaded.resolved_sources()[0].path) == (project / "memories").resolve()


def test_ignore_persistence_is_explicit_previewed_and_uses_canonical_discovery(tmp_path, capsys):
    project = tmp_path / "project"
    docs = _write(project / "docs" / "guide.md")
    example = _write(project / "examples" / "sample.md")

    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "custom", "--source", "docs", "--non-interactive",
    ], capsys)
    assert code == 0
    assert not (project / ".tessera-ignore").exists()
    assert docs.resolve() in {Path(path).resolve() for path in payload["result"]["indexed_sources"]}
    assert example.resolve() not in {Path(path).resolve() for path in payload["result"]["indexed_sources"]}

    code, dry, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "custom", "--source", "docs",
        "--persist-exclusion", "examples", "--non-interactive", "--dry-run",
    ], capsys)
    assert code == 0
    assert dry["plan"]["ignore"]["changes"] == ["examples/"]
    assert not (project / ".tessera-ignore").exists()

    code, applied, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "custom", "--source", "docs",
        "--persist-exclusion", "examples", "--non-interactive", "--update-existing",
    ], capsys)
    assert code == 0
    assert (project / ".tessera-ignore").read_text(encoding="utf-8") == "examples/\n"
    assert applied["result"]["ignore_applied"] is True

    code, repeated, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "custom", "--source", "docs",
        "--persist-exclusion", "examples", "--non-interactive",
    ], capsys)
    assert code == 0
    assert repeated["plan"]["ignore"]["changes"] == []
    assert repeated["plan"]["planned_mutations"]["ignore_file"] is False
    assert (project / ".tessera-ignore").read_text(encoding="utf-8") == "examples/\n"


def test_safe_ignore_reinclusion_can_be_selected_and_indexed_explicitly(tmp_path, capsys):
    project = tmp_path / "project"
    selected = _write(project / "node_modules" / "decisions.md")
    _write(project / "node_modules" / "other.md")
    _write(project / ".tessera-ignore", "node_modules/\n!node_modules/decisions.md\n")
    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "custom", "--source", "node_modules/decisions.md",
        "--non-interactive",
    ], capsys)
    assert code == 0
    assert {Path(path).resolve() for path in payload["result"]["indexed_sources"]} == {
        selected.resolve()
    }


def test_mixed_cluster_keeps_safe_child_and_excludes_forbidden_child(tmp_path, capsys):
    project = tmp_path / "project"
    safe = _write(project / "docs" / "safe.md")
    secret = _write(project / "docs" / "secret.key", "secret\n")
    before = secret.read_bytes()
    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive",
    ], capsys)
    assert code == 0
    cluster = next(item for item in payload["plan"]["discovery"]["clusters"] if item["path"] == "docs/")
    assert cluster["selectable"] is True and cluster["forbidden_count"] == 1
    assert safe.resolve() in {Path(path).resolve() for path in payload["result"]["indexed_sources"]}
    assert secret.resolve() not in {Path(path).resolve() for path in payload["result"]["indexed_sources"]}
    assert secret.read_bytes() == before


def test_outside_and_symlink_sources_fail_before_mutation(tmp_path, capsys):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside_source = _write(outside / "secret.md")
    (project / "escape").symlink_to(outside_source)
    for requested in ("../outside/secret.md", "escape"):
        code, payload, _ = _run_json([
            "init", "--project", str(project), "--store", "memories",
            "--sources", "custom", "--source", requested, "--non-interactive",
        ], capsys)
        assert code == 2
        assert payload["applied"] is False
        assert not (project / ".tessera").exists()
        assert not (project / "memories").exists()


def test_preflight_unwritable_project_fails_before_any_mutation(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "README.md")
    project.chmod(0o555)
    try:
        code, payload, _ = _run_json([
            "init", "--project", str(project), "--store", "memories",
            "--sources", "recommended", "--non-interactive", "--dry-run",
        ], capsys)
    finally:
        project.chmod(0o755)
    assert code == 2
    assert "preflight failed" in payload["error"]["message"]
    assert not (project / ".tessera").exists()


def test_index_failure_reports_truthful_partial_state_and_is_recoverable(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    source = _write(project / "README.md", "immutable\n")
    before = source.read_bytes()
    real_build = TesseraEngine.build_index
    monkeypatch.setattr(
        TesseraEngine, "build_index",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("index boom")),
    )
    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive",
    ], capsys)
    assert code == 3
    assert payload["partial_state"] == {
        "config_applied": True,
        "ignore_applied": False,
        "store_prepared": True,
        "index_applied": False,
        "source_files_modified": 0,
    }
    assert (project / ".tessera" / "config.yaml").is_file()
    assert source.read_bytes() == before

    monkeypatch.setattr(TesseraEngine, "build_index", real_build)
    code, recovered, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive",
    ], capsys)
    assert code == 0 and recovered["applied"] is True


def test_apply_failure_before_config_write_reports_partial_store_truthfully(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    source = _write(project / "README.md", "immutable\n")
    before = source.read_bytes()
    monkeypatch.setattr(
        "tessera.config.write_project_config",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("config boom")),
    )
    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", "memories",
        "--sources", "recommended", "--non-interactive",
    ], capsys)
    assert code == 3
    assert payload["partial_state"]["config_applied"] is False
    assert payload["partial_state"]["store_prepared"] is True
    assert payload["partial_state"]["source_files_modified"] == 0
    assert not (project / ".tessera" / "config.yaml").exists()
    assert source.read_bytes() == before


def test_external_generated_store_remains_distinct_from_project_sources(tmp_path, capsys):
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "README.md")
    external_store = tmp_path / "generated"
    code, payload, _ = _run_json([
        "init", "--project", str(project), "--store", str(external_store),
        "--sources", "recommended", "--non-interactive",
    ], capsys)
    assert code == 0
    loaded = ProjectConfig.load(project / ".tessera" / "config.yaml")
    assert Path(loaded.store.path) == external_store.resolve()
    assert {Path(root.path) for root in loaded.resolved_sources()} == {
        external_store.resolve(), project.resolve(),
    }
    assert payload["plan"]["store"]["path"] != payload["plan"]["index"]["path"]


def test_named_global_existing_store_is_idempotent_and_material_change_is_guarded(tmp_path, monkeypatch, capsys):
    registry_root = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(registry_root))
    first_store = tmp_path / "shared-a"
    base = [
        "init", "--global", "shared", "--store", str(first_store),
        "--non-interactive",
    ]
    assert _run_json(base, capsys)[0] == 0
    registry = registry_root / "tessera" / "registry.yaml"
    before = registry.read_bytes()
    code, repeated, _ = _run_json(base, capsys)
    assert code == 0
    assert repeated["plan"]["planned_mutations"]["config"] is False
    assert registry.read_bytes() == before

    code, blocked, _ = _run_json([
        "init", "--global", "shared", "--store", str(tmp_path / "shared-b"),
        "--non-interactive",
    ], capsys)
    assert code == 2
    assert "--update-existing" in blocked["error"]["message"]
    assert registry.read_bytes() == before
