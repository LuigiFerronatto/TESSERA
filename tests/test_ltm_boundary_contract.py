"""Executable baseline evidence for the proposed durable/ephemeral boundary."""
from pathlib import Path
import shutil
import pytest
from tessera import TesseraEngine, TesseraOrchestrator
from tessera.canonical import DRAWERS, parse_and_normalize
from tessera.evidence import evidence_from_canonical, verify_evidence_freshness

ROOT = Path(__file__).resolve().parents[1]


def sources(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*.md')}


def seeded(root):
    engine = TesseraEngine(storage_dir=str(root))
    result = engine.write_memory_note_result('project/fact', 'factual', 'episode/source',
                                           'Basalt service uses cobalt storage.', tags=['basalt'], entities=[])
    assert result.persisted
    engine.build_index()
    return engine


def test_only_explicit_successful_write_changes_durable_source(tmp_path):
    engine = seeded(tmp_path)
    before = sources(tmp_path)
    rejected = engine.write_memory_note_result('project/rejected', 'factual', 'episode/source', '', tags=[], entities=[])
    assert not rejected.persisted
    assert sources(tmp_path) == before
    assert DRAWERS == {'facts', 'preferences', 'insights'}


def test_retrieval_and_assisted_views_never_become_canonical_records(tmp_path):
    engine = seeded(tmp_path)
    before = sources(tmp_path)
    replies = iter(['factual service history', 'basalt cobalt', 'Temporary task plan and answer, not a memory.'])
    result = TesseraOrchestrator(engine, llm_fn=lambda *_: next(replies)).run('basalt cobalt')
    assert result.raw_memories
    assert result.consolidated_context.startswith('Temporary task plan')
    assert sources(tmp_path) == before
    engine.retrieve_context('basalt cobalt')
    assert sources(tmp_path) == before


def test_failed_assistance_does_not_write_partial_state(tmp_path):
    engine = seeded(tmp_path)
    before = sources(tmp_path)
    def failed(*_):
        raise RuntimeError('injected provider failure')
    with pytest.raises(RuntimeError):
        TesseraOrchestrator(engine, llm_fn=failed).run('basalt')
    assert sources(tmp_path) == before


def test_derived_index_loss_does_not_destroy_durable_sources(tmp_path):
    engine = seeded(tmp_path)
    before = sources(tmp_path)
    shutil.rmtree(engine.index_cache_dir)
    restored = TesseraEngine(storage_dir=str(tmp_path))
    restored.build_index()
    assert restored.retrieve_context('basalt cobalt')[0]['id'] == 'project/fact'
    assert sources(tmp_path) == before


def test_source_version_change_marks_old_evidence_stale_not_false(tmp_path):
    path = tmp_path / 'note.md';raw = '---\nid: project/note\n---\nBasalt uses cobalt.\n'
    path.write_text(raw)
    record = evidence_from_canonical(parse_and_normalize(raw, str(path), str(tmp_path)))
    assert verify_evidence_freshness(record, str(tmp_path)).status == 'fresh'
    path.write_text(raw.replace('cobalt', 'amber'))
    assert verify_evidence_freshness(record, str(tmp_path)).status == 'content_changed'


def test_document_keeps_current_and_target_ownership_distinct():
    text = (ROOT/'docs/LONG_TERM_MEMORY.md').read_text()
    assert 'PROPOSED contract candidate' in text
    assert 'What exists on the audited main' in text
    for issue in [19,21,73,15,16,137,196,177,138,135,136,169,167,171,263]:
        assert f'#{issue}' in text
    assert 'invalidation/recompile service itself is not implemented' in text
    assert 'Current overwrite' in text
