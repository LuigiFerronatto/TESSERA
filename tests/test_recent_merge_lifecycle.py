"""Keep merged implementation evidence distinct from validation decisions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/process/test-cards"


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


def test_harness_registry_reconciliation_preserves_exact_head_and_timing():
    text = (RECORDS / "71-harness-adapter-registry.md").read_text(encoding="utf-8")
    assert "| Record status | `IMPLEMENTED` |" in text
    assert "973a1e75ae1c024edcdd9acef54d840227bc801b" in text
    assert "f149ff292238e2a6f5cdd95894e9c11c365457f2" in text
    for run in ("38191615200", "38191615264", "38201483965", "38201483988"):
        assert run in text
    assert "six seconds after merge" in text
    assert "not evidence of a pre-merge failure" in text
    assert "no final-head formal review or KEEP is claimed" in text
    assert "TARGET — NOT YET ON MAIN" not in text
    assert "Not merged" not in text
    assert "#72 remains blocked on #32" in text
    index = (RECORDS / "README.md").read_text(encoding="utf-8")
    row = next(line for line in index.splitlines() if "| #71 " in line)
    assert "`IMPLEMENTED`" in row and "f149ff29" in row
    roadmap = (ROOT / "docs/process/roadmap.md").read_text(encoding="utf-8")
    assert "Depends only on #71 lifecycle completion" in roadmap
    assert "#71 harness adapter registry (READY / LATER)" not in roadmap
