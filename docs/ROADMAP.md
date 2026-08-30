# TESSERA — Experimental Roadmap

TESSERA is an **agent-agnostic, text-first memory and evidence layer**. It hides storage, indexing, relations, temporal metadata and retrieval mechanics while preserving enough **evidence, provenance and navigation** for the consuming agent to reason for itself.

> **TESSERA abstracts memory architecture away from the agent. It does not replace the cognition of the agent.**

## Executive takeaway

The current Foundation already proves **stable identity, explainable retrieval, query-aware evidence, provenance and deterministic CI**. Before adding more intelligence, the next cycle hardens the public/product contract, makes indexing incremental and measurable, and starts external evaluation early.

Recent research refines later experiments without changing the product boundary:

```text
GraphMemix → query-aware graph expansion + evidence budget
CaSKG      → relation origin/confidence/validation
MemToC     → evidence arbitration + four-state evidence status
RENDER     → retrieval quality ≠ renderer quality
```

Those are **research signals and Test Cards**, not implemented capabilities.

---

# Product invariants

- Source text is the source of truth; index/cache/ledger are derived and rebuildable.
- TESSERA returns **structured evidence**, not the final answer for the consuming agent.
- Exactly **3 semantic drawers** remain: `facts`, `preferences`, `insights`.
- `document_type`, harness, scope, temporal state, authority, confidence, relations, quality and utility are facets/metadata — not new drawers.
- TESSERA is text-first and auditable; source code is not primary memory.
- No generative LLM is mandatory in the basic path.
- Retrieval relevance ≠ confidence ≠ authority ≠ relation confidence ≠ temporal validity ≠ utility.
- User source files are never silently rewritten during indexing.
- A relation existing ≠ the relation being trustworthy ≠ the relation being useful for the current query.
- A conflict being detected ≠ the conflict being resolved.
- Public docs, examples, fixtures and CI must remain project-agnostic.

---

# Delivery model: Issue → Test Card → PR → Evidence → Decision

Every meaningful change starts as a hypothesis, not as a presumed feature.

1. Open one **Issue/Test Card** for one unit of work or decision.
2. Record hypothesis, baseline, experiment, metrics and failure signals before implementation.
3. Open a linked PR (`Closes #...` when applicable).
4. Explain the PR at three levels: **Executive takeaway**, **plain language**, **technical implementation**.
5. Record real outputs, CI/benchmark evidence and learnings.
6. Update the changelog or explicitly mark the change as N/A according to #65/#66.
7. Record a decision: **KEEP / ITERATE / REVERT / DROP / DEFER**.
8. Follow-up work becomes a new Issue instead of a hidden TODO.

Templates:
- `.github/ISSUE_TEMPLATE/test-card.md`
- `.github/pull_request_template.md`

Documentation/governance tracker: **Issue #38**.

---

# Authoritative execution portfolio — 2026-08-30

The open-issue portfolio was audited against the current runtime and cited research. The dependency graph below supersedes older status/dependency notes later in this document and inside historical issue sections.

## M0 — Contract & Safety

| Order | Issue | Decision |
| --- | --- | --- |
| 1 | #68 | Golden Engine/CLI/MCP response contract |
| 2 | #92 | Truthful write-gate and sanitization metadata |
| 3 | #93 | Canonical storage configuration across surfaces |
| 4 | #94 | Support JSON end-to-end or reject it before write |
| 5 | #95 | Remove legacy LAO/Blip runtime coupling |
| 6 | #67 | Encode #68/#92–#95 as regression gates |
| 7 | #74 | Decide deterministic core versus optional LLM boundary |
| 8 | #16 | Contain the silent heuristic resolver before the full M4 experiment |

## M1–M5

```text
M1  #96 LongMemEval V1 baseline → #28 rendering ablation
 ↓
M2  #12 → #69 → #70 → #13 → #73
 ↓
M3  #14 epic → #25 baseline/budget → #26 edge trust
 ↓
M4  #15; #71 → #32 → #72; then #16 → #27 → #20
 ↓
M5  #19 → #17/#74 assisted-mode ablation → #21
```

Rules:

