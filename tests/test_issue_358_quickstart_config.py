"""Quickstart must target the same project corpus as runtime configuration."""
import json

import pytest

from tessera.cli import main
from tessera.config import ConfigurationError, ConfigurationResolver, LEGACY_STORAGE_ENV
from tessera.diagnostics import apply_quickstart_plan, build_quickstart_plan


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv(LEGACY_STORAGE_ENV, raising=False)


def configure(root, store="kb/store", version=2):
    (root / ".tessera").mkdir()
    text = f"schema_version: {version}\nstore: {{id: 2d850c58-8f47-4cb9-aeec-b915c7bc93fd, path: {store}}}\n"
    if version == 2:
        text += "sources: {roots: [{path: notes, include: ['**/*.md'] }]}\nindex: {path: .tessera/custom-index}\n"
    (root / ".tessera/config.yaml").write_text(text)


@pytest.mark.parametrize("store,version", [("kb/store", 2), ("memories", 2), ("legacy", 1)])
@pytest.mark.parametrize("nested", [False, True])
def test_configured_plan_matches_runtime_and_is_read_only(tmp_path, store, version, nested):
    configure(tmp_path, store, version)
    start = tmp_path / "nested" if nested else tmp_path
    start.mkdir(exist_ok=True)
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    plan = build_quickstart_plan(str(start))
    selection = ConfigurationResolver(cwd=start).resolve()
    data = plan.to_dict()
    assert plan.storage_dir == selection.storage_dir
    assert plan.project_root == str(tmp_path)
    assert data["sources"] == selection.to_dict()["sources"]
    assert data["index_dir"] == selection.index_dir
    server = plan.mcp_config_block["mcpServers"]["tessera"]
    assert server["args"] == ["--project", str(tmp_path)]
    assert "env" not in server
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before


def test_plain_and_json_output_show_configured_boundaries(tmp_path, capsys):
    configure(tmp_path)
    for mode in ("--plain", "--json"):
        assert main(["quickstart", "--project-root", str(tmp_path), mode]) == 0
        output = capsys.readouterr().out
        assert str(tmp_path / "kb/store") in output
        assert str(tmp_path / "notes") in output
        assert str(tmp_path / ".tessera/custom-index") in output
        assert "TESSERA_STORAGE_DIR" not in output
        if mode == "--json":
            json.loads(output)


def test_no_config_plan_preserves_legacy_shape(tmp_path):
    plan = build_quickstart_plan(str(tmp_path))
    assert plan.storage_dir == str(tmp_path / "memories")
    assert set(plan.to_dict()) == {"storage_dir", "project_root", "detected_project_type", "mcp_config_block", "actions_taken"}
    assert plan.mcp_config_block["mcpServers"]["tessera"]["env"] == {"TESSERA_STORAGE_DIR": str(tmp_path / "memories")}


@pytest.mark.parametrize("override", ["explicit", "canonical", "legacy"])
def test_config_precedence_matches_resolver(tmp_path, monkeypatch, override):
    configure(tmp_path)
    other = str(tmp_path / "override")
    kwargs = {}
    if override == "explicit":
        kwargs["storage_dir"] = other
    elif override == "canonical":
        monkeypatch.setenv("TESSERA_STORAGE_DIR", other)
    else:
        monkeypatch.setenv(LEGACY_STORAGE_ENV, other)
    plan = build_quickstart_plan(str(tmp_path), **kwargs)
    selection = ConfigurationResolver(cwd=tmp_path).resolve(explicit=kwargs.get("storage_dir"))
    assert plan.storage_dir == selection.storage_dir
    if override == "legacy":
        assert "env" not in plan.mcp_config_block["mcpServers"]["tessera"]


def test_invalid_config_is_not_silently_replaced(tmp_path):
    configure(tmp_path)
    (tmp_path / ".tessera/config.yaml").write_text("schema_version: invalid\n")
    with pytest.raises(ConfigurationError):
        build_quickstart_plan(str(tmp_path))


def test_apply_indexes_configured_sources_without_mutating_them(tmp_path):
    configure(tmp_path)
    notes = tmp_path / "notes"
    notes.mkdir()
    note = notes / "one.md"
    content = "---\nid: sample\ntitle: Sample\n---\n\nA useful memory.\n"
    note.write_text(content)
    config = (tmp_path / ".tessera/config.yaml").read_bytes()
    plan = apply_quickstart_plan(build_quickstart_plan(str(tmp_path)))
    assert "1 nodes" in plan.actions_taken[-1]
    assert (tmp_path / ".tessera/custom-index").is_dir()
    assert not (tmp_path / "kb/store/.tessera_index").exists()
    assert note.read_text() == content
    assert (tmp_path / ".tessera/config.yaml").read_bytes() == config
