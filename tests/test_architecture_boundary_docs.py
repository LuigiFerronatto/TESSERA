from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0001-core-vs-optional-llm-boundary.md"


def test_core_optional_llm_adr_contains_binding_contract() -> None:
    text = ADR.read_text(encoding="utf-8")

    required = (
        "**Status:** Accepted",
        "CURRENT",
        "TARGET",
        "DEPRECATED",
        "PROPOSED FOLLOW-UP",
        "## Responsibility matrix",
        "## Dependency rules",
        "## Evidence and provenance invariants",
        "## LLM-as-a-judge boundary",
        "## Abstention boundary",
        "Benchmark applicability:** `NOT_APPLICABLE`",
        "O0 — Deterministic retrieval",
        "O1 — Deterministic query compilation",
        "O2 — Optional LLM-assisted planning",
        "O3 — Optional context consolidation",
        "O4 — External reader",
    )
    for marker in required:
        assert marker in text


def test_adr_assigns_one_owner_to_every_required_capability() -> None:
    text = ADR.read_text(encoding="utf-8")
    rows = (
        "canonical memory ingestion",
        "indexing",
        "deterministic retrieval",
        "ranking",
        "graph and metadata access",
        "provenance",
        "deterministic query compilation",
        "LLM-assisted planning",
        "context consolidation",
        "answer synthesis",
        "final answer policy",
        "abstention decision",
        "citations in a final answer",
        "LLM-as-a-judge",
        "benchmark scoring",
    )
    for capability in rows:
        matches = [line for line in text.splitlines() if line.startswith(f"| {capability} |")]
        assert len(matches) == 1
        assert matches[0].count("|") == 4


def test_current_docs_link_the_accepted_adr() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "docs" / "FEATURES.md",
        ROOT / "docs" / "CHEATSHEET.md",
        ROOT / "docs" / "README.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "0001-core-vs-optional-llm-boundary.md" in text, path

