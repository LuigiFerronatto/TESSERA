from pathlib import Path

from tessera.canonical import parse_and_normalize
from tessera.evidence import EvidenceLedger, evidence_from_canonical, verify_evidence_freshness


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
    assert first.source.content_hash == canonical.source.content_hash
    assert first.span.start_line == 1
    assert first.span.end_line == len(text.splitlines())


def test_content_edit_creates_new_evidence_version_but_memory_identity_can_stay(tmp_path):
    original = "---\nid: lao/charter\n---\nO propósito do LAO é escalar experimentação.\n"
    path, canonical_before = _canonical(tmp_path, original)
    before = evidence_from_canonical(canonical_before)

    edited = "---\nid: lao/charter\n---\nO propósito do LAO é escalar experimentação com agentes.\n"
    path.write_text(edited, encoding="utf-8")
    canonical_after = parse_and_normalize(
        edited,
        str(path),
        str(tmp_path),
        persistent_id=canonical_before.identity.id,
        persistent_doc_id=canonical_before.source.document_id,
    )
    after = evidence_from_canonical(canonical_after)

    assert before.memory_id == after.memory_id == "lao/charter"
    assert before.source.document_id == after.source.document_id
    assert before.source.content_hash != after.source.content_hash
    assert before.evidence_id != after.evidence_id


def test_verify_freshness_detects_fresh_content_metadata_and_missing_source(tmp_path):
    text = "---\nid: lao/charter\ntags: [lao]\n---\nO propósito do LAO é escalar experimentação.\n"
    path, canonical = _canonical(tmp_path, text)
    record = evidence_from_canonical(canonical)

    fresh = verify_evidence_freshness(record, str(tmp_path))
    assert fresh.status == "fresh"
    assert fresh.is_fresh

    metadata_only = "---\nid: lao/charter\ntags: [lao, purpose]\n---\nO propósito do LAO é escalar experimentação.\n"
    path.write_text(metadata_only, encoding="utf-8")
    changed_meta = verify_evidence_freshness(record, str(tmp_path))
    assert changed_meta.status == "metadata_changed"
    assert changed_meta.content_hash_matches is True
    assert changed_meta.document_hash_matches is False

    content_change = "---\nid: lao/charter\ntags: [lao, purpose]\n---\nO propósito mudou de conteúdo.\n"
    path.write_text(content_change, encoding="utf-8")
    changed_content = verify_evidence_freshness(record, str(tmp_path))
    assert changed_content.status == "content_changed"
    assert changed_content.content_hash_matches is False

    path.unlink()
    missing = verify_evidence_freshness(record, str(tmp_path))
    assert missing.status == "missing_source"
    assert missing.path_exists is False


def test_ledger_deduplicates_identical_record_and_queries_by_memory(tmp_path):
    first_text = "---\nid: lao/charter\n---\nCharter.\n"
    _path1, first_meta = _canonical(tmp_path, first_text, "charter.md")
    first = evidence_from_canonical(first_meta)

    second_text = "---\nid: lao/learning\n---\nLearning.\n"
    _path2, second_meta = _canonical(tmp_path, second_text, "learning.md")
    second = evidence_from_canonical(second_meta)

    ledger = EvidenceLedger([first, first, second])
    assert len(ledger) == 2
    assert ledger.get(first.evidence_id) == first
    assert ledger.for_memory("lao/charter") == [first]
    assert {item["evidence_id"] for item in ledger.to_list()} == {first.evidence_id, second.evidence_id}


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
    assert payload["extraction"] == {"method": "canonical_document", "inferred": False}
