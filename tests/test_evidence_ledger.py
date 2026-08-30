import json
from pathlib import Path

from tessera import Entity, TesseraEngine
from tessera.canonical import parse_and_normalize
from tessera.evidence import (
    EvidenceLedger,
    evidence_for_text,
    evidence_from_canonical,
    ledger_from_graph,
    locate_evidence_span,
    verify_evidence_freshness,
)


def _canonical(tmp_path: Path, text: str, name: str = "note.md"):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, parse_and_normalize(text, str(path), str(tmp_path))


def test_evidence_record_is_deterministic(tmp_path):
    text = "---\nid: lao/charter\n---\nO propósito do LAO é escalar experimentação.\n"
    _path, canonical = _canonical(tmp_path, text)
    first = evidence_from_canonical(canonical)
    second = evidence_from_canonical(canonical)
    assert first == second
    assert first.evidence_id.startswith("ev_")
    assert first.memory_id == "lao/charter"
    assert first.source.document_id == canonical.source.document_id
    assert first.span.start_line == 1
    assert first.span.end_line == len(text.splitlines())


def test_content_edit_creates_new_evidence_version_but_identity_stays(tmp_path):
    original = "---\nid: lao/charter\n---\nO propósito do LAO é escalar experimentação.\n"
    path, before_meta = _canonical(tmp_path, original)
    before = evidence_from_canonical(before_meta)

    edited = "---\nid: lao/charter\n---\nO propósito do LAO é escalar experimentação com agentes.\n"
    path.write_text(edited, encoding="utf-8")
    after_meta = parse_and_normalize(
        edited, str(path), str(tmp_path),
        persistent_id=before_meta.identity.id,
        persistent_doc_id=before_meta.source.document_id,
    )
    after = evidence_from_canonical(after_meta)

    assert before.memory_id == after.memory_id == "lao/charter"
    assert before.source.document_id == after.source.document_id
    assert before.source.content_hash != after.source.content_hash
    assert before.evidence_id != after.evidence_id


def test_metadata_only_change_creates_new_exact_source_version(tmp_path):
    original = "---\nid: lao/charter\ntags: [lao]\n---\nMesmo corpo.\n"
    path, before_meta = _canonical(tmp_path, original)
    before = evidence_from_canonical(before_meta)

    edited = "---\nid: lao/charter\ntags: [lao, purpose]\n---\nMesmo corpo.\n"
    path.write_text(edited, encoding="utf-8")
    after_meta = parse_and_normalize(
        edited, str(path), str(tmp_path),
        persistent_id=before_meta.identity.id,
        persistent_doc_id=before_meta.source.document_id,
    )
    after = evidence_from_canonical(after_meta)

    assert before.source.content_hash == after.source.content_hash
    assert before.source.document_hash != after.source.document_hash
    assert before.evidence_id != after.evidence_id


def test_verify_freshness_detects_all_states(tmp_path):
    text = "---\nid: lao/charter\ntags: [lao]\n---\nO propósito do LAO é escalar experimentação.\n"
    path, canonical = _canonical(tmp_path, text)
    record = evidence_from_canonical(canonical)
    assert verify_evidence_freshness(record, str(tmp_path)).status == "fresh"

    path.write_text(
        "---\nid: lao/charter\ntags: [lao, purpose]\n---\nO propósito do LAO é escalar experimentação.\n",
        encoding="utf-8",
    )
    changed_meta = verify_evidence_freshness(record, str(tmp_path))
    assert changed_meta.status == "metadata_changed"
    assert changed_meta.content_hash_matches is True

    path.write_text(
        "---\nid: lao/charter\ntags: [lao]\n---\nO propósito mudou.\n",
        encoding="utf-8",
    )
    assert verify_evidence_freshness(record, str(tmp_path)).status == "content_changed"

    path.unlink()
    assert verify_evidence_freshness(record, str(tmp_path)).status == "missing_source"


def test_ledger_deduplicates_and_queries_by_memory(tmp_path):
    _p1, m1 = _canonical(tmp_path, "---\nid: lao/charter\n---\nCharter.\n", "charter.md")
    _p2, m2 = _canonical(tmp_path, "---\nid: lao/learning\n---\nLearning.\n", "learning.md")
    first, second = evidence_from_canonical(m1), evidence_from_canonical(m2)
    ledger = EvidenceLedger([first, first, second])
    assert len(ledger) == 2
    assert ledger.get(first.evidence_id) == first
    assert ledger.for_memory("lao/charter") == [first]


