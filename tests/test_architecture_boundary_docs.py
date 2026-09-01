from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADR = ROOT / "docs" / "adr" / "0001-core-vs-optional-llm-boundary.md"
ROADMAP = ROOT / "docs" / "ROADMAP.md"
ISSUE_95_AUDIT = ROOT / "docs" / "PR_EVOLUTION_95.md"
ISSUE_115_AUDIT = ROOT / "docs" / "PR_EVOLUTION_115.md"
ISSUE_116_AUDIT = ROOT / "docs" / "PR_EVOLUTION_116.md"
LAYOUT_ADR = ROOT / "docs" / "adr" / "0002-repository-layout-and-distribution-boundary.md"
ISSUE_93_AUDIT = ROOT / "docs" / "PR_EVOLUTION_93.md"
CANONICAL_95_MERGE_SHA = "6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599"
ISSUE_115_CANDIDATE_SHA = "25afd31b910dec97cffea34a25092c6e7f8b4f2e"
CANONICAL_115_MERGE_SHA = "b475f1cd805f86cc8ad9526e563e3c6fb8409ff1"


def _markdown_table_row(text: str, issue: str) -> str:
    prefix = f"| [{issue}]"
    rows = [line for line in text.splitlines() if line.startswith(prefix)]
    assert len(rows) == 1, (issue, rows)
    return rows[0]


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
        "#124", "#108", "#125",
    ):
        assert pr in audit
    assert "27 distinct merged deliveries" in audit
    assert "9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05" in audit
    assert "CLOSED_UNMERGED" in audit
    assert "NOT_RERUN" in audit
    assert "LongMemEval V1 dev-50" in audit


def test_issue_95_lifecycle_and_dependency_routing_are_reconciled() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    audit = ISSUE_95_AUDIT.read_text(encoding="utf-8")

    issue_95 = _markdown_table_row(roadmap, "#95")
    issue_67 = _markdown_table_row(roadmap, "#67")
    issue_115 = _markdown_table_row(roadmap, "#115")
    issue_116 = _markdown_table_row(roadmap, "#116")

    assert "#95" in roadmap
    assert CANONICAL_95_MERGE_SHA in roadmap
    assert "`VALIDATED`" in issue_95

    assert "[#126]" in audit
    assert CANONICAL_95_MERGE_SHA in audit
    assert "Candidate/squash deduplication" in audit
    assert "one runtime delivery" in audit

    assert "`BLOCKED`" in issue_67
    assert "#92, #93 and #95 dependencies are satisfied" in issue_67
    assert "still blocked on regression-gate integration" in issue_67
    assert "still depends on #93, #95" not in issue_67
    assert "`VALIDATED`" in issue_115
    assert CANONICAL_115_MERGE_SHA in issue_115
    assert "`VALIDATED`" in issue_116
    assert "0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4" in issue_116


def test_repository_layout_adr_defines_distribution_ownership_without_migration() -> None:
    text = LAYOUT_ADR.read_text(encoding="utf-8")

    for marker in (
        "**Status:** Accepted",
        "Audited main:** `5d43a2d4cdda0c17be6516f47920121070339d0f`",
        "Option A",
        "Option B",
        "Option C",
        "`PACKAGE_RUNTIME`",
        "`BENCHMARK_TOOLING`",
        "`HISTORICAL_PROVENANCE`",
        "Target dependency rules",
        "#116",
        "#117",
        "#118",
        "#119",
        "#120",
        "#121",
        "No item is approved for immediate deletion",
    ):
        assert marker in text

    assert "src/tessera" in text
    assert "Runtime may import only runtime" in text
    assert "Issue #115 accepts the plan, not its migrations" in text


def test_issue_115_audit_records_current_artifacts_and_no_runtime_scope() -> None:
    audit = ISSUE_115_AUDIT.read_text(encoding="utf-8")

    for marker in (
        "146 tracked files",
        "128 internal import edges",
        "Wheel — 46 files",
        "Sdist — 69 files",
        "KEEP / MOVE / ARCHIVE / DELETE / SPLIT / DEFER",
        "RUNTIME_IMPLEMENTATION",
        "PACKAGING",
        "DOCUMENTATION_CORRECTION",
        "GOVERNANCE",
        "ARCHITECTURE_DECISION",
        "BENCHMARK_INFRASTRUCTURE",
        "SUPERSEDED_OPERATIONAL_PR",
        "No path is classified `DEAD`",
        "git diff origin/main -- tessera/",
        "LongMemEval V1 is not rerun",
    ):
        assert marker in audit

    assert "benchmark Python packages are accidentally/incompletely shipped" in audit
    assert "No new child Test Card is necessary now" in audit


