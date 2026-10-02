"""Freeze verified merge evidence for lifecycle issues #249/#269/#275/#278/#280.

These offline documentation checks do not make a new KEEP decision or assert
that an unmerged reconciliation branch is already canonical.
"""

import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FOUNDATION = (
    (12, 246, "12-incremental-idempotent-indexing.md",
     "def1c43c069f616e63fdea7e384e15af4ecfef44",
     "971801cd89b6ce7b890df9ceb43b6afff9fa0964", "5635092374"),
    (69, 264, "69-text-ingestion.md",
     "ddc1ff3a4394c89c7732357fc66168d6d599a2ac",
     "c815a684e4c8cbd426a0d717e243a7dfb0f04395", "5673959396"),
    (70, 270, "70-structural-segmentation.md",
     "e14ef92e2891d8429539ec4a47174c76ab241839",
     "8ca854f14f8f57443784e6cf3524419a953c2ce6", "5684680369"),
    (13, 277, "13-corpus-doctor.md",
     "dbcf5e737c4bd365f38915ae9e70a527713e6aa5",
     "20814a47ec0f72d7bea0639e0b057df1ecf5cded", "5685536995"),
)


def _table_row(text: str, first_cell: str) -> list[str]:
    rows = [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in text.splitlines() if line.startswith("|")
    ]
    matches = [row for row in rows if row and row[0] == first_cell]
    assert len(matches) == 1, (first_cell, matches)
    return matches[0]


@pytest.mark.parametrize("issue,pr,filename,head,merge,audit", FOUNDATION)
def test_stage_and_index_record_exact_canonical_evidence(
    issue: int, pr: int, filename: str, head: str, merge: str, audit: str,
) -> None:
    text = (DOCS / "test-cards" / filename).read_text(encoding="utf-8")
    # Inspect header fields, not a later historical mention of the desired state.
    header = text.split("## In one sentence", 1)[0]
    assert _table_row(header, "Record status")[1] == "`VALIDATED`"
    assert _table_row(header, "Decision")[1] == "`KEEP`"
    assert head in _table_row(header, "Head commit")[1]
    assert merge in _table_row(header, "Merge commit")[1]
    assert f"/pull/{pr}#issuecomment-{audit}" in text

    index = (DOCS / "test-cards" / "README.md").read_text(encoding="utf-8")
    rows = [line for line in index.splitlines() if f"]({filename})" in line]
    assert len(rows) == 1
    assert "`VALIDATED`" in rows[0]
    assert merge in rows[0]


@pytest.mark.parametrize("issue,pr,filename,head,merge,audit", FOUNDATION[1:])
def test_evolution_audit_distinguishes_candidate_from_merge(
    issue: int, pr: int, filename: str, head: str, merge: str, audit: str,
) -> None:
    path = DOCS / f"PR_EVOLUTION_{issue}.md"
    assert path.is_file(), f"Missing canonical evolution evidence: {path.name}"
    text = path.read_text(encoding="utf-8")
    assert head != merge
    assert head in text and merge in text
    assert "`VALIDATED`" in text and "`KEEP`" in text
    assert f"/pull/{pr}#issuecomment-{audit}" in text
    record = (DOCS / "test-cards" / filename).read_text(encoding="utf-8")
    assert path.name in _table_row(record, "PR Evolution Audit")[1]


@pytest.mark.parametrize(
    "issue,capability",
    ((12, "Incremental/idempotent indexing"),
     (69, "Plain-text ingestion beyond Markdown"),
     (70, "Structural segmentation"),
     (13, "Read-only Corpus Doctor")),
)
def test_implemented_foundation_is_not_listed_as_planned(
    issue: int, capability: str,
) -> None:
    overview = (DOCS / "OVERVIEW.md").read_text(encoding="utf-8")
    row = _table_row(overview, capability)
    assert "Validated" in row[1]
    assert f"#{issue}" in row[2]
    architecture = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    implemented, planned = architecture.split("Implemented Foundation:", 1)[1].split(
        "Planned / experimental:", 1
    )
    assert re.search(rf"^#{issue}\s", implemented, re.MULTILINE)
    planned = planned.split("## Target architecture", 1)[0]
    assert not re.search(rf"^#{issue}\s", planned, re.MULTILINE)


def test_completed_corpus_doctor_keeps_queue_12_and_no_new_now_selection() -> None:
    roadmap = (DOCS / "ROADMAP.md").read_text(encoding="utf-8")
    completed = roadmap.split("## Completed NOW positions", 1)[1].split("## NOW", 1)[0]
    code_blocks = re.findall(r"```text\n(.*?)```", completed, re.DOTALL)
    doctor_rows = [
        line for block in code_blocks for line in block.splitlines()
        if re.search(r"#13\s", line)
    ]
    assert len(doctor_rows) == 1
    assert re.match(r"12\s+#13\s", doctor_rows[0])
    assert "VALIDATED" in doctor_rows[0]
    now = roadmap.split("\n## NOW\n", 1)[1].split("\n## NEXT\n", 1)[0]
    assert "No executable card is currently selected" in now
    deferred = _table_row(
        roadmap, "[#19](https://github.com/LuigiFerronatto/TESSERA/issues/19)"
    )
    assert deferred[2] == "`DEFERRED`"
