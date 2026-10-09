"""Guard the distinction between research inspiration and validated behavior."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_paper_code_status_and_owner_are_explicit():
    text = (ROOT / "docs/QUMEM-GAP-ANALYSIS.md").read_text(encoding="utf-8")
    assert "20814a47ec0f72d7bea0639e0b057df1ecf5cded" in text
    assert "https://arxiv.org/html/2608.16168v1" in text
    assert "| Concept | Paper behavior | TESSERA main" in text
    assert "full QUMem fidelity is not validated" in text
    for issue in range(135, 147):
        assert f"#{issue}" in text
    for phrase in (
        "TESSERA-specific extension", "one mixed-type call",
        "one free-text sentence", "one query", "free-text consolidated context",
        "not an immutable truth", "valid JSON list, including `[]`",
        "MCP reports failed assistance", "**WHAT**", "**HOW**",
        "#20 separately owns evidence", "unmerged PR never promotes",
    ):
        assert phrase in " ".join(text.split()), phrase
    assert "✅ IMPLEMENTADO" not in text


def test_current_entrypoints_link_the_fidelity_map():
    for name in ("README.md", "docs/README.md", "docs/research/REFERENCES.md", "docs/ROADMAP.md"):
        assert "QUMEM-GAP-ANALYSIS.md" in (ROOT / name).read_text(encoding="utf-8"), name


def test_docstrings_name_the_actual_baseline_without_changing_prompts():
    docs = {}
    for name in ("decomposer", "episode_boundary", "orchestrator"):
        tree = ast.parse((ROOT / f"tessera/{name}.py").read_text(encoding="utf-8"))
        docs[name] = ast.get_docstring(tree)
        assert "QUMEM-GAP-ANALYSIS.md" in docs[name]
    assert "one mixed-type extraction call" in docs["decomposer"]
    assert "does not distinguish user" in docs["episode_boundary"]
    assert "free text" in docs["orchestrator"]


def test_merged_documentation_record_cannot_promote_runtime_fidelity():
    text = (ROOT / "docs/test-cards/146-qumem-fidelity-documentation.md").read_text(encoding="utf-8")
    header = text.split("## In one sentence", 1)[0]
    assert "| Record status | `IMPLEMENTED` |" in header
    assert "| Decision | `PENDING`" in header
    assert "b5381e93df68006b02a32bf410398f0cfc49dc4c" in header
    assert "0a4a22c3b356c191a6f30c555eb01677ac2b85a4" in header
    assert "Not merged" not in text
    assert "37849579311" in text and "37849579474" in text
    assert "historical BLOCK" in text
    assert "No runtime dependency is unlocked" in text
