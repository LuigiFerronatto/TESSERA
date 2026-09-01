import json
import os
from pathlib import Path

import pytest

from tessera import cli
from tessera.config import ProjectConfig, ResolvedConfiguration, SourceRootRecord
from tessera.source_discovery import (
    DEFAULT_MAX_SOURCE_BYTES,
    SourceClassification,
    SourceReason,
    discover_sources,
    discover_sources_for_configuration,
)


def _write(path: Path, text: str = "# source\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _by_path(plan):
    return {item.path: item for item in plan.files}


def _selection(root: Path, *, sources=None, index=None, schema=2):
    store = root / "memories"
    store.mkdir(exist_ok=True)
    return ResolvedConfiguration(
        store_id="12345678-1234-1234-1234-123456789abc",
        storage_dir=str(store),
        source="project_config",
        project_root=str(root),
        config_path=str(root / ".tessera" / "config.yaml"),
        source_roots=tuple(sources or (SourceRootRecord(str(store), ("**/*.md",)),)),
        index_dir=str(index or (root / ".tessera" / "index")),
        identity_root=str(root),
        config_schema_version=schema,
    )


def test_basic_discovery_root_files_clusters_and_counts(tmp_path):
    for relative in ("README.md", "AGENTS.md", "docs/a.md", "docs/b.md", "research/x.md"):
        _write(tmp_path / relative)

    plan = discover_sources(tmp_path)
    files = _by_path(plan)
    assert files["README.md"].classification == "RECOMMENDED"
    assert files["README.md"].reason == "project_entrypoint"
    assert files["AGENTS.md"].classification == "RECOMMENDED"
    clusters = {item.path: item for item in plan.clusters}
    assert clusters["docs/"].recommended_count == 2
    assert clusters["research/"].recommended_count == 1
    assert all(item.path not in {"README.md", "AGENTS.md"} for item in plan.clusters)
    assert plan.totals == {"SUPPORTED": 0, "RECOMMENDED": 5, "IGNORED": 0, "FORBIDDEN": 0}


def test_configured_memory_source_is_recommended_without_config_mutation(tmp_path):
    memory = _write(tmp_path / "custom" / "fact.md")
    selection = _selection(
        tmp_path,
        sources=(SourceRootRecord(str(tmp_path / "custom"), ("**/*.md",)),),
    )
    before = selection.to_dict()
    plan = discover_sources_for_configuration(selection)
    assert _by_path(plan)["custom/fact.md"].reason == SourceReason.CONFIGURED_SOURCE.value
    assert selection.to_dict() == before
    assert memory.read_text(encoding="utf-8") == "# source\n"


def test_only_current_markdown_ingestion_is_selectable(tmp_path):
    _write(tmp_path / "notes.md")
    _write(tmp_path / "notes.txt", "text\n")
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01")
    files = _by_path(discover_sources(tmp_path))
    assert files["notes.md"].selectable is True
    for name in ("notes.txt", "blob.bin"):
        assert files[name].classification == "IGNORED"
        assert files[name].reason == "unsupported_format"
        assert files[name].selectable is False


def test_mandatory_exclusions_and_ignore_file_cannot_be_selected(tmp_path):
    _write(tmp_path / ".git" / "config", "secret")
    _write(tmp_path / ".tessera" / "index" / "derived.md")
    _write(tmp_path / ".tessera_index" / "legacy.md")
    _write(tmp_path / ".tessera-ignore", "!.git/config\n!.tessera/index/derived.md\n")
    files = _by_path(discover_sources(tmp_path))
    assert files[".git/"].classification == "FORBIDDEN"
    assert files[".tessera/index/"].reason == "derived_index"
    assert files[".tessera_index/"].reason == "derived_index"
    assert files[".tessera-ignore"].classification == "IGNORED"
    assert files[".tessera-ignore"].reason == "ignore_file"
    assert not any(item.selectable for item in files.values() if item.path.startswith(".git"))


def test_custom_resolved_index_is_forbidden(tmp_path):
    _write(tmp_path / "derived" / "cache" / "state.md")
    selection = _selection(tmp_path, index=tmp_path / "derived" / "cache")
    files = _by_path(discover_sources(tmp_path, selection))
    assert files["derived/cache/"].classification == "FORBIDDEN"
    assert files["derived/cache/"].reason == "derived_index"


def test_convenience_exclusions_are_ignored_and_safe_reinclude_works(tmp_path):
    _write(tmp_path / "node_modules" / "package.md")
    _write(tmp_path / ".venv" / "notes.md")
    _write(tmp_path / "archive" / "old.md")
    _write(tmp_path / "archive" / "decisions.md")
    _write(tmp_path / ".tessera-ignore", "archive/\n!archive/decisions.md\n")
    files = _by_path(discover_sources(tmp_path))
    assert files["node_modules/"].reason == "recommended_exclusion"
    assert files[".venv/"].reason == "recommended_exclusion"
    assert files["archive/"].classification == "IGNORED"
    assert files["archive/old.md"].classification == "IGNORED"
    assert files["archive/decisions.md"].classification == "SUPPORTED"
    assert files["archive/decisions.md"].matched_rule == "!archive/decisions.md"


def test_ignore_subset_supports_comments_blanks_globs_question_and_double_star(tmp_path):
    for relative in ("docs/a.md", "docs/ab.md", "docs/deep/private.md", "root.log", "keep.md"):
        _write(tmp_path / relative)
    _write(
        tmp_path / ".tessera-ignore",
        "# comment\n\n*.log\ndocs/?.md\ndocs/**/private.md\n",
    )
    files = _by_path(discover_sources(tmp_path))
    assert files["root.log"].reason == "ignored_by_tessera_ignore"
    assert files["docs/a.md"].reason == "ignored_by_tessera_ignore"
    assert files["docs/ab.md"].classification == "RECOMMENDED"
    assert files["docs/deep/private.md"].reason == "ignored_by_tessera_ignore"


def test_invalid_ignore_pattern_is_diagnostic_and_scan_continues(tmp_path):
    _write(tmp_path / "README.md")
    _write(tmp_path / ".tessera-ignore", "!\n../outside\n[abc].md\n")
    plan = discover_sources(tmp_path)
    assert _by_path(plan)["README.md"].classification == "RECOMMENDED"
    assert [item.code for item in plan.warnings].count("invalid_ignore_pattern") == 3


def test_unreadable_ignore_file_is_diagnostic(tmp_path):
    ignore = _write(tmp_path / ".tessera-ignore", "archive/\n")
    ignore.chmod(0)
    try:
        plan = discover_sources(tmp_path)
    finally:
        ignore.chmod(0o600)
    assert any(item.code == "unreadable_ignore_file" for item in plan.warnings)


def test_symlinked_ignore_file_is_not_followed(tmp_path):
    outside = _write(tmp_path.parent / f"{tmp_path.name}-ignore", "archive/\n")
    (tmp_path / ".tessera-ignore").symlink_to(outside)
    plan = discover_sources(tmp_path)
    assert any(item.code == "unsafe_ignore_file" for item in plan.warnings)
    item = _by_path(plan)[".tessera-ignore"]
    assert item.classification == "FORBIDDEN"
    assert item.reason == "outside_root"


@pytest.mark.parametrize("name", ["private.pem", "private.key", "id_rsa", "id_ed25519", "credentials.json", ".env", ".env.local"])
def test_high_confidence_sensitive_artifacts_are_forbidden(tmp_path, name):
    _write(tmp_path / name, "secret")
    item = _by_path(discover_sources(tmp_path))[name]
    assert item.classification == "FORBIDDEN"
    assert item.reason == "sensitive_file"


def test_sensitive_examples_are_not_claimed_as_supported_formats(tmp_path):
    _write(tmp_path / ".env.example", "TOKEN=example")
    _write(tmp_path / "credentials.example.json", "{}")
    files = _by_path(discover_sources(tmp_path))
    assert files[".env.example"].reason == "unsupported_format"
    assert files["credentials.example.json"].reason == "unsupported_format"


def test_sensitive_directory_is_forbidden_before_ignore_override(tmp_path):
    _write(tmp_path / "secrets" / "notes.md")
    _write(tmp_path / ".tessera-ignore", "!secrets/notes.md\n")
    item = _by_path(discover_sources(tmp_path))["secrets/"]
    assert item.classification == "FORBIDDEN"
    assert item.reason == "sensitive_file"


def test_symlinks_inside_outside_and_loop_are_never_followed(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-sibling"
    outside.mkdir()
    _write(outside / "outside.md")
    _write(tmp_path / "docs" / "inside.md")
    (tmp_path / "inside-alias").symlink_to(tmp_path / "docs", target_is_directory=True)
    (tmp_path / "outside-alias").symlink_to(outside, target_is_directory=True)
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)
    files = _by_path(discover_sources(tmp_path))
    assert files["inside-alias"].reason == "unsafe_symlink"
    assert files["outside-alias"].reason == "outside_root"
    assert files["loop"].classification == "FORBIDDEN"
    assert [item.path for item in files.values()].count("docs/inside.md") == 1
    assert "outside.md" not in files


def test_oversized_markdown_is_ignored_without_content_read(tmp_path):
    path = tmp_path / "large.md"
    with path.open("wb") as handle:
        handle.truncate(DEFAULT_MAX_SOURCE_BYTES + 1)
    item = _by_path(discover_sources(tmp_path))["large.md"]
    assert item.classification == "IGNORED"
    assert item.reason == "oversized"
    assert item.size_bytes == DEFAULT_MAX_SOURCE_BYTES + 1


def test_unreadable_file_and_directory_emit_diagnostics(tmp_path):
    file_path = _write(tmp_path / "private.md")
    directory = tmp_path / "locked"
    directory.mkdir()
    file_path.chmod(0)
    directory.chmod(0)
    try:
        plan = discover_sources(tmp_path)
    finally:
        file_path.chmod(0o600)
        directory.chmod(0o700)
    files = _by_path(plan)
    assert files["private.md"].reason == "unreadable"
    assert files["locked/"].reason == "unreadable"
    assert sum(item.code == "unreadable" for item in plan.warnings) == 2


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO fixtures require mkfifo")
def test_special_files_are_forbidden(tmp_path):
    fifo = tmp_path / "events.pipe"
    os.mkfifo(fifo)
    item = _by_path(discover_sources(tmp_path))["events.pipe"]
    assert item.kind == "special"
    assert item.classification == "FORBIDDEN"
    assert item.reason == "special_file"


def test_forbidden_child_is_visible_in_cluster_summary(tmp_path):
    _write(tmp_path / "docs" / "guide.md")
    _write(tmp_path / "docs" / "private.key", "secret")
    cluster = {item.path: item for item in discover_sources(tmp_path).clusters}["docs/"]
    assert cluster.recommended_count == 1
    assert cluster.forbidden_count == 1
    assert cluster.classification == "FORBIDDEN"


def test_repeated_scan_has_identical_semantic_output_and_metrics(tmp_path):
    for index in range(50):
        _write(tmp_path / "docs" / f"{index:03d}.md")
    first = discover_sources(tmp_path).to_dict()
    second = discover_sources(tmp_path).to_dict()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["metrics"] == {
        "directories_visited": 2,
        "entries_stat": 51,
        "supported_candidates": 0,
        "recommended_candidates": 50,
        "ignored_candidates": 0,
        "forbidden_candidates": 0,
    }


def test_discovery_does_not_mutate_sources_ignore_config_or_index(tmp_path):
    source = _write(tmp_path / "docs" / "guide.md", "original\n")
    ignore = _write(tmp_path / ".tessera-ignore", "*.tmp\n")
    config = _write(tmp_path / ".tessera" / "config.yaml", "schema_version: 2\n")
    index = tmp_path / ".tessera" / "index"
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (source, ignore, config)}
    discover_sources(tmp_path)
    after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (source, ignore, config)}
    assert after == before
    assert not index.exists()


