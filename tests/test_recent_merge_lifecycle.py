"""Keep merged implementation evidence distinct from validation decisions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/test-cards"


def test_corpus_repair_records_merge_and_exact_head_keep_without_false_pass():
    text = (RECORDS / "12-corpus-equivalence-repair.md").read_text(encoding="utf-8")
    header = text.split("## In one sentence", 1)[0]
    assert "| Record status | `IMPLEMENTED`" in header
    assert "| Decision | `KEEP`" in header
    assert "879ad1f54ecd08f0895c3040743ac8c8b13291ae" in header
    assert "89dec1e444e15bfa8b1361683a9b88a89402888e" in header
    assert "/pull/282#issuecomment-5957192591" in text
    assert "37849491343" in text and "37849491372" in text
    assert "were cancelled on `89dec1e" in text
    assert "37849579311" in text and "37849579474" in text
    assert "not a pass on the earlier merge" in text
    assert "unmerged repair follow-up" not in text
    assert "TARGET — NOT YET ON MAIN" not in text
    assert "Not merged" not in text


def test_recent_merge_index_matches_stage_records_without_promoting_children():
    index = (RECORDS / "README.md").read_text(encoding="utf-8")
    for filename, merge in (
        ("12-corpus-equivalence-repair.md", "89dec1e444e15bfa8b1361683a9b88a89402888e"),
        ("146-qumem-fidelity-documentation.md", "0a4a22c3b356c191a6f30c555eb01677ac2b85a4"),
    ):
        rows = [line for line in index.splitlines() if f"]({filename})" in line]
        assert len(rows) == 1
        assert "| `IMPLEMENTED` |" in rows[0]
        assert merge in rows[0]
    original = (RECORDS / "12-incremental-idempotent-indexing.md").read_text(encoding="utf-8")
    assert "| Record status | `VALIDATED` |" in original
    assert "971801cd89b6ce7b890df9ceb43b6afff9fa0964" in original
