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


def test_roadmap_uses_reconciled_status_contract() -> None:
    text = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")

    for status in (
        "`IMPLEMENTED`",
        "`VALIDATED`",
        "`READY`",
        "`IN_PROGRESS`",
        "`BLOCKED`",
        "`DEFERRED`",
        "`TRACKER`",
        "`DROPPED`",
        "`SUPERSEDED`",
    ):
        assert status in text

    for issue in ("#68", "#74", "#94", "#96", "#100", "#103", "#104", "#105", "#106"):
        assert issue in text

    assert "## Reconciliation matrix" in text
    assert "#28 rendering ablation" in text
    assert "#25 graph-expansion card DoR completion" in text
    assert "LongMemEval V1 dev-50 historical" in text
    assert "deterministic sanity fixture" in text
    assert "✅" not in text
    assert "🟡" not in text
    assert "⬜" not in text


def test_write_gate_contract_and_roadmap_evolution_are_documented() -> None:
    contract = (ROOT / "docs" / "WRITE_GATE_CONTRACT.md").read_text(encoding="utf-8")
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")

    for marker in (
        "detection",
        "optional deterministic transformation",
        "admission decision",
        "atomic Markdown persistence",
        "accept_sanitized",
        "review",
        "content_changed",
        "original_hash",
        "persisted_hash",
        "not a semantic",
    ):
        assert marker in contract
    assert "merge `0c0b638`" in roadmap
    assert "https://github.com/LuigiFerronatto/TESSERA/pull/107" in roadmap
    assert "0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2" in roadmap
    assert "https://github.com/LuigiFerronatto/TESSERA/pull/108" in roadmap
    assert "PR_EVOLUTION_92.md" in roadmap
    assert "| [#92]" in roadmap and "9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05" in roadmap
    assert "`VALIDATED`" in roadmap
    assert "| [#19]" in roadmap and "BLOCKED" in roadmap


def test_issue_92_pr_evolution_audit_is_complete_and_deduplicated() -> None:
    audit = (ROOT / "docs" / "PR_EVOLUTION_92.md").read_text(encoding="utf-8")

    for classification in (
        "RUNTIME_IMPLEMENTATION",
        "BENCHMARK_INFRASTRUCTURE",
        "DOCUMENTATION_CORRECTION",
        "GOVERNANCE",
        "ARCHITECTURE_DECISION",
        "SUPERSEDED_OPERATIONAL_PR",
    ):
        assert classification in audit
    for pr in (
        "#6", "#53", "#61", "#79", "#83", "#98", "#99", "#101",
        "#102", "#107", "#110", "#111", "#113", "#122", "#123",
        "#124", "#108",
    ):
        assert pr in audit
    assert "27 distinct merged deliveries" in audit
    assert "9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05" in audit
    assert "CLOSED_UNMERGED" in audit
    assert "NOT_RERUN" in audit
    assert "LongMemEval V1 dev-50" in audit
