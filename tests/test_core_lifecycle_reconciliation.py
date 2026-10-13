"""Canonical delivery, check identity and adoption remain separate facts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs/process/test-cards"
CASES = (
    ("73-revision-history.md", "121ff0a2ce8b67647a91dc5e8b47e1e53a63cd70", "3a9e9b892604a69a30de44efe8980ef6682b8042"),
    ("263-durable-write-receipts.md", "894464179c669d876f4d2f1f314f4699559ae49a", "4b8606112d26b9294f295edcd988af41082ea415"),
    ("166-unified-cli-presentation.md", "d40833c2a3293fc52ad508509936e5b98a207f3a", "7566fc701a5227de18995cd8c01e556547bf886a"),
)


def test_merged_core_records_name_exact_delivery_without_inventing_decisions():
    index = (RECORDS / "README.md").read_text(encoding="utf-8")
    for filename, candidate, canonical in CASES:
        text = (RECORDS / filename).read_text(encoding="utf-8")
        header = text.split("## In one sentence", 1)[0]
        assert "| Record status | `IMPLEMENTED` |" in header
        assert "| Decision | `PENDING`" in header
        assert candidate in header and canonical in header
        assert "TARGET — NOT YET ON MAIN" not in text
        assert "Not merged" not in text
        assert "final-head formal reviews" in text
        rows = [line for line in index.splitlines() if f"]({filename})" in line]
        assert len(rows) == 1
        assert "| `IMPLEMENTED` |" in rows[0]
        assert canonical in rows[0]


def test_revision_history_preserves_cancelled_canonical_ci_and_opt_in_limits():
    text = (RECORDS / CASES[0][0]).read_text(encoding="utf-8")
    for marker in ("38203793938", "38203793949", "38203925811", "38203925791", "canonical CI was cancelled", "not a successful canonical CI run", "CLI/MCP/config opt-in", "default activation", "#15/#16/#19"):
        assert marker in text
    assert "| Decision | `KEEP" not in text


def test_receipts_and_presentation_record_exact_canonical_passes():
    receipt = (RECORDS / CASES[1][0]).read_text(encoding="utf-8")
    ui = (RECORDS / CASES[2][0]).read_text(encoding="utf-8")
    for marker in ("38203173850", "38203173845", "38203671135", "38203671143", "Legacy/external writers", "Distributed transactions"):
        assert marker in receipt
    for marker in ("38205377624", "38205377619", "38205379993", "38205379999", "#356", "#119", "#351/#357"):
        assert marker in ui


def test_core_roadmap_records_delivery_without_promoting_dependents():
    text = (ROOT / "docs/process/roadmap.md").read_text(encoding="utf-8")
    for number, _, canonical in ((73, *CASES[0][1:]), (263, *CASES[1][1:]), (166, *CASES[2][1:])):
        rows = [line for line in text.splitlines() if line.startswith(f"| [#{number}]")]
        assert len(rows) == 1
        assert "| `IMPLEMENTED` |" in rows[0]
        assert canonical in rows[0]
    for number in (15, 16, 19):
        rows = [line for line in text.splitlines() if line.startswith(f"| [#{number}]")]
        assert len(rows) == 1
        assert "`READY`" not in rows[0]
