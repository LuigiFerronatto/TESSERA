from pathlib import Path


# Portfolio routing is intentionally frozen by this governance-only, NOT_APPLICABLE card.
ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "ROADMAP.md"


def _row(text: str, issue: str) -> str:
    prefix = f"| [{issue}]"
    rows = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(rows) == 1, (issue, rows)
    return rows[0]


def test_productization_v2_critical_path_is_explicit() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    for marker in (
        "#153 config v2",
        "#154 sources",
        "#155 init UX",
        "#118 clean onboarding",
        "#134 first PyPI release",
        "#87 legal/repository entrypoint",
    ):
        assert marker in text

    assert "`READY`" in _row(text, "#153")
    for issue in ("#154", "#155", "#118", "#134"):
        assert "`BLOCKED`" in _row(text, issue)


def test_intelligence_tracker_and_children_are_dependency_routed() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    assert "`TRACKER`" in _row(text, "#164")
    expected_blocked = ("#157", "#158", "#159", "#160", "#161", "#162", "#163", "#165")
    for issue in expected_blocked:
        assert "`BLOCKED`" in _row(text, issue)

    assert "#153 -> #157 typed model profiles" in text
    assert "capability\n-> typed profile\n-> provider/model" in text


def test_cognitive_continuity_ownership_is_explicit() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    assert "`TRACKER`" in _row(text, "#170")
    assert "`READY`" in _row(text, "#168")
    for issue in ("#169", "#167", "#171"):
        assert "`BLOCKED`" in _row(text, issue)

    for marker in (
        "#168 = durable memory boundary",
        "#169 = selection + synthesis + context budgeting",
        "#167 = packet identity + bootstrap + reuse + freshness/invalidation",
        "#171 = semantic intents: search / context / evidence / remember / inspect",
        "#120 = MCP server/transport/config/errors/timeouts/concurrency",
        "#168 Long-Term Memory\n!=\n#169 Context Compiler\n!=\n#167 Working Context\n!=\n#171 Agent-facing semantic API\n!=\n#120 MCP transport/runtime",
        "READ BEFORE REASONING",
        "WRITE AFTER LEARNING",
    ):
        assert marker in text


def test_every_audited_open_issue_has_one_reconciliation_row() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    open_issues = (
        "#12", "#13", "#14", "#15", "#16", "#17", "#18", "#19", "#20", "#21",
        "#25", "#26", "#27", "#28", "#32", "#67", "#69", "#70", "#71", "#72",
        "#73", "#78", "#80", "#87", "#103", "#104", "#105", "#106",
        "#118", "#119", "#120", "#121", "#134",
        "#135", "#136", "#137", "#138", "#139", "#140", "#141", "#142",
        "#143", "#144", "#145", "#146",
        "#153", "#154", "#155", "#157", "#158", "#159", "#160", "#161",
        "#162", "#163", "#164", "#165", "#166", "#167", "#168", "#169",
        "#170", "#171", "#172",
    )
    for issue in open_issues:
        assert "open" in _row(text, issue)


def test_trackers_and_owner_decision_cannot_masquerade_as_ready_execution() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    for issue in ("#14", "#18", "#145", "#164", "#170"):
        row = _row(text, issue)
        assert "`TRACKER`" in row
        assert "| TRACKER |" in row
        assert "`READY`" not in row

    issue_87 = _row(text, "#87")
    assert "| ADMIN |" in issue_87
    assert "`BLOCKED`" in issue_87


def test_ready_executable_backlog_stays_within_declared_wip_limit() -> None:
    text = ROADMAP.read_text(encoding="utf-8")

    ready_executable = []
    for line in text.splitlines():
        if not line.startswith("| [#"):
            continue
        if "| open |" in line and "`READY`" in line and "| EXECUTABLE |" in line:
            ready_executable.append(line)

    assert len(ready_executable) <= 8, ready_executable
    assert any("[#153]" in line for line in ready_executable)
    assert any("[#135]" in line for line in ready_executable)
