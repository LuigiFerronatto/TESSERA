"""Acceptance coverage for Issue #13 read-only Corpus Doctor."""

from __future__ import annotations

import json
from pathlib import Path

from tessera import cli
from tessera.config import ResolvedConfiguration, SourceRootRecord
from tessera.corpus_diagnostics import run_corpus_doctor
from tessera.engine import TesseraEngine


def _configuration(project: Path) -> ResolvedConfiguration:
    store = project / "memories"
    store.mkdir(parents=True, exist_ok=True)
    return ResolvedConfiguration(
        "b6d96df8-68d2-58e9-b8ed-f444985a687c",
        str(store),
        "project_config",
        project_root=str(project),
        config_path=str(project / ".tessera" / "config.yaml"),
        source_roots=(SourceRootRecord(str(project), ("**/*.md", "**/*.txt")),),
        index_dir=str(project / ".tessera" / "index"),
        identity_root=str(project),
        config_schema_version=2,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _all_file_bytes(root: Path):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_healthy_report_is_deterministic_and_read_only(tmp_path: Path) -> None:
    project = tmp_path / "project"
    configuration = _configuration(project)
    _write(
        project / "memories" / "alpha.md",
        "---\nid: facts/alpha\nnode_type: factual\nrelated_to: [facts/beta]\n---\nAlpha.\n",
    )
    _write(
        project / "memories" / "beta.md",
        "---\nid: facts/beta\nnode_type: factual\n---\nBeta.\n",
    )
    TesseraEngine(configuration=configuration).build_index(use_cache=False)
    before = _all_file_bytes(project)

    first = run_corpus_doctor(configuration)
    second = run_corpus_doctor(configuration)

    assert first.to_dict() == second.to_dict()
    assert first.status == "healthy"
    assert first.exit_code == 0
    assert first.counts["sources_selected"] == 2
    assert first.counts["metadata_complete"] == 2
    assert first.counts["relations_resolved"] == 1
    assert first.counts["errors"] == 0
    assert first.counts["warnings"] == 0
    assert first.source_files_modified == 0
    assert _all_file_bytes(project) == before


def test_reports_parse_identity_metadata_and_relation_defects(tmp_path: Path) -> None:
    project = tmp_path / "project"
    configuration = _configuration(project)
    _write(project / "bad-yaml.md", "---\ndescription: broken: value\n---\nBody.\n")
    _write(project / "one.md", "---\nid: duplicate\nnode_type: factual\n---\nOne.\n")
    _write(
        project / "two.md",
        "---\n"
        "id: duplicate\n"
        "node_type: factual\n"
        "drawer: archive\n"
        "created_at: yesterday\n"
        "related_to: [missing]\n"
        "---\n"
        "Two.\n",
    )

    report = run_corpus_doctor(configuration)
    codes = [item.code for item in report.findings]

    assert report.status == "error"
    assert report.exit_code == 1
    assert "malformed_frontmatter" in codes
    assert "duplicate_explicit_identity" in codes
    assert "invalid_drawer" in codes
    assert "invalid_date" in codes
    assert "broken_relation" in codes
    assert "index_missing" in codes
    assert report.counts["relations_broken"] == 1
    assert report.source_files_modified == 0


def test_reports_stale_manifest_and_evidence_after_source_edit(tmp_path: Path) -> None:
    project = tmp_path / "project"
    configuration = _configuration(project)
    source = project / "memories" / "note.md"
    _write(source, "---\nid: facts/note\nnode_type: factual\n---\nOriginal.\n")
    TesseraEngine(configuration=configuration).build_index(use_cache=False)
    source.write_text(
        "---\nid: facts/note\nnode_type: factual\n---\nChanged after indexing.\n",
        encoding="utf-8",
    )

    report = run_corpus_doctor(configuration)
    codes = [item.code for item in report.findings]

    assert report.status == "warning"
    assert report.exit_code == 0
    assert "stale_source_version" in codes
    assert "stale_evidence" in codes
    assert report.counts["stale_evidence_records"] == 1


def test_no_frontmatter_and_inferred_metadata_are_counted_without_being_errors(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    configuration = _configuration(project)
    _write(project / "README.md", "# Project context\n")
    _write(project / "notes.txt", "Body-only plain text.\n")
    TesseraEngine(configuration=configuration).build_index(use_cache=False)

    report = run_corpus_doctor(configuration)

    assert report.status == "healthy"
    assert report.counts["metadata_none"] == 2
    assert report.counts["inferred_identities"] == 2
    assert report.counts["inferred_metadata_fields"] > 0


def test_cli_json_contract_and_strict_warning_exit(tmp_path: Path, monkeypatch, capsys) -> None:
    project = tmp_path / "project"
    configuration = _configuration(project)
    _write(project / "README.md", "# Project context\n")
    monkeypatch.setattr(cli, "_selection_from_args", lambda _args: configuration)

    assert cli.main(["corpus", "doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == 1
    assert payload["status"] == "warning"
    assert payload["source_files_modified"] == 0
    assert any(item["code"] == "index_missing" for item in payload["findings"])

    assert cli.main(["corpus", "doctor", "--strict", "--plain"]) == 2
    output = capsys.readouterr().out
    assert "tessera corpus doctor — warning" in output
    assert "source files modified: 0" in output


def test_symlink_escape_is_reported_and_never_followed(tmp_path: Path) -> None:
    project = tmp_path / "project"
    configuration = _configuration(project)
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    link = project / "linked.md"
    link.symlink_to(outside)

    report = run_corpus_doctor(configuration)

    assert any(item.code == "unsafe_symlink" for item in report.findings)
    assert report.status == "error"
    assert not report.sources
