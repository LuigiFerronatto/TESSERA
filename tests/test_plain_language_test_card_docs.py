from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = ROOT / "docs" / "test-cards"
INDEX = RECORDS_DIR / "README.md"
TEMPLATE = RECORDS_DIR / "TEMPLATE.md"

REQUIRED_HEADINGS = (
    "## In one sentence",
    "## What problem existed?",
    "## How did TESSERA behave before?",
    "## What changed or is being tested?",
    "## How does it work now?",
    "## Concrete example",
    "## How was it validated?",
    "## What improved?",
    "## What remains unimplemented?",
    "## What is unlocked next?",
    "## Technical provenance",
    "## Evolution",
)

REQUIRED_METADATA = (
    "| Issue |",
    "| Record status |",
    "| Capability type |",
    "| Pull request |",
    "| Merge commit |",
    "| Decision |",
    "| Benchmark applicability |",
    "| Last audited |",
)


def stage_records() -> list[Path]:
    return sorted(
        path
        for path in RECORDS_DIR.glob("*.md")
        if path.name not in {"README.md", "TEMPLATE.md"}
    )


def test_plain_language_record_system_has_index_template_and_records() -> None:
    assert INDEX.is_file()
    assert TEMPLATE.is_file()
    assert stage_records()


def test_each_stage_record_has_required_explanation_and_provenance() -> None:
    for path in stage_records():
        text = path.read_text(encoding="utf-8")
        for marker in REQUIRED_HEADINGS + REQUIRED_METADATA:
            assert marker in text, f"{path}: missing {marker!r}"

        assert "https://github.com/LuigiFerronatto/TESSERA/issues/" in text
        assert "CURRENT" in text or "current" in text
        assert "remain" in text.lower()


def test_index_links_every_versioned_stage_record() -> None:
    index = INDEX.read_text(encoding="utf-8")
    for path in stage_records():
        assert f"]({path.name})" in index, path


def test_template_preserves_open_vs_merged_status_boundary() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    for marker in REQUIRED_HEADINGS + REQUIRED_METADATA:
        assert marker in text

    assert "An open PR is never" not in text  # rule lives in the index
    assert "For planned/open work" in text
    assert "Not merged" in text
    assert "What remains unimplemented?" in text


def test_issue_and_pr_templates_require_stage_record() -> None:
    issue_template = (
        ROOT / ".github" / "ISSUE_TEMPLATE" / "test-card.md"
    ).read_text(encoding="utf-8")
    pr_template = (
        ROOT / ".github" / "pull_request_template.md"
    ).read_text(encoding="utf-8")

    assert "## Plain-language stage record" in issue_template
    assert "docs/test-cards/<issue>-<slug>.md" in issue_template
    assert "**Plain-language stage record:**" in pr_template
    assert "Plain-language stage record created/updated" in pr_template


def test_documentation_map_and_roadmap_link_stage_records() -> None:
    docs_map = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")

    assert "test-cards/README.md" in docs_map
    assert "docs/test-cards/" in roadmap
    assert "#109" in roadmap
    assert "0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2" in roadmap
