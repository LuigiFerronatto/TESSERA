from pathlib import Path


# Post-#117 lifecycle routing is intentionally frozen by this governance test.
ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "ROADMAP.md"


def _markdown_table_row(text: str, issue: str) -> str:
    prefix = f"| [{issue}]"
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(matches) == 1, f"expected one roadmap row for {issue}, got {len(matches)}"
    return matches[0]


def test_roadmap_tracks_current_product_release_routing() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    assert "a13abbbba2138e48e237f14a182dd6746e3ec7d4" in text
    assert "fc0ed763ad47f5eba88775f3517cbee99d00a8b9" in text
    assert "`VALIDATED`" in _markdown_table_row(text, "#117")
    assert "`READY`" in _markdown_table_row(text, "#118")
    assert "`READY`" in _markdown_table_row(text, "#119")
    assert "`READY`" in _markdown_table_row(text, "#120")
    assert "`BLOCKED`" in _markdown_table_row(text, "#121")
    assert "`BLOCKED`" in _markdown_table_row(text, "#134")
    assert "remaining blockers are #118 validation + #87" in _markdown_table_row(text, "#134")
    assert "`BLOCKED`" in _markdown_table_row(text, "#87")


def test_roadmap_tracks_qumem_epic_and_child_statuses_without_claiming_delivery() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    expected = {
        "#135": "`READY`",
        "#136": "`BLOCKED`",
        "#137": "`BLOCKED`",
        "#138": "`BLOCKED`",
        "#139": "`READY`",
        "#140": "`BLOCKED`",
        "#141": "`BLOCKED`",
        "#142": "`BLOCKED`",
        "#143": "`BLOCKED`",
        "#144": "`BLOCKED`",
        "#145": "`TRACKER`",
        "#146": "`READY`",
    }

    for issue, status in expected.items():
        row = _markdown_table_row(text, issue)
        assert status in row
        assert "`VALIDATED`" not in row
        assert "`IMPLEMENTED`" not in row

    issue_147 = _markdown_table_row(text, "#147")
    assert "closed" in issue_147
    assert "`VALIDATED`" in issue_147
    assert "a13abbbba2138e48e237f14a182dd6746e3ec7d4" in issue_147

    assert "Principal QUMem gap" in _markdown_table_row(text, "#141")
    assert "fixture design may start early" in _markdown_table_row(text, "#142")
    assert "no direct implementation PR" in _markdown_table_row(text, "#145")


def test_roadmap_freezes_qumem_ownership_boundaries() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    for marker in (
        "#139 = what historical facets must be established?",
        "#140 = WHAT sub-queries/stores should retrieve them?",
        "#17  = HOW each frozen retrieval operation should execute efficiently?",
        "#141 = what state does evidence imply for this query?",
        "#20  = is the evidence/state sufficient, insufficient, conflicting or ambiguous?",
        "interaction temporal_position (#137)",
        "temporal validity/state semantics (#15)",
        "semantic episode membership (#138)",
        "Beginning/Middle/End TESSERA representation",
    ):
        assert marker in text


def test_roadmap_preserves_parallel_ready_work_and_q25_correction() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    assert "`READY`" in _markdown_table_row(text, "#25")
    assert "`READY`" in _markdown_table_row(text, "#28")
    assert "#25 graph-expansion card DoR completion" in text
    assert "superseded by live routing" in _markdown_table_row(text, "#25")

    assert "The roadmap is not one serial queue" in text
    assert "The repository uses bounded WIP" in text


def test_roadmap_keeps_qumem_assisted_mode_optional_and_source_backed() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    for marker in (
        "Optional assisted memory-construction path",
        "Optional assisted query-conditioned path",
        "Information Needs (#139)",
        "Retrieval Plan: WHAT to retrieve (#140)",
        "Structured Fq / Tq / Iq State (#141)",
        "Evidence Status / Abstention (#20)",
        "TESSERA returns evidence and optional structured derived state",
        "Exactly three semantic drawers remain",
    ):
        assert marker in text