- #14, #18 and #38 are epics/trackers and do not produce direct implementation PRs.
- #18 depends only on #68 for its first executable child, #96.
- Feature cards depend on the benchmark; benchmark reruns are evidence and never reverse dependencies.
- Policy (#32) precedes resolver (#72).
- The architecture decision (#74) precedes adaptive implementation (#17).
- Maximum WIP is two implementation cards plus one benchmark/documentation lane.
- See [TEST_CARD_OPERATING_MODEL.md](TEST_CARD_OPERATING_MODEL.md) for Definition of Ready, stop conditions and the Codex handoff contract.

---

# Current status

## Foundation — implemented

| Status | Issue | Capability | Implementation |
| --- | --- | --- | --- |
| ✅ | #7 | Output Contract | PR #1 merged |
| ✅ | #8 | Explainable Ranking + Query-aware Evidence | PR #2 merged |
| ✅ | #9 | Canonical Metadata + Classification + Stable Identity | PR #3 merged |
| ✅ | #10 | CI + deterministic sanity evaluation | PR #4 merged |
| ✅ | #11 | Evidence Ledger + Provenance | PR #6 merged |

## Public foundation / governance — current cycle

| Status | Issue | Workstream |
| --- | --- | --- |
| 🟡 | #62 | Enforce project-agnostic public surface |
| ⬜ | #63 | README vNext — executive + colloquial + technical entrypoint |
| ⬜ | #64 | Versioned brand / visual documentation assets |
| ⬜ | #65 | Human-readable CHANGELOG + change policy |
| ⬜ | #66 | PR contract v2 — changelog/evidence/decision requirements |
| ⬜ | #67 | CI Quality Gate v2 — governance/docs checks |
| 🟡 | #75 | Roadmap vNext synchronization |

## Foundation — next technical hardening

| Status | Issue | Capability / experiment |
| --- | --- | --- |
| ⬜ | #68 | Engine / CLI / MCP retrieval contract parity |
| ⬜ | #12 | Incremental & Idempotent Indexing |
| ⬜ | #69 | Text ingestion coverage beyond Markdown |
| ⬜ | #70 | Structural segmentation without source-fidelity loss |
| ⬜ | #13 | Metadata Doctor / corpus diagnostics |

## Intelligence — structure and retrieval experiments

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #14 | Typed Relations + controlled graph expansion |
| ⬜ | #25 | Query-aware graph expansion + evidence budget |
| ⬜ | #26 | Relation origin + confidence + validation |
| ⬜ | #15 | Temporal Model + State Keys |
| ⬜ | #71 | Harness Adapter Registry |
| ⬜ | #72 | Instruction Resolver — applicability/scope/precedence |
| ⬜ | #32 | Source authority + scope + instruction precedence |
| ⬜ | #73 | Versioned memory/source revision history |
| ⬜ | #16 | Conflict Resolution + Supersession |
| ⬜ | #27 | Evidence / Source Arbitration |

## Adaptive / orchestration

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #17 | Query Compiler + Adaptive Retrieval |
| ⬜ | #74 | Core vs optional LLM orchestrator boundary |
| ⬜ | #19 | Write Gating / Memory Admission |

## Evaluation / state

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #18 | LongMemEval V1/V2 adapters + ablations |
| ⬜ | #28 | RAW vs EVIDENCE vs STRUCTURED rendering ablation |
| ⬜ | #20 | State Reconstruction + Evidence Sufficiency + Abstention |

## Learning — only after the previous layers earn their complexity

| Status | Issue | Experiment |
| --- | --- | --- |
| ⬜ | #21 | Experience Traces + Derived Insights + Utility Feedback |

---

# Superseded execution order — historical reference

> The sequence below predates the 2026-08-30 portfolio audit and is retained only to explain earlier roadmap assumptions. Use the authoritative execution portfolio above and the routing block in each open issue.

```text
PUBLIC FOUNDATION / GOVERNANCE
  #62 Project-agnostic public surface
      ↓
  #63 README vNext
  #64 Visual assets
      ↓
  #65 CHANGELOG policy
      ↓
  #66 PR contract v2
      ↓
  #67 CI Quality Gate v2
      ↓
FOUNDATION CONTRACT
  #68 Engine / CLI / MCP contract parity
      ↓
INDEXING / INGESTION
  #12 Incremental & Idempotent Indexing
      ↓
  #69 Text ingestion coverage
      ↓
  #70 Structural segmentation
      ↓
  #13 Metadata Doctor
      ↓
MEASURE EARLY
  #18 LongMemEval baseline / adapter
    └─ #28 Renderer control starts here
      ↓
RELATIONS ABLATIONS
  #14 Typed Relations / controlled expansion
    ├─ #25 Query-aware evidence budget
    └─ #26 Relation confidence / validation
      ↓
TEMPORAL + INSTRUCTIONS
  #15 Temporal Model + State Keys
  #71 Harness Adapter Registry
  #72 Instruction Resolver
  #32 Authority / scope / precedence
  #73 Revision history
      ↓
CONFLICT / TRUST
  #16 Conflict / Supersession
    └─ #27 Evidence Arbitration
      ↓
ADAPTIVE
  #17 Query Compiler / Adaptive Retrieval
  #74 Core vs optional LLM orchestrator
  #19 Memory Admission
      ↓
STATE / ABSTENTION
  #20 State Reconstruction + four-state evidence status
      ↓
LEARNING
  #21 Experience + Utility
```

The ordering is not a claim that every capability will ship. Each feature must earn **KEEP** through its Test Card.

---

# Research-derived experiment map

| Research signal | TESSERA Test Card | Question we measure |
| --- | --- | --- |
| GraphMemix | #25 | Does query-aware/budgeted expansion outperform indiscriminate 1-hop in quality/cost? |
| CaSKG | #26 | Does relation confidence/validation reduce harmful expansion without destroying recall? |
| MemToC | #27 | Does Evidence Arbitration improve source selection and abstention versus a silent winner? |
| MemToC | #20 | Do `sufficient / insufficient / conflicting / ambiguous` improve downstream control flow? |
| MemToC + harness scope | #32/#72 | Do authority + scope + precedence resolve instructions better than newest/relevance wins? |
| RENDER | #28 | Does reader-facing rendering change downstream QA when the evidence set is frozen? |

### Relations: four dimensions that must stay separate

```text
relation_type
→ what the relation means

relation_origin
→ where the relation came from

relation_confidence
→ how strongly we believe the edge is correct

query_relevance
→ whether the edge is useful for this query
```

### Future evidence-status contract

```text
sufficient
→ continue

insufficient
→ search / expand

conflicting
→ inspect provenance / arbitration

ambiguous
→ verify / ask / tool call
```

TESSERA provides infrastructure signals; the consuming agent keeps the final cognitive decision.

---

# Foundation pipeline — what exists today

```text
TEXT FILES
   ↓
① DISCOVER
   ↓
② UNDERSTAND
   ├── document type
   ├── metadata
   ├── scope
   └── semantic drawer
   ↓
③ NORMALIZE
   ├── explicit metadata
   ├── inferred metadata
   └── stable identity
   ↓
④ TRACE
   ├── source
   ├── spans
   ├── hashes
   └── Evidence Ledger
   ↓
⑤ CONNECT
   ├── explicit links
   ├── relations
   └── graph
   ↓
⑥ INDEX
   └── current rebuild/cache behavior
   ↓
⑦ RETRIEVE
   ├── candidates
   ├── explainable ranking
   └── relevant evidence
   ↓
⑧ RETURN
   └── structured evidence + provenance
   ↓
CONSUMING AGENT
```

Incremental/idempotent behavior at step ⑥ is still #12. Plain-text coverage and structural segmentation are still #69/#70. They must not be described as implemented before their Test Cards close.

---

# Target pipeline — only if the Test Cards are KEEP

```text
QUERY
  ↓
Candidate Retrieval
  ↓
Seed Evidence
  ↓
Query-Aware Graph Expansion
  ↓
Relation Type / Origin / Confidence
  ↓
Temporal Validity + State Keys
  ↓
Authority / Scope / Instruction Resolution
  ↓
Conflict Detection
  ↓
Evidence Arbitration
  ↓
Evidence Status
  ├── sufficient
  ├── insufficient
  ├── conflicting
  └── ambiguous
  ↓
Renderer
  ├── RAW
  ├── EVIDENCE
  └── STRUCTURED
  ↓
CONSUMING AGENT
```

This is **target architecture**, not a description of `main` today.

---

# Current retrieval baseline

The deterministic CI sanity suite currently protects:

- Hit@1: **75%**
- Hit@3: **100%**
- Hit@5: **100%**
- MRR: **0.875**
- Evidence hit rate: **100%**

This is a **regression alarm**, not a competitive benchmark. A known paraphrase case can still place the gold memory at #2 rather than #1; that failure remains visible until semantic/adaptive retrieval proves a general improvement through #18/#17 rather than query-specific tuning.

---

# Documentation / research layer

Current-reference docs:

- `docs/OVERVIEW.md` — executive + colloquial + technical overview.
- `docs/FEATURES.md` — implemented capability catalog.
- `docs/CONCEPTS.md` — canonical vocabulary and semantic distinctions.
- `docs/ARCHITECTURE.md` — current architecture and explicit future boundaries.
- `docs/OUTPUT_CONTRACT.md` — structured retrieval semantics.
- `docs/QUERY_EXAMPLES.md` — usage examples and clearly marked future targets.
- `docs/research/REFERENCES.md` — primary research/product sources.
- `docs/research/PAPER_NOTES.md` — source claim → TESSERA learning → Test Card.
- `docs/research/COMPETITIVE_LANDSCAPE.md` — version-aware competitor comparison.
- `docs/research/DECISION_TRACE.md` — source → insight → issue → decision trace.

Program tracker: #38.

---

# GitHub Project fields recommended

The GitHub Projects v2 board should mirror Issues/Test Cards rather than become a second source of truth:

- `Phase`: Foundation / Intelligence / Adaptive / Evaluation / State / Learning
- `Status`: Backlog / Ready / In Progress / Measuring / Decision / Done / Dropped
- `Decision`: Pending / Keep / Iterate / Revert / Drop / Defer
- `Test Card`: Draft / Ready / Updated
- `Impact`: Low / Medium / High / Transformational
- `Evidence`: Missing / Partial / Sufficient
- `Benchmark Gate`: N/A / Pending / Pass / Fail
- `PR`: linked PR

Operational note: Issues + versioned roadmap files remain the source of truth. The board is a visualization of those records.
