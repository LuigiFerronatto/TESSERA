# TESSERA — Documentation Map

Docs are grouped by what you are trying to do. Folder names say what kind of document you are reading:

```text
docs/
├── guides/        use TESSERA: commands, queries, walkthroughs
├── concepts/      understand TESSERA: what it is, vocabulary, capabilities
├── reference/     machine-facing contracts: output, write gate, MCP runtime, model profiles, harness adapters
├── architecture/  how the code is built + accepted decisions (adr/)
├── process/       how the project is run: roadmap, Test Cards, CI, governance, evidence
├── research/      external papers, competitors, decision trace, fidelity map
├── history/       per-issue evolution audits (pr-evolution/<issue>.md)
└── assets/        brand assets
```

---

## 1. Use it

| Document | Use it for |
|---|---|
| [guides/cheatsheet.md](guides/cheatsheet.md) | Operational cheat sheet: CLI commands, MCP tools, common flows. Verify against the current CLI. |
| [guides/query-examples.md](guides/query-examples.md) | Concrete query/retrieval examples and known limitations. |
| [reference/mcp-runtime.md](reference/mcp-runtime.md) | MCP runtime contract: startup, stdio, schema, errors and cancellation (#120). |
| [reference/model-profiles.md](reference/model-profiles.md) | Model profiles for the optional LLM paths. |

## 2. Understand it

Suggested reading order for newcomers:

```text
concepts/overview → concepts/features + concepts/concepts → architecture/architecture
  → guides/query-examples + reference/output-contract → process/roadmap
```

| Document | Use it for |
|---|---|
| [concepts/overview.md](concepts/overview.md) | What TESSERA is, why it exists, current vs planned architecture. |
| [concepts/features.md](concepts/features.md) | Capabilities implemented on the current Foundation. |
| [concepts/concepts.md](concepts/concepts.md) | Canonical vocabulary: drawers, identity, evidence, provenance, relevance, confidence, authority, relations. |
| [concepts/procedural-anchors.md](concepts/procedural-anchors.md) | Procedural-anchor concept and skills. It does not create a fourth semantic drawer. |
| [architecture/architecture.md](architecture/architecture.md) | Technical current-main architecture and module/pipeline boundaries. |
| [architecture/long-term-memory.md](architecture/long-term-memory.md) | Proposed durable-memory boundary; current and target ownership are explicit, no runtime promotion. |
| [architecture/code-explanation.md](architecture/code-explanation.md) | Code-oriented walkthrough. May lag module refactors; verify against current source. |
| [architecture/adr/README.md](architecture/adr/README.md) | Accepted architecture decisions and binding module/public-contract boundaries. |
| [reference/output-contract.md](reference/output-contract.md) | Machine-facing semantic retrieval-result contract. |
| [reference/write-gate-contract.md](reference/write-gate-contract.md) | Write-gate contract: what may be stored and how. |
| [architecture/architecture-diagrams.md](architecture/architecture-diagrams.md) | Versioned current/experimental SVG diagrams and source mappings. |
| [reference/harness-adapters.md](reference/harness-adapters.md) | Harness adapter registry: how instruction files (AGENTS.md, CLAUDE.md, …) are classified, and how to register a custom adapter (#71). |

Current binding decision: [ADR 0001 — Core vs Optional LLM Orchestrator Boundary](architecture/adr/0001-core-vs-optional-llm-boundary.md).

## 3. Contribute / project process

Start with [`../CONTRIBUTING.md`](../CONTRIBUTING.md), then:

| Document | Use it for |
|---|---|
| [process/roadmap.md](process/roadmap.md) | Experimental roadmap, Test Cards, priorities and future target architecture. |
| [process/test-cards/README.md](process/test-cards/README.md) | Plain-language stage records: what changed, how it works, evidence, limitations and next work. |
| [process/test-card-operating-model.md](process/test-card-operating-model.md) | Definition of Ready, WIP limits, execution waves, stop conditions and Codex handoff contract. |
| [process/change-policy.md](process/change-policy.md) | When and how a PR updates the changelog. |
| [process/benchmark-ci.md](process/benchmark-ci.md) | Versioned benchmark ledger, applicability levels, CI tiers, dataset integrity and artifact policy. |
| [process/agentic-governance.md](process/agentic-governance.md) | Repository-process automation: issue triage, PR audit, opt-in fixer, merge governor, post-merge lifecycle reconciliation, documentation drift audits. Not a product/runtime feature. |
| [process/project-board-sync.md](process/project-board-sync.md) | How the GitHub project board is kept in sync with issues and PRs. |
| [process/evidence/](process/evidence/) | Raw evidence attached to Test Cards. |

The repository follows:

```text
1 task → 1 Issue / Test Card → 1 linked implementation PR → evidence / CI / benchmark
       → KEEP | ITERATE | REVERT | DROP | DEFER
```

Use the roadmap for sequencing, but the linked Issue is the living experiment record.

### Where each kind of history lives

| Artifact | Question it answers |
|---|---|
| [`../CHANGELOG.md`](../CHANGELOG.md) | **What changed** in the product/public contract? |
| [research/decision-trace.md](research/decision-trace.md) | **Why** did a research/architecture signal influence a decision? |
| [research/memory-lifecycle-2026-10-02.md](research/memory-lifecycle-2026-10-02.md) | Versioned five-system × ten-dimension lifecycle matrix, pinned code/docs claims, bounded unknowns and existing-system comparisons. |
| [process/roadmap.md](process/roadmap.md) + linked Issues/Test Cards | **What are we trying to prove next?** |
| [process/test-cards/](process/test-cards/) | **What does each stage mean in plain language, and what remains unfinished?** |
| [history/pr-evolution/](history/pr-evolution/) | **How did an issue evolve** across its PRs and reviews? |
| Pull request + CI/benchmark artifacts | **How was it implemented and what evidence passed?** |

The changelog is curated manually. CI may enforce that a PR updated it or declared N/A, but CI does not synthesize product history from commits.

### Documentation maintenance rule

```text
implementation PR
  → update CHANGELOG or explicitly mark N/A
  → update its Test Card with evidence/learnings and its plain-language stage record
  → update concepts/features, architecture/architecture, reference/output-contract if public semantics changed
  → update process/roadmap if the decision changes sequencing
  → update research/decision-trace if an external idea materially influenced the change
```

Do not let a feature become "implemented" only in a PR description.

## 4. Research

| Document | Use it for |
|---|---|
| [research/qumem-gap-analysis.md](research/qumem-gap-analysis.md) | Canonical source-to-implementation fidelity map with dated code baseline and validation owners. |
| [research/references.md](research/references.md) | Primary papers/product references used by current project decisions. |
| [research/paper-notes.md](research/paper-notes.md) | What each paper says, what TESSERA learned, and which Test Card it influenced. |
| [research/memory-papers-2026-09-07.md](research/memory-papers-2026-09-07.md) | Dated review of 28 main AI-memory papers plus one supplementary source. |
| [research/improvement-map-2026-09-07.md](research/improvement-map-2026-09-07.md) | 48 proposed opportunities checked against the 82-issue audit snapshot; candidates, not a roadmap. |
| [research/competitive-landscape.md](research/competitive-landscape.md) | Mem0, Zep/Graphiti, Letta, LangGraph/LangMem, MemOS, MemPalace and research-system comparison. |
| [research/decision-trace.md](research/decision-trace.md) | Source → insight → Test Card → decision trace. |

Research hygiene:

```text
external source claim ≠ TESSERA interpretation ≠ TESSERA implementation ≠ TESSERA benchmark result
```

Revalidate competitive claims against current primary sources before publishing them outside the project.

## 5. History and older narratives

Not the current product/architecture source of truth:

| Document | Classification |
|---|---|
| [history/pr-evolution/](history/pr-evolution/) | Per-issue evolution audits, e.g. [#120](history/pr-evolution/120.md). |
| [guides/how-it-works-pt.md](guides/how-it-works-pt.md) | Portuguese project narrative; may describe older roadmap assumptions. |
| [research/references-pt.md](research/references-pt.md) | Older compact Portuguese reference list; prefer [research/references.md](research/references.md). |

Historical docs should preserve useful decision history, but they must not define the current public product contract. Legacy examples are project-neutral. Exact prior identifiers and presentation artwork remain available through pinned Git-history links; historical claims never override current contracts.

---

## Which document wins when docs disagree?

For **project-status claims**:

```text
current code + tests
  → current linked Issue/Test Card / merged PR evidence
  → concepts/features, architecture/architecture, reference/output-contract
  → concepts/overview, process/roadmap
  → deep-dive docs
  → history and narrative docs
```

For **external research/product claims**, current primary sources win over repository prose; update the research docs when they disagree.