def test_evidence_serialization_preserves_provenance_fields(tmp_path):
    text = "---\nid: decisions/adr-001\ndocument_type: decision_record\n---\nDecisão registrada.\n"
    _path, canonical = _canonical(tmp_path, text, "adr-001.md")
    payload = evidence_from_canonical(canonical).to_dict()
    assert payload["memory_id"] == "decisions/adr-001"
    assert payload["source"]["document_id"]
    assert payload["source"]["path"] == "adr-001.md"
    assert payload["source"]["document_hash"]
    assert payload["source"]["content_hash"]
    assert payload["fingerprint"]


def test_query_aware_evidence_exact_span_and_ambiguity(tmp_path):
    raw = (
        "---\nid: lao/charter\n---\n# Charter\n\nO LAO pesquisa sinais.\n\n"
        "O propósito do LAO é escalar experimentação.\n"
        "com agentes autônomos e evidência auditável.\n"
    )
    _path, canonical = _canonical(tmp_path, raw)
    evidence_text = (
        "O propósito do LAO é escalar experimentação.\n"
        "com agentes autônomos e evidência auditável."
    )
    span = locate_evidence_span(raw, evidence_text)
    assert (span.start_line, span.end_line) == (8, 9)
    record = evidence_for_text(canonical, raw, evidence_text)
    assert (record.span.start_line, record.span.end_line) == (8, 9)

    unknown = locate_evidence_span(raw, "texto inexistente")
    assert (unknown.start_line, unknown.end_line) == (None, None)

    duplicate = "---\nid: x\n---\nMesmo trecho.\n\nMesmo trecho.\n"
    ambiguous = locate_evidence_span(duplicate, "Mesmo trecho.")
    assert (ambiguous.start_line, ambiguous.end_line) == (None, None)


def test_engine_integrates_ledger_provenance_evidence_and_derived_snapshot(tmp_path):
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.write_memory_note(
        mem_id="lao/charter",
        mem_type="factual",
        episode_id="ep-purpose",
        content=(
            "O propósito do LAO é escalar experimentação com agentes autônomos.\n\n"
            "A memória auditável preserva evidências para decisões futuras."
        ),
        tags=["lao", "purpose", "charter"],
        entities=[Entity("LAO", "Lab Autonomous Officer")],
    )
    engine.write_memory_note(
        mem_id="lao/noise", mem_type="factual", episode_id="ep-noise",
        content="Uma nota geral sobre automação de software.",
        tags=["automation"], entities=[],
    )
    engine.build_index(use_cache=False)

    assert len(engine.evidence_ledger.for_memory("lao/charter")) == 1
    assert engine.graph.nodes["lao/charter"]["evidence_record"]["memory_id"] == "lao/charter"

    snapshot_path = tmp_path / ".tessera_index" / "evidence.json"
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["derived"] is True
    assert payload["source_of_truth"] == "source_files"
    assert any(r["memory_id"] == "lao/charter" for r in payload["records"])

    results = engine.retrieve_context("qual o propósito do LAO?", top_n=2)
    charter = next(item for item in results if item["id"] == "lao/charter")
    assert charter["provenance"]["memory_id"] == "lao/charter"
    assert charter["relevant_evidence"]
    assert charter["evidence"] is not None
    assert charter["evidence"]["span"]["start_line"] is not None
    assert charter["evidence"]["extraction"]["method"] == "paragraph_lexical"


def test_cached_index_rebuilds_same_logical_evidence_ledger(tmp_path):
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.write_memory_note(
        mem_id="lao/charter", mem_type="factual", episode_id="ep",
        content="O propósito do LAO é escalar experimentação.",
        tags=["lao"], entities=[],
    )
    engine.build_index(use_cache=False)
    first_id = engine.evidence_ledger.for_memory("lao/charter")[0].evidence_id

    reloaded = TesseraEngine(storage_dir=str(tmp_path))
    reloaded.build_index(use_cache=True)
    second_id = reloaded.evidence_ledger.for_memory("lao/charter")[0].evidence_id
    assert first_id == second_id


def test_no_relevant_evidence_means_no_query_specific_evidence(tmp_path):
    engine = TesseraEngine(storage_dir=str(tmp_path))
    engine.write_memory_note(
        mem_id="lao/charter", mem_type="factual", episode_id="ep",
        content="O propósito do LAO é escalar experimentação.", tags=["lao"], entities=[],
    )
    engine.build_index(use_cache=False)
    results = engine.retrieve_context("xyzabcqwe", top_n=1)
    if results:
        assert results[0]["relevant_evidence"] is None
        assert results[0]["evidence"] is None
        assert results[0]["provenance"] is not None
