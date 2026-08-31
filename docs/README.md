# TESSERA — Documentation Map

This directory contains several generations of TESSERA documentation. Use this page as the navigation source of truth so current architecture, research notes and historical/prototype material are not confused.

## Executive takeaway

If you are new to TESSERA, read:

```text
OVERVIEW
  ↓
FEATURES + CONCEPTS
  ↓
ARCHITECTURE
  ↓
QUERY EXAMPLES / OUTPUT CONTRACT
  ↓
ROADMAP
```

If you are making an architecture decision, also read the relevant Test Card and `research/` notes before changing code.

---

# Start here — current product reference

| Document | Use it for |
|---|---|
| [OVERVIEW.md](OVERVIEW.md) | What TESSERA is, why it exists, current vs planned architecture. |
| [FEATURES.md](FEATURES.md) | Capabilities implemented on current Foundation. |
| [CONCEPTS.md](CONCEPTS.md) | Canonical vocabulary: drawers, identity, evidence, provenance, relevance, confidence, authority, relations. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical current-main architecture and module/pipeline boundaries. |
| [QUERY_EXAMPLES.md](QUERY_EXAMPLES.md) | Concrete current query/retrieval examples and known limitations. |
| [OUTPUT_CONTRACT.md](OUTPUT_CONTRACT.md) | Machine-facing semantic retrieval-result contract. |
| [ROADMAP.md](ROADMAP.md) | Experimental roadmap, Test Cards, priorities and future target architecture. |
| [test-cards/README.md](test-cards/README.md) | Plain-language stage records: what changed, how it works, evidence, limitations and next work. |
| [TEST_CARD_OPERATING_MODEL.md](TEST_CARD_OPERATING_MODEL.md) | Definition of Ready, WIP limits, execution waves, stop conditions and Codex handoff contract. |
| [BENCHMARK_CI.md](BENCHMARK_CI.md) | Versioned benchmark ledger, applicability levels, CI tiers, dataset integrity and artifact policy. |
| [adr/README.md](adr/README.md) | Accepted architecture decisions and binding module/public-contract boundaries. |

Current binding decision: [ADR 0001 — Core vs Optional LLM Orchestrator Boundary](adr/0001-core-vs-optional-llm-boundary.md).

---

# Change history and governance

TESSERA keeps product history, architecture rationale and experimental evidence separate on purpose.

| Artifact | Question it answers |
|---|---|
| [`../CHANGELOG.md`](../CHANGELOG.md) | **What changed** in the product/public contract? |
| [CHANGE_POLICY.md](CHANGE_POLICY.md) | **When and how** should a PR update the changelog? |
| [research/DECISION_TRACE.md](research/DECISION_TRACE.md) | **Why** did a research/architecture signal influence a decision? |
| [ROADMAP.md](ROADMAP.md) + linked Issues/Test Cards | **What are we trying to prove next?** |
| [test-cards/](test-cards/) | **What does each stage mean in plain language, and what remains unfinished?** |
| Pull request + CI/benchmark artifacts | **How was it implemented and what evidence passed?** |

Canonical separation:

```text
CHANGELOG
→ what changed

DECISION TRACE
→ why the direction changed

TEST CARD
→ what we tried to prove

PR
→ how it was implemented

PLAIN-LANGUAGE STAGE RECORD
→ understandable before/after, proof and limitations

CI / BENCHMARK
→ objective evidence
```

The changelog is curated manually. CI may later enforce that a PR explicitly updated it or declared N/A, but CI should not synthesize product history from commits.

---

# Research and competitive intelligence

Directory: [`research/`](research/)

| Document | Use it for |
|---|---|
| [research/REFERENCES.md](research/REFERENCES.md) | Primary papers/product references used by current project decisions. |
| [research/PAPER_NOTES.md](research/PAPER_NOTES.md) | What each paper says, what TESSERA learned, and which Test Card it influenced. |
| [research/COMPETITIVE_LANDSCAPE.md](research/COMPETITIVE_LANDSCAPE.md) | Mem0, Zep/Graphiti, Letta, LangGraph/LangMem, MemOS, MemPalace and research-system comparison. |
| [research/DECISION_TRACE.md](research/DECISION_TRACE.md) | Source → insight → Test Card → decision trace. |