def test_scan_is_root_bounded_and_never_enumerates_sibling(tmp_path, monkeypatch):
    project = tmp_path / "project"
    sibling = tmp_path / "sibling"
    project.mkdir()
    sibling.mkdir()
    _write(project / "README.md")
    _write(sibling / "secret.md")
    visited = []
    real_scandir = os.scandir

    def recording_scandir(path):
        visited.append(Path(path).resolve())
        return real_scandir(path)

    monkeypatch.setattr("tessera.source_discovery.os.scandir", recording_scandir)
    plan = discover_sources(project)
    assert visited == [project.resolve()]
    assert all(path == project.resolve() or project.resolve() in path.parents for path in visited)
    assert "secret.md" not in _by_path(plan)


def test_schema_v2_explicit_sources_remain_unchanged(tmp_path):
    config_path = tmp_path / ".tessera" / "config.yaml"
    _write(tmp_path / "memories" / "fact.md")
    _write(tmp_path / "docs" / "guide.md")
    _write(
        config_path,
        """schema_version: 2
store:
  id: 12345678-1234-1234-1234-123456789abc
  path: memories
sources:
  roots:
    - path: memories
      include: ['**/*.md']
index:
  path: .tessera/index
""",
    )
    config = ProjectConfig.load(config_path)
    before_mapping = config.to_mapping()
    selection = _selection(tmp_path, sources=config.resolved_sources())
    plan = discover_sources(tmp_path, selection)
    assert config.to_mapping() == before_mapping
    assert len(config.resolved_sources()) == 1
    assert Path(config.resolved_sources()[0].path) == (tmp_path / "memories").resolve()
    assert _by_path(plan)["docs/guide.md"].classification == "RECOMMENDED"


