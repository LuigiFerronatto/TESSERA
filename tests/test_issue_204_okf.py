"""Bounded OKF interoperability; import is candidate-only, never admission."""
import copy
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest
import yaml

from tessera.canonical import parse_and_normalize
from tessera.engine import TesseraEngine
from tessera.okf import (
    EXTENSION, SPEC_REVISION, ExchangeError, ExchangeRecord, export_records,
    knowledge_signals, main, native_preview, plan_import, plan_native_export,
)

FIXTURE = Path(__file__).parent / "fixtures" / "okf_v02"
NATIVE = Path(__file__).parent / "fixtures" / "okf_native"


def write_plan(root, files):
    for path, text in files.items():
        out = root / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")


def concept(tmp_path, fields=None, body="Body\n"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    fm = {"type": "Unknown Type", "resource": "urn:test:one", **(fields or {})}
    (tmp_path / "one.md").write_text("---\n" + yaml.safe_dump(fm) + "---\n" + body)
    return tmp_path


def test_frozen_roundtrip_preserves_every_canonical_field_and_body(tmp_path):
    original = {p: p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()}
    first = plan_import(FIXTURE, namespace="frozen")
    assert first.report["accepted_candidates"] == 10
    assert first.report["external_format"] == "PASS"
    assert first.report["mapping"] == "PASS"
    exported = export_records(first.records, auxiliary=first.auxiliary)
    write_plan(tmp_path, exported["files"])
    second = plan_import(tmp_path, namespace="frozen")
    assert second.report["external_format"] == "PASS"
    assert second.report["accepted_candidates"] == 10
    assert [r.to_dict() for r in first.records] == [r.to_dict() for r in second.records]
    assert exported == export_records(second.records, auxiliary=second.auxiliary)
    assert original == {p: p.read_bytes() for p in original}
    assert sum(len(r.canonical.relations) for r in first.records) == 3


def test_native_roundtrip_preserves_typed_relations_temporal_scope_quality_provenance(tmp_path):
    export = plan_native_export(NATIVE)
    write_plan(tmp_path, export["files"])
    imported = plan_import(tmp_path, namespace="native")
    raw = (NATIVE / "database.md").read_text()
    expected = parse_and_normalize(raw, str(NATIVE / "database.md"), str(NATIVE))
    expected.temporal.indexed_at = ""
    actual = imported.records[0].canonical
    assert actual.to_dict() == expected.to_dict()
    assert {r.type for r in actual.relations} == {"supersedes", "conflicts_with", "derived_from"}
    assert actual.temporal.valid_until == "2027-09-01T00:00:00Z"
    assert actual.source.document_hash == expected.source.document_hash


def test_generation_staleness_lifecycle_never_become_truth_timestamps_or_authority():
    plan = plan_import(FIXTURE, namespace="temporal")
    for record in plan.records:
        assert record.canonical.temporal.observed_at is None
        assert record.canonical.temporal.valid_until is None
        assert record.canonical.temporal.recorded_at is None
        assert record.canonical.quality.authority is None
    signals = {r.path: r.to_dict()["okf_signals"] for r in plan.records}
    assert signals["concepts/human.md"]["trust_tier"] == "human-reviewed"
    assert len(signals["concepts/human.md"]["verified"]) == 1
    assert signals["concepts/machine.md"]["trust_tier"] == "machine-confirmed"
    assert signals["concepts/database-old.md"]["status"] == "deprecated"


def test_unknown_extensions_and_timestamp_lexemes_survive(tmp_path):
    plan = plan_import(FIXTURE, namespace="unknown")
    record = next(r for r in plan.records if "unknown.md" in r.path)
    assert record.external_frontmatter["producer_extension"]["labels"] == ["on", "yes"]
    files = export_records(plan.records)["files"]
    write_plan(tmp_path, files)
    text = (tmp_path / "concepts/freshness.md").read_text()
    assert "2026-10-01T00:00:00+00:00" in text
    assert plan_import(tmp_path, namespace="unknown").records[0].canonical.temporal.observed_at is None


def test_resource_identity_survives_rename_but_collisions_require_review(tmp_path):
    root = concept(tmp_path)
    before = plan_import(root, namespace="same").records[0]
    (root / "one.md").rename(root / "renamed.md")
    after = plan_import(root, namespace="same").records[0]
    assert before.canonical.identity.id == after.canonical.identity.id
    assert before.canonical.source.document_id == after.canonical.source.document_id
    assert before.canonical.source.path != after.canonical.source.path
    shutil.copy(root / "renamed.md", root / "duplicate.md")
    collision = plan_import(root, namespace="same")
    assert not collision.records
    assert collision.report["external_format"] == "PASS"
    assert collision.report["review_required"] == 2


def test_namespace_scopes_external_identities(tmp_path):
    root = concept(tmp_path)
    a = plan_import(root, namespace="one").records[0]
    b = plan_import(root, namespace="two").records[0]
    assert a.canonical.identity.id != b.canonical.identity.id


def test_missing_identity_is_valid_okf_but_not_silently_path_identified(tmp_path):
    concept(tmp_path, {"resource": None})
    plan = plan_import(tmp_path, namespace="missing")
    assert plan.report["external_format"] == "PASS"
    assert plan.report["mapping"] == "REVIEW"
    assert not plan.records


@pytest.mark.parametrize("timestamp", ["2026-09-01", "2026-09-01T00:00:00", "bad", 42])
def test_ambiguous_timestamps_diagnosed_not_guessed(tmp_path, timestamp):
    concept(tmp_path, {"stale_after": timestamp})
    plan = plan_import(tmp_path, namespace="time")
    assert plan.report["accepted_candidates"] == 1
    assert any(d["code"] == "timestamp_requires_offset" for d in plan.report["diagnostics"])
    assert plan.records[0].canonical.temporal.valid_until is None


@pytest.mark.parametrize("target", ["../outside.md", "%2e%2e/outside.md", "/../outside.md", "..\\outside.md"])
def test_escaping_paths_require_review_without_reading(tmp_path, target):
    root = concept(tmp_path / "bundle", body=f"[escape]({target})\n")
    (tmp_path / "outside.md").write_text("Never read this")
    plan = plan_import(root, namespace="security")
    assert plan.report["mapping"] == "REVIEW"
    assert not plan.records


@pytest.mark.parametrize("field", ["resource", "attester", "executor", "computation", "sources"])
def test_path_valued_fields_never_escape(tmp_path, field):
    value = "../outside.py"
    if field in {"attester", "executor"}:
        value = {"resource": value}
    elif field == "sources":
        value = [{"resource": value}]
    concept(tmp_path, {field: value})
    assert plan_import(tmp_path, namespace="paths").report["mapping"] == "REVIEW"


def test_symlinks_special_files_binary_and_large_input_are_not_ingested(tmp_path):
    root = concept(tmp_path / "bundle")
    (root / "symlink.md").symlink_to(tmp_path / "outside.md")
    (root / "directory-link").symlink_to(tmp_path, target_is_directory=True)
    (root / "binary.md").write_bytes(b"\x00binary")
    (root / "large.md").write_bytes(b"a" * (1024 * 1024 + 1))
    plan = plan_import(root, namespace="security")
    assert plan.report["security"] == "FAIL"
    assert plan.report["mapping"] == "REVIEW"
    assert plan.report["accepted_candidates"] == 1


def test_no_network_execution_or_source_mutation(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No network or executable is permitted")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    root = concept(tmp_path, {"type": "Attested Computation", "executor": {"resource": "run.py"}, "attester": {"resource": "https://example.invalid/attest"}})
    (root / "run.py").write_text("raise RuntimeError('must never execute')")
    before = {p: p.read_bytes() for p in root.iterdir()}
    plan = plan_import(root, namespace="inert")
    assert plan.report["execution"] == "DISABLED"
    assert plan.report["skipped"] == [{"path": "run.py", "reason": "non_markdown_not_read"}]
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("frontmatter", ["type: Concept\ntype: Other", "type: [Concept]", "type: !unsafe value", "type: Concept\nx: &x [*x]"])
def test_invalid_or_ambiguous_yaml_diagnosed(tmp_path, frontmatter):
    (tmp_path / "one.md").write_text("---\n" + frontmatter + "\n---\nbody")
    plan = plan_import(tmp_path, namespace="invalid")
    assert plan.report["external_format"] == "FAIL"
    assert not plan.records


def test_extension_hash_mismatch_unknown_version_and_namespace_collision(tmp_path):
    for index, change in enumerate(("body", "version", "profile")):
        root = tmp_path / change
        exported = plan_native_export(NATIVE)["files"]
        text = exported["database.md"]
        if change == "body":
            text += "Tampered body\n"
        elif change == "version":
            text = text.replace("schema_version: 1", "schema_version: 9")
        else:
            text = text.replace("profile: tessera-canonical-v1", "profile: unknown")
        write_plan(root, {"database.md": text})
        plan = plan_import(root, namespace="bad-extension")
        assert plan.report["external_format"] == "PASS"
        assert plan.report["mapping"] == "REVIEW"


def test_unknown_extension_members_roundtrip(tmp_path):
    plan = plan_import(FIXTURE, namespace="future")
    plan.records[0].extension_extra = {"future": {"do_not_lose": True}}
    exported = export_records(plan.records)
    write_plan(tmp_path, exported["files"])
    assert plan_import(tmp_path, namespace="future").records[0].extension_extra == {"future": {"do_not_lose": True}}


def test_export_rejects_unsafe_reserved_duplicate_paths():
    record = plan_import(FIXTURE, namespace="export").records[0]
    for path in ("../escape.md", "/absolute.md", "index.md", "a.txt"):
        candidate = copy.deepcopy(record)
        candidate.path = path
        with pytest.raises(ExchangeError):
            export_records([candidate])
    with pytest.raises(ExchangeError):
        export_records([record, record])


def test_cli_json_determinism_namespace_and_no_persistence(capsys):
    assert main(["plan", str(FIXTURE), "--namespace", "cli"]) == 0
    first = capsys.readouterr().out
    assert main(["plan", str(FIXTURE), "--namespace", "cli"]) == 0
    assert first == capsys.readouterr().out
    assert json.loads(first)["report"]["spec_revision"] == SPEC_REVISION
    assert main(["plan", str(FIXTURE)]) == 2
    assert "explicit --namespace" in capsys.readouterr().out


def test_current_engine_retrieves_projected_synthetic_candidates_with_evidence(tmp_path):
    plan = plan_import(FIXTURE, namespace="retrieval")
    # Test-only materialization of synthetic input. Product import does not
    # write source files or bypass the existing Engine admission/write gate.
    write_plan(tmp_path, {r.path: native_preview(r) for r in plan.records})
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.build_index(use_cache=False)
    hits = engine.retrieve_context("primary database Cedar", top_n=3)
    current = next(r for r in plan.records if r.path.endswith("database-current.md"))
    hit = next(h for h in hits if h["id"] == current.canonical.identity.id)
    assert hit["provenance"]["source"]["document_hash"]
    assert "Cedar" in hit["relevant_evidence"]
    assert hit["evidence"]["source"]["content_hash"]
    assert hit["frontmatter"]["okf_exchange_provenance"]["source"]["document_hash"] == current.canonical.source.document_hash


def test_changed_outer_metadata_does_not_silently_restore_stale_canonical(tmp_path):
    export = plan_native_export(NATIVE)
    text = export["files"]["database.md"].replace("title: Primary database", "title: Changed title")
    write_plan(tmp_path, {"database.md": text})
    plan = plan_import(tmp_path, namespace="changed")
    assert plan.report["external_format"] == "PASS"
    assert plan.report["mapping"] == "REVIEW"
    assert not plan.records


def test_frozen_experiment_with_independent_upstream_validator():
    import importlib.util
    path = Path(__file__).resolve().parents[1] / "benchmarks/okf_roundtrip/run.py"
    spec = importlib.util.spec_from_file_location("okf_experiment", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run()
    assert result["external_concept_validation"] == {"input": 10, "exported": 10, "native_exported": 1}
    assert all(value == "PASS" for value in result["matrix"].values())
    frozen = json.loads((path.parent / "result.json").read_text())
    assert result["input_hashes"] == frozen["input_hashes"]
    assert result["export_hashes"] == frozen["export_hashes"]


def test_code_examples_do_not_invent_relations_and_complex_links_require_review(tmp_path):
    root = concept(tmp_path, body='```markdown\n[not an edge](/missing.md)\n```\n`[also not an edge](/missing.md)`\n')
    plan = plan_import(root, namespace="code")
    assert plan.report["mapping"] == "PASS"
    assert not plan.records[0].canonical.relations
    assert not any(d["code"] == "unresolved_link" for d in plan.report["diagnostics"])
    for body in ('[link][ref]\n\n[ref]: /missing.md\n', '[link](/missing.md "title")\n'):
        concept(root, body=body)
        assert plan_import(root, namespace="complex").report["mapping"] == "REVIEW"


def test_optional_lineage_field_can_be_absent_without_changing_legacy_profile(monkeypatch):
    import tessera.okf as adapter
    from dataclasses import field, make_dataclass
    payload=adapter._canonical_payload(plan_import(FIXTURE,namespace='optional').records[0].canonical)
    extended=make_dataclass('ExtendedCanonicalMetadata',[('lineage',object,field(default=None))],bases=(adapter.CanonicalMetadata,))
    monkeypatch.setattr(adapter,'CanonicalMetadata',extended)
    restored=adapter._restore(payload)
    assert restored.lineage is None
    payload['unrecognized_future_field']='not accepted'
    with pytest.raises(ExchangeError,match='fields differ'):
        adapter._restore(payload)


def test_supported_lineage_is_restored_as_typed_data_not_an_opaque_mapping(monkeypatch):
    import tessera.okf as adapter
    from dataclasses import field, make_dataclass
    payload=adapter._canonical_payload(plan_import(FIXTURE,namespace='optional').records[0].canonical)
    extended=make_dataclass('ExtendedCanonicalMetadata',[('lineage',object,field(default=None))],bases=(adapter.CanonicalMetadata,))
    lineage_type=make_dataclass('LineageMetadata',[('source_episode_id',str),('supporting_turns',list),
        ('temporal_position',object),('episode_source',object),('source_evidence',list)])
    monkeypatch.setattr(adapter,'CanonicalMetadata',extended)
    monkeypatch.setattr(adapter.canonical_types,'LineageMetadata',lineage_type,raising=False)
    payload['lineage']={'source_episode_id':'ep-1','supporting_turns':[1],
        'temporal_position':1,'episode_source':None,'source_evidence':[]}
    assert adapter._restore(payload).lineage==lineage_type(**payload['lineage'])
    payload['lineage']['supporting_turns']=[True]
    with pytest.raises(ExchangeError,match='Malformed canonical lineage'):
        adapter._restore(payload)
