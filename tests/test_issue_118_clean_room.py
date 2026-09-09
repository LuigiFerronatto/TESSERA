"""Regressions first reproduced using #118's installed console executable."""
import json
from pathlib import Path

import pytest

from tessera import cli
from tessera.config import ConfigurationResolver
from tessera.source_discovery import discover_sources


def invoke(args, capsys):
    code = cli.main([*args, "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_global_repeat_keeps_accepted_store_inside_configured_project(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Local\n\nOnly project knowledge.\n")
    monkeypatch.chdir(project)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert invoke(["init", "--project", ".", "--store", "generated",
                   "--sources", "recommended", "--non-interactive"], capsys)[0] == 0
    local_before = {str(p): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    global_store = tmp_path / "shared"
    args = ["init", "--global", "shared", "--store", str(global_store), "--non-interactive"]
    code, first = invoke(args, capsys)
    assert code == 0
    registry = tmp_path / "xdg/tessera/registry.yaml"
    registry_before = registry.read_bytes()
    code, repeated = invoke(args, capsys)
    assert code == 0
    assert repeated["result"]["storage_selection"] == first["result"]["storage_selection"]
    assert repeated["result"]["indexed_sources"] == []
    assert repeated["result"]["config_applied"] is False
    assert registry.read_bytes() == registry_before
    assert {str(p): p.read_bytes() for p in project.rglob("*") if p.is_file()} == local_before


@pytest.mark.skipif(__import__("os").name == "nt", reason="requires symlink support")
def test_unselected_alias_does_not_poison_configured_source_diagnostics(tmp_path, capsys):
    (tmp_path / "README.md").write_text("# Aster\n\nProject calibration.\n")
    alias = tmp_path / "unselected-alias.md"
    alias.symlink_to(tmp_path / "README.md")
    args = ["init", "--project", str(tmp_path), "--store", "generated",
            "--sources", "recommended", "--non-interactive"]
    code, first = invoke(args, capsys)
    assert code == 0
    selected = ConfigurationResolver(cwd=tmp_path, environ={}).resolve()
    discovery = discover_sources(tmp_path, selected)
    assert not [w for w in discovery.warnings if w.code == "configured_source_forbidden"]
    assert next(f for f in discovery.files if f.path == alias.name).classification == "FORBIDDEN"
    assert invoke(["config", "doctor", "--project", str(tmp_path)], capsys)[0] == 0
    code, repeated = invoke(args, capsys)
    assert code == 0
    assert repeated["plan"]["config_changes"] == []
    assert first["result"]["indexed_sources"] == repeated["result"]["indexed_sources"] == [str(tmp_path / "README.md")]

    # An explicitly configured alias must still report a forbidden source.
    from dataclasses import replace
    from tessera.config import SourceRootRecord
    explicit_alias = replace(selected, source_roots=(SourceRootRecord(str(tmp_path), (alias.name,)),))
    assert any(w.code == "configured_source_forbidden"
               for w in discover_sources(tmp_path, explicit_alias).warnings)