def test_schema_v1_store_remains_only_configured_source(tmp_path):
    config_path = tmp_path / ".tessera" / "config.yaml"
    _write(tmp_path / "memories" / "fact.md")
    _write(tmp_path / "docs" / "guide.md")
    _write(
        config_path,
        """schema_version: 1
store:
  id: 12345678-1234-1234-1234-123456789abc
  path: memories
""",
    )
    config = ProjectConfig.load(config_path)
    assert config.loaded_schema_version == 1
    before = tuple(config.resolved_sources())
    selection = _selection(tmp_path, sources=before, schema=1)
    discover_sources(tmp_path, selection)
    assert tuple(config.resolved_sources()) == before
    assert len(before) == 1
    assert Path(before[0].path) == (tmp_path / "memories").resolve()


def test_configuration_helper_rejects_non_project_legacy_selection(tmp_path):
    selection = ResolvedConfiguration(None, str(tmp_path), "legacy_storage_dir")
    with pytest.raises(ValueError, match="project configuration root"):
        discover_sources_for_configuration(selection)


def test_config_doctor_exposes_machine_readable_discovery_plan(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)
    project = tmp_path / "project"
    _write(project / "README.md")
    _write(project / "memories" / "fact.md")
    _write(
        project / ".tessera" / "config.yaml",
        """schema_version: 2
store:
  id: 12345678-1234-1234-1234-123456789abc
  path: memories
sources:
  roots:
    - path: memories
      include: ['**/*.md']
index:
  path: .tessera/index
""",
    )
    assert cli.main(["config", "doctor", "--project", str(project), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_discovery"]["schema_version"] == 1
    assert payload["source_discovery"]["project_root"] == str(project.resolve())
    assert any(item["name"] == "source_discovery_policy" and item["ok"] for item in payload["checks"])


def test_config_doctor_rejects_invalid_ignore_contract(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("TESSERA_STORAGE_DIR", raising=False)
    monkeypatch.delenv("LAO_MEM_DIR", raising=False)
    project = tmp_path / "project"
    _write(project / "memories" / "fact.md")
    _write(project / ".tessera-ignore", "../outside\n")
    _write(
        project / ".tessera" / "config.yaml",
        """schema_version: 2
store:
  id: 12345678-1234-1234-1234-123456789abc
  path: memories
sources:
  roots:
    - path: memories
      include: ['**/*.md']
index:
  path: .tessera/index
""",
    )
    assert cli.main(["config", "doctor", "--project", str(project), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    check = next(item for item in payload["checks"] if item["name"] == "source_discovery_policy")
    assert check["ok"] is False
    assert "invalid_ignore_pattern" in check["detail"]


def test_configured_forbidden_source_is_actionable_diagnostic(tmp_path):
    _write(tmp_path / "secrets" / "notes.md")
    selection = _selection(
        tmp_path,
        sources=(SourceRootRecord(str(tmp_path / "secrets"), ("**/*.md",)),),
    )
    plan = discover_sources_for_configuration(selection)
    warning = next(item for item in plan.warnings if item.code == "configured_source_forbidden")
    assert warning.path == "secrets/"
    assert "sensitive_file" in warning.detail


def test_candidate_and_cluster_order_is_classification_then_path(tmp_path):
    _write(tmp_path / "z.md")
    _write(tmp_path / "README.md")
    _write(tmp_path / "docs" / "a.md")
    _write(tmp_path / "examples" / "b.md")
    _write(tmp_path / "archive" / "c.md")
    _write(tmp_path / "private.key", "secret")
    plan = discover_sources(tmp_path)
    priorities = {"RECOMMENDED": 0, "SUPPORTED": 1, "IGNORED": 2, "FORBIDDEN": 3}
    keys = [(priorities[SourceClassification(item.classification)], item.path.casefold()) for item in plan.files]
    assert keys == sorted(keys)
    cluster_keys = [(priorities[SourceClassification(item.classification)], item.path.casefold()) for item in plan.clusters]
    assert cluster_keys == sorted(cluster_keys)