Research hygiene:

```text
external source claim
≠ TESSERA interpretation
≠ TESSERA implementation
≠ TESSERA benchmark result
```

Competitive claims should be revalidated against current primary sources before publication outside the project.

---

# Experimental work lives in GitHub Issues

The repository follows:

```text
1 task
→ 1 Issue / Test Card
→ 1 linked implementation PR
→ evidence / CI / benchmark
→ KEEP | ITERATE | REVERT | DROP | DEFER
```

Use [ROADMAP.md](ROADMAP.md) for sequencing, but use the linked Issue as the living experiment record.

Current examples include:

```text
#68 Engine / CLI / MCP Contract Parity (closed)
#74 Core vs Optional LLM Boundary (accepted ADR 0001)
#12 Incremental & Idempotent Indexing
#69 Text Ingestion Coverage
#70 Structural Segmentation
#13 Metadata Doctor
#18 LongMemEval
#25 Query-aware Graph Expansion
#26 Relation Confidence
#27 Evidence Arbitration
#20 Evidence Sufficiency / Abstention
#32 Authority / Scope / Instruction Precedence
```

---

# Deep dives / implementation-oriented documents

These documents can still be useful, but they are narrower and may contain terminology from earlier iterations. Validate architecture claims against `OVERVIEW.md`, `FEATURES.md`, `ARCHITECTURE.md` and current code.

| Document | Role / caution |
|---|---|
| [CODE_EXPLANATION.md](CODE_EXPLANATION.md) | Code-oriented explanation. May lag module refactors; verify against current source. |
| [PROCEDURAL_ANCHORS.md](PROCEDURAL_ANCHORS.md) | Historical/current detail on procedural-anchor concept and skills. Do not infer that it creates a fourth semantic drawer. |
| [CHEATSHEET.md](CHEATSHEET.md) | Operational/reference cheat sheet; verify commands/contracts against current CLI. |
| [QUMEM-GAP-ANALYSIS.md](QUMEM-GAP-ANALYSIS.md) | Research/design gap analysis that influenced TESSERA. Treat as decision history, not current feature list. |

---

# Historical / narrative material

The following files preserve useful project history, demos or earlier architecture narratives. They are **not** the current product/architecture source of truth:

| Document | Classification |
|---|---|
| [COMO-FUNCIONA-E-PROXIMOS-PASSOS.md](COMO-FUNCIONA-E-PROXIMOS-PASSOS.md) | Historical/project narrative; may describe older roadmap assumptions. |
| [ROTEIRO-DEMO-VIDEO.md](ROTEIRO-DEMO-VIDEO.md) | Demo/presentation material, not technical contract. |
| [REFERENCES.md](REFERENCES.md) | Older compact reference list; prefer `research/REFERENCES.md` for current research decision trace. |
| `archive/` | Explicit older implementation/version material when present. |

Historical docs should preserve useful decision history, but they must not define the current public product contract. Project-specific legacy narratives are tracked for cleanup separately.

---

# Which document wins when docs disagree?

Use this precedence for **project-status claims**:

```text
current code + tests
        ↓
current linked Issue/Test Card / merged PR evidence
        ↓
FEATURES.md / ARCHITECTURE.md / OUTPUT_CONTRACT.md
        ↓
OVERVIEW.md / ROADMAP.md
        ↓
deep-dive docs
        ↓
historical/demo docs
```

For **external research/product claims**, current primary sources win over repository prose; update the research docs when discrepancies are found.

---

# Documentation maintenance rule

When a feature changes:

```text
implementation PR
  ↓
update CHANGELOG or explicitly mark N/A
  ↓
update its Test Card with evidence/learnings
  ↓
create/update its plain-language stage record
  ↓
update FEATURES/ARCHITECTURE/OUTPUT_CONTRACT if public semantics changed
  ↓
update ROADMAP if the decision changes sequencing
  ↓
update research decision trace if an external idea materially influenced the change
```

Do not let a feature become “implemented” only in a PR description. If it changes the product contract, current documentation and product history should move with it.