def test_issue_115_post_merge_lifecycle_unlocks_only_116() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    issue_115 = _markdown_table_row(roadmap, "#115")
    issue_116 = _markdown_table_row(roadmap, "#116")

    assert "closed" in issue_115
    assert "`VALIDATED`" in issue_115
    assert "ADR 0002" in issue_115
    assert "PR #128" in issue_115
    assert CANONICAL_115_MERGE_SHA in issue_115
    assert "`KEEP`" in issue_115
    assert "`VALIDATED`" in issue_116
    assert "0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4" in issue_116

    assert "`READY`" in _markdown_table_row(roadmap, "#117")
    for issue in ("#118", "#119", "#120", "#121"):
        assert "`BLOCKED`" in _markdown_table_row(roadmap, issue)


def test_issue_115_canonical_delivery_is_deduplicated() -> None:
    audit = ISSUE_115_AUDIT.read_text(encoding="utf-8")
    record = (ROOT / "docs/test-cards/115-repository-layout-architecture.md").read_text(
        encoding="utf-8"
    )

    for marker in (
        "PR #128",
        "`ARCHITECTURE_DECISION`",
        ISSUE_115_CANDIDATE_SHA,
        CANONICAL_115_MERGE_SHA,
        "squash",
        "one architecture delivery",
        "`KEEP`",
        "implementation applicability is `SMOKE_ONLY`",
        "lifecycle synchronization applicability is `NOT_APPLICABLE`",
        "`DOCUMENTATION_CORRECTION`",
        "PR #130",
    ):
        assert marker in audit

    assert "| Record status | `VALIDATED` |" in record
    assert ISSUE_115_CANDIDATE_SHA in record
    assert CANONICAL_115_MERGE_SHA in record
    assert "**VALIDATED ON `main`.**" in record
    assert "migrations are not implemented" in record


def test_issue_93_post_merge_lifecycle_and_dependency_routing_are_truthful() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    audit = ISSUE_93_AUDIT.read_text(encoding="utf-8")

    issue_93 = _markdown_table_row(roadmap, "#93")
    issue_67 = _markdown_table_row(roadmap, "#67")

    assert "closed" in issue_93
    assert "`VALIDATED`" in issue_93
    assert "`KEEP`" in issue_93
    assert "c6124548f32b6dc5e1b7acf5127632bc6c75fccc" in issue_93
    assert "PR_EVOLUTION_93.md" in issue_93
    assert "5d43a2d4cdda0c17be6516f47920121070339d0f" in audit
    for delivery in ("#83", "#98", "#108", "#126", "#127"):
        assert delivery in audit
    assert "#128" in audit
    assert "b475f1cd805f86cc8ad9526e563e3c6fb8409ff1" in audit
    assert "parallel architecture delivery, not part of #93" in audit
    assert "candidate and merge counted once" in audit
    assert "already satisfied by #95" in audit
    assert "still broken" in audit
    assert "SMOKE_ONLY" in audit
    assert "NOT_APPLICABLE" in audit
    assert "c460e2f1c7d477a40f046e5e54da8d71aee45bac" in audit
    assert "c6124548f32b6dc5e1b7acf5127632bc6c75fccc" in audit
    assert "one runtime delivery" in audit
    assert "DOCUMENTATION_CORRECTION" in audit
    assert "LongMemEval V1 dev-50 remains `NOT_RERUN`" in audit

    assert "`BLOCKED`" in issue_67
    assert "#92, #93 and #95 dependencies are satisfied" in issue_67
    assert "still blocked on regression-gate integration" in issue_67


def test_issue_116_tracks_distribution_without_starting_downstream_work() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    audit = ISSUE_116_AUDIT.read_text(encoding="utf-8")
    record = (ROOT / "docs/test-cards/116-packaging-hardening.md").read_text(
        encoding="utf-8"
    )

    assert "`VALIDATED`" in _markdown_table_row(roadmap, "#116")
    assert "`READY`" in _markdown_table_row(roadmap, "#117")
    for issue in ("#118", "#119", "#120", "#121"):
        assert "`BLOCKED`" in _markdown_table_row(roadmap, issue)

    for marker in (
        "055a35f4a7e8298013bcb816b30f67d9706b9516",
        "Wheel before — 46 files",
        "Sdist before — 77 entries",
        "candidate wheel contains 30 files",
        "sdist contains 40",
        "BASE_RUNTIME_REQUIRED",
        "OPTIONAL_RUNTIME",
        "DEV_ONLY",
        "#87 owns the standalone license",
        "No misleading benchmark extra",
        "65f42d76a7bfbd88f4d2b35f977f91848810e23a",
        "PR #132",
        "0adb147075c25e1c442c1e310763eb66ca04c567",
        "0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4",
        "one `PACKAGING` delivery",
        "`DOCUMENTATION_CORRECTION`",
    ):
        assert marker in audit

    assert "| Record status | `VALIDATED` |" in record
    assert "VALIDATED ON `main`" in record
    assert "LongMemEval remains skipped" in record
