"""Issue #263 failure matrix: no providers, source rewrites, or secret diagnostics."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tessera import TesseraEngine, WriteReceipt
from tessera import write_receipts as receipts

SECRET = "Private source payload must never enter operational diagnostics."


def write(engine, operation_id="op-263", **changes):
    args = dict(mem_id="project/note", mem_type="factual", episode_id="episode-1",
                content=SECRET, tags=[], entities=[], operation_id=operation_id)
    args.update(changes)
    return engine.write_memory_note_result(**args)


def canonical_bytes(engine):
    return (Path(engine.storage_dir) / "project/note.md").read_bytes()


def fail(*_a, **_k):
    raise OSError(SECRET)


def test_clean_receipt_and_restart_idempotency(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    first = write(engine)
    before = canonical_bytes(engine)
    second = write(TesseraEngine(str(tmp_path)))
    assert first.to_dict() == second.to_dict()
    assert canonical_bytes(engine) == before
    receipt = first.write_receipt.to_dict()
    assert receipt["schema_version"] == 1
    assert receipt["persisted"] and receipt["indexed"] == receipt["evidence_ledger"] == "complete"
    assert receipt["hooks"] == [] and receipt["hooks_status"] == "not_applicable"
    assert not receipt["repair_required"]
    assert SECRET not in json.dumps(receipt)
    for record in (tmp_path / ".tessera_operations").glob("*.json"):
        assert SECRET not in record.read_text()
    assert len(list(tmp_path.rglob("*.md"))) == 1


@pytest.mark.parametrize("content,memory_id", [("", "project/note"), (SECRET, "../escape")])
def test_rejection_precedes_all_mutation(tmp_path, content, memory_id):
    engine = TesseraEngine(str(tmp_path))
    result = write(engine, content=content, mem_id=memory_id)
    assert not result.persisted
    assert result.write_receipt.indexed == "not_applicable"
    assert list(tmp_path.iterdir()) == []


def test_pre_persistence_failure_has_no_applied_components(tmp_path, monkeypatch):
    engine = TesseraEngine(str(tmp_path))
    original = os.replace
    def replace(source, target):
        if str(target).endswith(".md"):
            fail()
        return original(source, target)
    monkeypatch.setattr(os, "replace", replace)
    result = write(engine)
    assert not result.persisted and not result.write_receipt.persisted
    assert not list(tmp_path.rglob("*.md"))
    assert not engine.file_registry and not engine.graph and not engine.evidence_ledger.to_list()
    assert result.write_receipt.errors == ("persistence_failed",)
    assert SECRET not in json.dumps(result.to_dict())
    monkeypatch.setattr(os, "replace", original)
    assert write(engine).write_receipt.indexed == "complete"


@pytest.mark.parametrize("stage,status,ledger", [
    ("_write_receipt_index", "failed", "pending"),
    ("save_index", "failed", "pending"),
    ("_rebuild_evidence_ledger", "complete", "failed"),
    ("_persist_evidence_summary", "complete", "failed"),
])
def test_post_persistence_failure_and_deterministic_repair(tmp_path, monkeypatch, stage, status, ledger):
    engine = TesseraEngine(str(tmp_path))
    monkeypatch.setattr(engine, stage, fail)
    result = write(engine)
    assert result.persisted and result.write_receipt.persisted
    assert result.write_receipt.indexed == status
    assert result.write_receipt.evidence_ledger == ledger
    assert result.write_receipt.repair_required
    before = canonical_bytes(engine)
    restarted = TesseraEngine(str(tmp_path))
    repaired = restarted.repair_write_receipt("op-263")
    assert repaired.indexed == repaired.evidence_ledger == "complete"
    assert not repaired.repair_required
    assert canonical_bytes(engine) == before
    ledger_before = restarted.evidence_ledger.to_list()
    restarted.repair_write_receipt("op-263")
    assert restarted.evidence_ledger.to_list() == ledger_before
    assert len(ledger_before) == 1
    assert SECRET not in json.dumps(result.to_dict())


def test_journal_failure_after_source_replace_preserves_truth(tmp_path, monkeypatch):
    engine = TesseraEngine(str(tmp_path))
    real = receipts._atomic_json
    calls = 0
    def failing_checkpoint(path, value):
        nonlocal calls
        calls += 1
        if calls > 1:
            fail()
        return real(path, value)
    monkeypatch.setattr(receipts, "_atomic_json", failing_checkpoint)
    result = write(engine)
    assert result.persisted
    assert "receipt_store_failed" in result.write_receipt.errors
    assert result.write_receipt.repair_required
    monkeypatch.setattr(receipts, "_atomic_json", real)
    before = canonical_bytes(engine)
    assert write(TesseraEngine(str(tmp_path))).write_receipt.indexed == "complete"
    assert canonical_bytes(engine) == before


PROCESS = '''
import json, os, sys
from tessera import TesseraEngine
engine = TesseraEngine(sys.argv[1])
if sys.argv[2] == "crash":
    original = os.replace
    def replace(source, target):
        original(source, target)
        if str(target).endswith(".md"):
            os._exit(71)
    os.replace = replace
result = engine.write_memory_note_result("project/note", "factual", "episode-1", %r, [], [], operation_id="op-263")
print(json.dumps(result.write_receipt.to_dict()))
''' % SECRET


def test_process_crash_after_replace_then_restart(tmp_path):
    process = subprocess.run([sys.executable, "-c", PROCESS, str(tmp_path), "crash"], capture_output=True)
    assert process.returncode == 71
    engine = TesseraEngine(str(tmp_path))
    before = canonical_bytes(engine)
    inspected = engine.inspect_write_receipt("op-263")
    assert inspected.persisted and inspected.indexed == "pending"
    repaired = engine.repair_write_receipt("op-263")
    assert not repaired.repair_required
    assert canonical_bytes(engine) == before
    assert write(engine).write_receipt.source_revision == repaired.source_revision


def test_concurrent_retry_from_independent_processes(tmp_path):
    processes = [subprocess.Popen([sys.executable, "-c", PROCESS, str(tmp_path), "write"],
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(3)]
    results = []
    for process in processes:
        output, errors = process.communicate(timeout=60)
        assert process.returncode == 0, errors
        results.append(json.loads(output))
    assert results[0] == results[1] == results[2]
    assert len(list(tmp_path.rglob("*.md"))) == 1


@pytest.mark.parametrize("changes", [{"content": "Different."}, {"mem_id": "project/other"}, {"tags": ["different"]}])
def test_operation_id_reuse_with_different_request_is_refused(tmp_path, changes):
    engine = TesseraEngine(str(tmp_path))
    write(engine)
    before = canonical_bytes(engine)
    with pytest.raises(ValueError, match="different request"):
        write(engine, **changes)
    assert canonical_bytes(engine) == before


@pytest.mark.parametrize("artifact", ["graph.pkl", "graph.json", "identity_manifest.json", "evidence.json"])
def test_corrupt_or_missing_projections_are_rebuildable(tmp_path, artifact):
    engine = TesseraEngine(str(tmp_path))
    write(engine)
    before = canonical_bytes(engine)
    clean_evidence = engine.evidence_ledger.to_list()
    path = Path(engine.index_cache_dir) / artifact
    path.write_text("corrupt")
    assert engine.inspect_write_receipt("op-263").repair_required
    repaired_engine = TesseraEngine(str(tmp_path))
    assert not repaired_engine.repair_write_receipt("op-263").repair_required
    assert repaired_engine.evidence_ledger.to_list() == clean_evidence
    assert canonical_bytes(engine) == before
    path.unlink()
    assert engine.inspect_write_receipt("op-263").repair_required
    assert not engine.repair_write_receipt("op-263").repair_required


def test_corrupt_journal_recovery_is_source_driven(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    write(engine)
    before = canonical_bytes(engine)
    path = receipts._record_path(engine, "op-263")
    path.write_text("bad json")
    with pytest.raises(ValueError, match="corrupt"):
        write(engine)
    assert any(item.get("status") == "corrupt" for item in engine.inspect_write_receipts())
    assert not engine.repair_write_receipt("op-263").repair_required
    assert canonical_bytes(engine) == before
    path.unlink()
    assert engine.inspect_write_receipt("op-263").repair_required
    assert not write(engine).write_receipt.repair_required
    assert canonical_bytes(engine) == before


def test_old_operation_never_reverts_a_newer_source(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    old = write(engine)
    write(engine, "op-new", content="Newer content.")
    before = canonical_bytes(engine)
    retried = write(engine)
    assert retried.persisted
    assert retried.write_receipt.source_revision == old.write_receipt.source_revision
    assert retried.write_receipt.source_state == "superseded"
    assert retried.write_receipt.indexed == "not_applicable"
    assert canonical_bytes(engine) == before


def test_python_cli_mcp_receipt_parity(tmp_path, monkeypatch):
    from tessera import mcp_server
    engine = TesseraEngine(str(tmp_path))
    expected = write(engine).write_receipt.to_dict()
    command = [sys.executable, "-m", "tessera.cli", "write", str(tmp_path), "--id", "project/note",
               "--type", "factual", "--episode", "episode-1", "--content", SECRET,
               "--operation-id", "op-263", "--json"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["write_receipt"] == expected
    monkeypatch.setattr(mcp_server, "_engine", engine)
    assert mcp_server.write_memory("project/note", "factual", "episode-1", SECRET,
                                   operation_id="op-263")["write_receipt"] == expected
    assert mcp_server.inspect_write_receipt("op-263") == expected
    assert mcp_server.repair_write_receipt("op-263") == expected


def test_doctor_reports_incomplete_receipt_without_mutation(tmp_path, monkeypatch):
    from tessera.config import ResolvedConfiguration
    from tessera.corpus_diagnostics import run_corpus_doctor
    engine = TesseraEngine(str(tmp_path))
    monkeypatch.setattr(engine, "_write_receipt_index", fail)
    write(engine)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    report = run_corpus_doctor(ResolvedConfiguration(None, str(tmp_path), "legacy_storage_dir"))
    assert any(item.code == "incomplete_write_receipt" for item in report.findings)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_rebuild_never_unpickles_corrupt_cache(tmp_path, monkeypatch):
    import pickle
    engine = TesseraEngine(str(tmp_path))
    write(engine)
    monkeypatch.setattr(pickle, "load", fail)
    assert not engine.repair_write_receipt("op-263").repair_required


def test_invalid_receipt_states_are_rejected():
    with pytest.raises(ValueError):
        WriteReceipt("op", "id", indexed="complete")
    with pytest.raises(ValueError):
        WriteReceipt("op", "id", True)


def test_crlf_payload_uses_exact_source_revision(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    result = write(engine, content="First line.\r\nUnicode café.\r\n")
    assert not result.write_receipt.repair_required
    assert canonical_bytes(engine).endswith(b"First line.\r\nUnicode caf\xc3\xa9.\r\n")
    assert not engine.repair_write_receipt("op-263").repair_required


def test_deleted_source_is_not_recreated(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    original = write(engine)
    Path(original.filepath).unlink()
    receipt = engine.repair_write_receipt("op-263")
    assert receipt.persisted and receipt.source_state == "missing"
    assert receipt.indexed == receipt.evidence_ledger == "not_applicable"
    assert not Path(original.filepath).exists()


def test_crash_after_index_before_ledger_has_truthful_stages(tmp_path):
    script = PROCESS.replace('if sys.argv[2] == "crash":',
       'if sys.argv[2] == "index-crash":\n    engine._rebuild_evidence_ledger = lambda: os._exit(72)\nif sys.argv[2] == "crash":')
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path), "index-crash"], capture_output=True)
    assert process.returncode == 72
    engine = TesseraEngine(str(tmp_path))
    inspected = engine.inspect_write_receipt("op-263")
    assert inspected.persisted and inspected.indexed == "complete" and inspected.evidence_ledger == "pending"
    assert not engine.repair_write_receipt("op-263").repair_required


def test_crash_reconciled_before_later_operation_can_overwrite(tmp_path):
    subprocess.run([sys.executable, "-c", PROCESS, str(tmp_path), "crash"], check=False)
    engine = TesseraEngine(str(tmp_path))
    write(engine, "new-op", content="Newer source.")
    before = canonical_bytes(engine)
    old = write(engine)
    assert old.persisted and old.write_receipt.source_state == "superseded"
    assert canonical_bytes(engine) == before


def test_journal_creation_failure_reports_no_false_success(tmp_path, monkeypatch):
    engine = TesseraEngine(str(tmp_path))
    monkeypatch.setattr(receipts, "_fsync_dir", fail)
    result = write(engine)
    assert not result.persisted
    assert result.write_receipt.errors == ("receipt_store_failed",)
    assert not list(tmp_path.rglob("*.md"))


def test_source_parser_failures_do_not_leak_private_text(tmp_path, capsys):
    (tmp_path / "broken.md").write_text("---\nbad: [" + SECRET + "\n---\n")
    result = write(TesseraEngine(str(tmp_path)))
    assert result.persisted and result.write_receipt.indexed == "failed"
    assert SECRET not in capsys.readouterr().err
    assert SECRET not in json.dumps(result.write_receipt.to_dict())


def test_multiple_receipts_converge_after_shared_projection_repair(tmp_path, monkeypatch):
    engine = TesseraEngine(str(tmp_path))
    first = write(engine)
    with monkeypatch.context() as patch:
        patch.setattr(engine, "_persist_evidence_summary", fail)
        partial = write(engine, "partial", mem_id="project/partial")
        assert partial.write_receipt.evidence_ledger == "failed"
    write(engine, "third", mem_id="project/third")
    assert not any(item["repair_required"] for item in engine.inspect_write_receipts())
    assert engine.inspect_write_receipt("partial").evidence_ledger == "complete"
    engine.repair_write_receipt("op-263")
    assert not any(item["repair_required"] for item in engine.inspect_write_receipts())
    assert engine.inspect_write_receipt("op-263").source_revision == first.write_receipt.source_revision


def test_mcp_startup_can_reach_repair_with_structurally_corrupt_cache(tmp_path):
    import pickle
    from tessera.config import ResolvedConfiguration
    from tessera.mcp_runtime import MCPRuntime
    engine = TesseraEngine(str(tmp_path))
    write(engine)
    before = canonical_bytes(engine)
    Path(engine.index_cache_pkl).write_bytes(pickle.dumps([]))
    runtime = MCPRuntime(configuration=ResolvedConfiguration(None, str(tmp_path), "legacy_storage_dir"))
    started = runtime.get_engine()
    assert not started.repair_write_receipt("op-263").repair_required
    assert canonical_bytes(engine) == before


def test_read_only_external_source_marker_cannot_claim_store_persistence(tmp_path, monkeypatch):
    external = TesseraEngine(str(tmp_path / "external"))
    foreign = write(external)
    target = TesseraEngine(str(tmp_path / "target"))
    monkeypatch.setattr(target, "_iter_source_files", lambda recursive: [foreign.filepath])
    with pytest.raises(ValueError, match="not found"):
        target.inspect_write_receipt("op-263")
    assert target.inspect_write_receipts() == []


def test_missing_journal_does_not_allow_operation_reuse_for_another_memory(tmp_path):
    engine = TesseraEngine(str(tmp_path))
    write(engine)
    receipts._record_path(engine, "op-263").unlink()
    with pytest.raises(ValueError, match="different request"):
        write(engine, mem_id="project/other")
    assert not (tmp_path / "project/other.md").exists()


def test_receipt_inspection_uses_engine_owned_physical_source_keys(tmp_path,monkeypatch):
    engine=TesseraEngine(str(tmp_path))
    previous=engine._relative_identity_path
    monkeypatch.setattr(engine,'_relative_identity_path',lambda path:'selected/'+previous(path))
    first=write(engine,operation_id='physical-key')
    assert first.write_receipt.indexed=='complete'
    assert engine.inspect_write_receipt('physical-key').to_dict()==first.write_receipt.to_dict()
    assert write(engine,operation_id='physical-key').write_receipt.to_dict()==first.write_receipt.to_dict()


def test_receipt_request_hash_preserves_typed_metadata_without_lossy_strings(tmp_path,monkeypatch):
    from dataclasses import dataclass
    @dataclass
    class SourceReference:
        episode: str
        positions: list
    engine=TesseraEngine(str(tmp_path))
    original=engine._write_memory_note_result
    def extension_writer(**arguments):
        arguments.pop('source_reference')
        return original(**arguments)
    monkeypatch.setattr(engine,'_write_memory_note_result',extension_writer)
    arguments=dict(mem_id='project/note',mem_type='factual',episode_id='episode-1',
        content=SECRET,tags=[],entities=[],description='',provenance_turns=None,
        active_connections=None,persist_format='md',source_reference=SourceReference('ep',[1,3]))
    first=receipts.write_with_receipt(engine,arguments,'typed-request')
    assert first.persisted
    assert receipts.write_with_receipt(engine,arguments,'typed-request').to_dict()==first.to_dict()
    arguments['source_reference']=SourceReference('ep',[1,4])
    with pytest.raises(ValueError,match='different request'):
        receipts.write_with_receipt(engine,arguments,'typed-request')
    with pytest.raises(TypeError,match='unsupported receipt'):
        receipts._request_json_default(object())
    with pytest.raises(TypeError,match='unsupported receipt'):
        receipts._request_json_default(SourceReference)
