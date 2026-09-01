# TESSERA — Experimental Roadmap

TESSERA is an **agent-agnostic, text-first memory and evidence layer**. It hides storage, indexing, relations, temporal metadata and retrieval mechanics while preserving enough **evidence, provenance and navigation** for the consuming agent to reason for itself.

> **TESSERA abstracts memory architecture away from the agent. It does not replace the cognition of the agent.**

## Executive takeaway

The Foundation is functional and most public truth/safety contracts are already validated. Productization has advanced through repository architecture and clean Python packaging, with `#117` now the next product/runtime card. In parallel, the 2026-09-01 QUMem audit exposed a second major lane: memory construction, query-conditioned retrieval planning and structured user-state reconstruction.

The roadmap therefore has three concurrent priorities:

```text
CONTRACT / SAFETY
#135 decomposition fallback + #16 containment + #67 regression-gate integration

PRODUCTIZATION
#117 configuration → #118 clean onboarding → #134 first PyPI release

MEMORY INTELLIGENCE
#145 QUMem epic
→ construction (#136/#137/#138)
→ query-conditioned planning (#139/#140)
→ structured state (#141)
→ fidelity/benchmark/public parity (#142/#143/#144)
```

Research signals remain hypotheses until their Test Cards earn `KEEP`:

```text
GraphMemix → query-aware graph expansion + evidence budget
CaSKG      → relation origin/confidence/validation
MemToC     → evidence arbitration + four-state evidence status
RENDER     → retrieval quality != renderer quality
QUMem      → dynamic episodes + typed F/P/I + multi-query planning + Fq/Tq/Iq state
```

---

# Product invariants

- Source text is the source of truth; index/cache/ledger are derived and rebuildable.
- TESSERA returns **structured evidence**, not the final answer for the consuming agent.
- Exactly **3 semantic drawers** remain: `facts`, `preferences`, `insights`.
- `document_type`, harness, scope, temporal state, authority, confidence, relations, quality and utility are facets/metadata — not new drawers.
- QUMem `F / P / I` semantics map onto the existing three TESSERA drawers; they do not create additional drawers.
- TESSERA is text-first and auditable; source code is not primary memory.
- No generative LLM is mandatory in the basic deterministic path.
- Retrieval relevance != confidence != authority != relation confidence != temporal validity != utility.
- User source files are never silently rewritten during indexing.
- A relation existing != the relation being trustworthy != the relation being useful for the current query.
- A conflict being detected != the conflict being resolved.
- Derived query-conditioned state is a view over evidence, never a replacement source of truth.
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

Plain-language stage records: [`docs/test-cards/`](test-cards/).

---

# Authoritative execution portfolio — audited 2026-09-01

This portfolio is reconciled against GitHub issue routing and canonical `main` at:

`b3be96f4aa842a81c135b6ac87d3311ed292d339`

That commit is the canonical lifecycle merge for #116 / PR #133. Historical prose and emoji markers are not status evidence.

## Status contract

| Status | Meaning |
|---|---|
| `IMPLEMENTED` | A merged runtime or contract exists on `main`. |
| `VALIDATED` | The implementation exists and its required tests or benchmark passed. |
| `READY` | Dependencies are closed and the Test Card satisfies Definition of Ready. |
| `IN_PROGRESS` | An active, unmerged pull request exists. |
| `BLOCKED` | An explicit dependency, missing Definition-of-Ready gate, or owner decision remains unresolved. |
| `DEFERRED` | Work is intentionally postponed even though dependencies are satisfied. |
| `TRACKER` | Epic or coordination issue without a direct implementation PR. |
| `DROPPED` | The card was explicitly rejected. |
| `SUPERSEDED` | A newer issue, contract, or audit replaced the record. |

## Reconciliation matrix

| Issue | GitHub state / routing | Canonical evidence or remaining gap | Benchmark applicability | Corrected status |
|---|---|---|---|---|
| [#68](https://github.com/LuigiFerronatto/TESSERA/issues/68) | closed | PR #98, canonical merge `fb23012ba4b2fddc3912d7cb593391a04fe45ae7`; lossless Engine/CLI/MCP direct-query parity | contract/smoke | `VALIDATED` |
| [#74](https://github.com/LuigiFerronatto/TESSERA/issues/74) | closed | [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107), merge `0c0b638`, canonical `0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2`; accepted ADR 0001 | `NOT_APPLICABLE` | `VALIDATED` |
| [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) | closed | [PR #108](https://github.com/LuigiFerronatto/TESSERA/pull/108), canonical merge `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05`, [PR Evolution Audit](PR_EVOLUTION_92.md); truthful write admission and path containment | `SMOKE_ONLY` | `VALIDATED` |
| [#93](https://github.com/LuigiFerronatto/TESSERA/issues/93) | closed | PR #129 canonical merge `c6124548f32b6dc5e1b7acf5127632bc6c75fccc`; lifecycle #132; `KEEP` | implementation `SMOKE_ONLY`; lifecycle `NOT_APPLICABLE` | `VALIDATED` |
| [#94](https://github.com/LuigiFerronatto/TESSERA/issues/94) | closed | PR #101, canonical merge `467ba649f53312cedcecf40caf548af5f766c67b`; Markdown-only persistence contract | `SMOKE_ONLY` | `VALIDATED` |
| [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) | closed | PR #126 canonical merge `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`; generic defaults + explicit deprecated compatibility | `SMOKE_ONLY` | `VALIDATED` |
| [#96](https://github.com/LuigiFerronatto/TESSERA/issues/96) | closed | PR #99, canonical merge `812c3aa37b59a3e99135a9d8b39245aeb71356d0`; reproducible LongMemEval V1 dev-50 baseline | benchmark | `VALIDATED` |
| [#100](https://github.com/LuigiFerronatto/TESSERA/issues/100) | closed | PR #102, canonical merge `39febe36f016997f0c54ede9824f15dec04cc1ee`; versioned ledger + applicability-aware CI | benchmark | `VALIDATED` |
| [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) | closed | PR #113 canonical merge `a80a5f19671a002e6ec2ed1846d041afb090e7a2`; public TESSERA identity | smoke | `VALIDATED` |
| [#114](https://github.com/LuigiFerronatto/TESSERA/issues/114) | closed | PR #123 canonical merge `a79b5aec661f0d401b00c2985eff3a5a24363943`; auditable evolution/lifecycle governance | contract | `VALIDATED` |
| [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) | closed | ADR 0002, PR #128, canonical merge `b475f1cd805f86cc8ad9526e563e3c6fb8409ff1`, lifecycle #130; `KEEP` | implementation `SMOKE_ONLY`; lifecycle `NOT_APPLICABLE` | `VALIDATED` |
| [#116](https://github.com/LuigiFerronatto/TESSERA/issues/116) | closed | PR #131 canonical packaging merge `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4`; lifecycle PR #133 canonical `b3be96f4aa842a81c135b6ac87d3311ed292d339`; ownership-correct wheel/sdist | implementation `SMOKE_ONLY`; lifecycle `NOT_APPLICABLE` | `VALIDATED` |
| [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117) | open; #94/#115/#116 satisfied | project config, global store registry and explicit `tessera init` discovery contract not yet implemented | `SMOKE_ONLY` | `READY` |
| [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) | open; depends on #117 | clean installed-artifact onboarding matrix absent | `SMOKE_ONLY` | `BLOCKED` |
| [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) | open; depends on #117 | full CLI UX/output audit absent | `SMOKE_ONLY` | `BLOCKED` |
| [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) | open; depends on #117 plus validated foundation cards | MCP lifecycle/protocol robustness absent | `SMOKE_ONLY` unless retrieval changes | `BLOCKED` |
| [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121) | open; depends on #117/#120 | official versioned TESSERA Skills absent | `SMOKE_ONLY` | `BLOCKED` |
| [#134](https://github.com/LuigiFerronatto/TESSERA/issues/134) | open; depends on #117, #118 and #87 | TestPyPI/PyPI publication, release workflow and external public-artifact smoke are intentionally gated | `SMOKE_ONLY` | `BLOCKED` |
| [#67](https://github.com/LuigiFerronatto/TESSERA/issues/67) | open; #92, #93 and #95 dependencies are satisfied; still blocked on regression-gate integration | final Quality Gate v2 integration absent | governance/regression | `BLOCKED` |
| [#16 containment](https://github.com/LuigiFerronatto/TESSERA/issues/16) | open; containment has no dependencies | current silent resolver must first be contained/disabled before full supersession research | regression fixture | `READY` |
| [#16 full](https://github.com/LuigiFerronatto/TESSERA/issues/16) | open; depends on #15, #73 and #96 | deterministic state-key/validity/supersession experiment remains future | `REQUIRED` when executed | `BLOCKED` |
| [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) | open; depends on #67/#94 | incremental/idempotent indexing absent | `REQUIRED` | `BLOCKED` |
| [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) | open; depends on #12/#94 | text ingestion beyond Markdown absent | `REQUIRED` | `BLOCKED` |
| [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) | open; depends on #12/#69 | structural segmentation absent | `REQUIRED` | `BLOCKED` |
| [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) | open; depends on #12/#69/#70 | corpus doctor absent | focused/benchmark as applicable | `BLOCKED` |
| [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) | open; depends on #12/#94 | versioned memory/source revision history absent | `REQUIRED` | `BLOCKED` |
| [#14](https://github.com/LuigiFerronatto/TESSERA/issues/14) | open epic | graph experiment coordination only; no direct implementation PR | child-owned | `TRACKER` |
| [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) | open; #96 satisfied and live routing reconciled | query-aware/budgeted 1-hop graph expansion not implemented | `REQUIRED` | `READY` |
| [#26](https://github.com/LuigiFerronatto/TESSERA/issues/26) | open; depends on frozen #25 baseline/#96 | edge origin/confidence/validation absent | `REQUIRED` | `BLOCKED` |
| [#15](https://github.com/LuigiFerronatto/TESSERA/issues/15) | open; depends on #73/#96 | temporal state semantics/state keys absent | `REQUIRED` | `BLOCKED` |
| [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) | open; depends on #69/#70 | harness adapter registry absent | focused | `BLOCKED` |
| [#32](https://github.com/LuigiFerronatto/TESSERA/issues/32) | open; depends on #71 | source authority/scope/precedence policy absent | `REQUIRED` | `BLOCKED` |
| [#72](https://github.com/LuigiFerronatto/TESSERA/issues/72) | open; depends on #71/#32 | deterministic instruction resolver absent | `REQUIRED` | `BLOCKED` |
| [#27](https://github.com/LuigiFerronatto/TESSERA/issues/27) | open; depends on #15/#16/#32/#72/#96 | cross-source Evidence Arbitration absent | `REQUIRED` | `BLOCKED` |
| [#20](https://github.com/LuigiFerronatto/TESSERA/issues/20) | open; depends on #15/#16/#27/#96 | four-state evidence sufficiency/abstention absent | `REQUIRED` | `BLOCKED` |
| [#19](https://github.com/LuigiFerronatto/TESSERA/issues/19) | open; #92 satisfied; still depends on #13/#16/#73 | evidence-aware memory admission absent; #92 only answers `safe to persist?` | `REQUIRED` | `BLOCKED` |
| [#17](https://github.com/LuigiFerronatto/TESSERA/issues/17) | open; depends on #20/#74/#96 | adaptive HOW-to-retrieve strategy remains future | `REQUIRED` | `BLOCKED` |
| [#21](https://github.com/LuigiFerronatto/TESSERA/issues/21) | open; depends on #19/#20/#96 | experience/utility feedback absent | `REQUIRED` | `BLOCKED` |
| [#18](https://github.com/LuigiFerronatto/TESSERA/issues/18) | open benchmark epic | tracks #96/#100/#28/#103–#106 | child-owned | `TRACKER` |
| [#28](https://github.com/LuigiFerronatto/TESSERA/issues/28) | open; #68/#96 satisfied and live routing reconciled | frozen-evidence rendering ablation not yet executed | `REQUIRED` | `READY` |
| [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103) | open; depends on #28/#74/#96/#100 | frozen-evidence reader baseline absent | `REQUIRED` | `BLOCKED` |
| [#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) | open; depends on #74/#100/#103 | calibrated/versioned judge absent | `REQUIRED` | `BLOCKED` |
| [#105](https://github.com/LuigiFerronatto/TESSERA/issues/105) | open; depends on #96/#100/#103/#104 | LongMemEval V1 full-500 not run | `REQUIRED` | `BLOCKED` |
| [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) | open; depends on #74/#100/#103/#104/#105 | LongMemEval V2 adapter/small-tier absent | `REQUIRED` | `BLOCKED` |
| [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135) | open; no dependencies | documented deterministic decomposer fallback exists in code but is not invoked on provider/parse failure | `SMOKE_ONLY` | `READY` |
| [#136](https://github.com/LuigiFerronatto/TESSERA/issues/136) | open; depends on #135/#74 | QUMem F/P/I fidelity and 1-pass vs 3-pass ablation not validated | `REQUIRED` | `BLOCKED` |
| [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) | open; depends on #135; coordinates #136/#15 | decomposed-memory source episode/supporting-turn/temporal-position lineage not preserved end-to-end | `REQUIRED` | `BLOCKED` |
| [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) | open; #74 satisfied; routing requires frozen baseline fixture before execution | role-aware adjacent-user continuity experiment not ready until fixture DoR is frozen | `REQUIRED` | `BLOCKED` |
| [#139](https://github.com/LuigiFerronatto/TESSERA/issues/139) | open; #74 satisfied | current assisted orchestrator emits one free-text information need; bounded multi-need contract absent | `REQUIRED` | `READY` |
| [#140](https://github.com/LuigiFerronatto/TESSERA/issues/140) | open; depends on #139/#74/#96 | bounded multi-query/multi-store WHAT-to-retrieve planner absent | `REQUIRED` | `BLOCKED` |
| [#141](https://github.com/LuigiFerronatto/TESSERA/issues/141) | open; depends on #140/#15/#16/#137/#74/#96 | principal QUMem gap: structured evidence-backed `Fq/Tq/Iq` state absent | `REQUIRED` | `BLOCKED` |
| [#142](https://github.com/LuigiFerronatto/TESSERA/issues/142) | open; full suite depends on #135–#141 | fixture design may start, but final QUMem fidelity regression suite is not executable end-to-end yet | `REQUIRED` | `BLOCKED` |
| [#143](https://github.com/LuigiFerronatto/TESSERA/issues/143) | open; depends on #136/#137/#138/#140/#141/#142/#96 | external personalized-memory/preference-evolution benchmark track absent | `REQUIRED` | `BLOCKED` |
| [#144](https://github.com/LuigiFerronatto/TESSERA/issues/144) | open; depends on validated #136/#137/#138/#140/#141/#142 plus #68/#74 | assisted construction/state parity across Python/CLI/MCP intentionally waits for semantic contracts to stabilize | `SMOKE_ONLY` unless semantics change | `BLOCKED` |
| [#145](https://github.com/LuigiFerronatto/TESSERA/issues/145) | open epic | coordinates QUMem-derived construction, planning, state, evaluation and docs; no direct implementation PR | child-owned | `TRACKER` |
| [#146](https://github.com/LuigiFerronatto/TESSERA/issues/146) | open; no dependency for truth correction | current QUMem-facing docs overstate some paper/runtime fidelity; docs correction can proceed independently | `NOT_APPLICABLE` | `READY` |
| [#38](https://github.com/LuigiFerronatto/TESSERA/issues/38) | open documentation epic | general documentation/governance tracker | child-owned | `TRACKER` |
| [#87](https://github.com/LuigiFerronatto/TESSERA/issues/87) | open; owner legal decision required | standalone LICENSE/contribution entrypoint is a direct blocker for #134 | `NOT_APPLICABLE` | `BLOCKED` |

## Completed and validated capabilities

- Foundation memory/retrieval/graph/evidence primitives are on `main`.
- Direct-query Engine/CLI/MCP parity is `VALIDATED` (#68).
- Markdown-only persistence is `VALIDATED` (#94).
- Truthful/path-contained write safety is `VALIDATED` (#92).
- Core-vs-optional-LLM architecture is `VALIDATED` (#74).
- LongMemEval V1 dev-50 and benchmark governance are `VALIDATED` (#96/#100).
- Runtime independence is `VALIDATED` (#95).
- Storage/corpus-boundary parity is `VALIDATED` (#93).
- Repository architecture and clean Python distribution are `VALIDATED` (#115/#116).

---

# Current execution map

The roadmap is no longer one serial chain. Three lanes can progress in parallel while respecting dependencies and WIP limits.

## Lane A — Contract and safety

```text
READY #135 decomposer fallback integrity
READY #16 containment
READY #146 QUMem truth correction (docs only)

#67 Quality Gate v2
  └─ BLOCKED only on regression-gate integration

#12 incremental indexing
  └─ remains downstream of #67
```

#135 is P0 because deeper decomposition experiments should not be evaluated while the documented offline fallback contract is broken. #16 containment remains P0 safety because historical preference evidence must not be silently hidden before trajectory/state work.

## Lane B — Productization and first public package

```text
#115 repository architecture                 VALIDATED
  ↓
#116 clean Python distribution                VALIDATED
  ↓
#117 project/global configuration + init      READY
  ↓
#118 clean installed-artifact onboarding      BLOCKED
  ↓
#134 first TestPyPI/PyPI release              BLOCKED
  ↑
#87 LICENSE / legal ownership                 BLOCKED — owner decision

Parallel after #117:
#119 CLI experience
#120 MCP robustness
  ↓
#121 official TESSERA Skills
```

#119–#121 improve the product but are not blanket blockers for the first PyPI release. #134 is explicitly gated by #117, #118 and #87.

## Lane C — QUMem-derived memory intelligence

Parent tracker: [#145](https://github.com/LuigiFerronatto/TESSERA/issues/145).

```text
NOW
#135 fallback integrity          READY
#16 resolver containment        READY
#146 docs truth reconciliation  READY

MEMORY CONSTRUCTION
#138 role-aware episode continuity   BLOCKED on fixture DoR
#136 F/P/I semantics + 1-pass/3-pass BLOCKED on #135
          └──────────────┬───────────┘
                         ↓
#137 episode/supporting-turn/position lineage

QUERY-CONDITIONED RETRIEVAL
#139 multiple information needs  READY
  ↓
#140 bounded multi-query + multi-store planner

TEMPORAL FOUNDATION IN PARALLEL
#73 revision history
  ↓
#15 temporal model/state keys
  ↓
#16 full supersession

PRINCIPAL QUMem GAP
#140 + #15 + #16 + #137
  ↓
#141 structured query-conditioned state: Fq / Tq / Iq

CONTROL FLOW + EVALUATION
#141 coordinates with #20 evidence status/abstention
#142 frozen QUMem fidelity suite
  ↓
#143 personalized-memory / preference-evolution benchmark

PUBLIC INTEGRATION AFTER SEMANTICS STABILIZE
#144 Python / CLI / MCP assisted-feature parity
```

### Ownership boundaries inside the QUMem lane

```text
#140 = WHAT evidence should be retrieved?
#17  = HOW should each retrieval execute efficiently?

#141 = what does retrieved evidence imply for this query? (Fq/Tq/Iq)
#20  = is the evidence sufficient/conflicting/ambiguous and what control-flow signal follows?

#137 temporal_position = position in source episode/interaction
#15  temporal validity = when a state/fact is applicable in the world
```

These dimensions must not be collapsed into one opaque planner or one truth score.

---

# Measurement lane

## Benchmark capabilities: keep baselines separate

| Benchmark | Purpose | Scope | Record / owner | Status |
|---|---|---|---|---|
| deterministic sanity fixture | fast regression alarm for core retrieval | synthetic corpus; Hit@1/3/5, MRR, evidence hit rate | [`benchmarks/sanity`](../benchmarks/sanity/) | `VALIDATED` through #10 |
| LongMemEval V1 dev-50 historical | frozen retrieval-only experiment | deterministic 50-question subset; not answer quality/full-500 | [baseline record](../benchmarks/results/longmemeval-v1-dev-50/baseline.md) | `VALIDATED` |
| LongMemEval V1 dev-50 forward | candidate-vs-parent merge gate | same frozen retrieval profile + environment fingerprint | [forward record](../benchmarks/results/longmemeval-v1-dev-50/forward.md) | `VALIDATED` |
| renderer ablation | isolate retrieval from presentation | same evidence/reader/budget; RAW vs EVIDENCE vs STRUCTURED | #28 rendering ablation | `READY` |
| LongMemEval V1 frozen reader | downstream QA from frozen evidence | reader-only track | #103 | `BLOCKED` |
| calibrated judge | semantic evaluation infrastructure | separate probabilistic evaluation layer | #104 | `BLOCKED` |
| LongMemEval V1 full-500 | preregistered retrieval/reader/judge execution | all 500 questions | #105 | `BLOCKED` |
| LongMemEval V2 | multimodal trajectory-memory protocol | V2 small tier first | #106 | `BLOCKED` |
| QUMem fidelity suite | behavior-level regression across #135–#141 | frozen reviewed fixtures | #142 | `BLOCKED` for full suite |
| personalized-memory/preference evolution | external evidence for typed construction + trajectories + Fq/Tq/Iq | dataset/license audit required | #143 | `BLOCKED` |

Historical roadmap wording `#25 graph-expansion card DoR completion` is superseded by the live routing correction: #25 is now `READY`; the experiment itself is still unimplemented.

---

# Research-derived experiment map

| Research signal | TESSERA Test Card | Question we measure |
|---|---|---|
| GraphMemix | #25 | Does query-aware/budgeted expansion outperform indiscriminate 1-hop in quality/cost? |
| CaSKG | #26 | Does relation confidence/validation reduce harmful expansion without destroying recall? |
| MemToC | #27 | Does Evidence Arbitration improve source selection and abstention versus a silent winner? |
| MemToC | #20 | Do `sufficient / insufficient / conflicting / ambiguous` improve downstream control flow? |
| MemToC + harness scope | #32/#72 | Do authority + scope + precedence resolve instructions better than newest/relevance wins? |
| RENDER | #28 | Does reader-facing rendering change downstream QA when the evidence set is frozen? |
| QUMem | #135 | Does provider/parse failure truthfully reach the deterministic decomposer fallback? |
| QUMem | #136 | Is corrected one-pass typed extraction competitive with three type-conditioned F/P/I passes? |
| QUMem | #137 | Does atomic-memory lineage preserve source episode/supporting turns/position end-to-end? |
| QUMem | #138 | Does adjacent-user role-aware continuity improve episode boundaries over current accumulated-TF-IDF/timeout? |
| QUMem | #139/#140 | Do multiple needs and bounded targeted sub-queries improve compound/temporal evidence coverage? |
| QUMem | #141 | Does structured evidence-backed Fq/Tq/Iq improve preference/current-state reasoning over raw Top-K/free-text consolidation? |
| QUMem | #142/#143 | Do fidelity fixtures and external personalized-memory benchmarks justify the added complexity? |
| QUMem | #144 | Can only validated assisted contracts remain lossless across Python/CLI/MCP? |
| QUMem research governance | #145/#146 | Can paper behavior, current main, TESSERA-specific choices and future experiments remain explicitly separated? |

---

# Foundation pipeline — what exists today

```text
TEXT / CANONICAL MEMORY SOURCES
   ↓
DISCOVER
   ↓
UNDERSTAND
   ├── document type
   ├── metadata
   ├── scope
   └── semantic drawer
   ↓
NORMALIZE
   ├── explicit metadata
   ├── inferred metadata
   └── stable identity
   ↓
TRACE
   ├── source
   ├── spans
   ├── hashes
   └── Evidence Ledger
   ↓
CONNECT
   ├── explicit links
   ├── relations
   └── graph
   ↓
INDEX
   └── current rebuild/cache behavior
   ↓
RETRIEVE
   ├── candidates
   ├── explainable ranking
   └── relevant evidence
   ↓
RETURN
   └── structured evidence + provenance
   ↓
CONSUMING AGENT
```

Incremental/idempotent indexing is still #12. Plain-text coverage and structural segmentation are still #69/#70. They must not be described as implemented before their Test Cards close.

---

# Optional assisted memory path — target only if Test Cards are KEEP

The deterministic pipeline above remains independently usable. QUMem-derived work adds an optional assisted path around it:

```text
SOURCE INTERACTION
  ↓
Role-aware Episode Construction (#138)
  ↓
Typed Atomic F/P/I Decomposition (#136)
  ↓
Episode + Supporting-Turn Lineage (#137)
  ↓
CANONICAL TESSERA MEMORY / EVIDENCE

QUERY / TASK
  ↓
Information Needs (#139)
  ↓
Bounded Query + Store Plan (#140)
  ↓
DETERMINISTIC TESSERA RETRIEVAL
  ↓
Structured Query-Conditioned State (#141)
  ├── Fq facts
  ├── Tq preference trajectory
  └── Iq transferable insights
  ↓
Evidence Status / Abstention (#20)
  ↓
CONSUMING AGENT
```

This is **target architecture**, not a description of `main` today. Beginning/Middle/End remains a TESSERA-specific episode representation and must not be described as QUMem's boundary algorithm. #146 owns documentation truth while capabilities evolve.

---

# Existing advanced target pipeline — graph / temporal / trust

```text
QUERY
  ↓
Candidate Retrieval
  ↓
Seed Evidence
  ↓
Query-Aware Graph Expansion (#25)
  ↓
Relation Type / Origin / Confidence (#26)
  ↓
Temporal Validity + State Keys (#15)
  ↓
Authority / Scope / Instruction Resolution (#32/#72)
  ↓
Conflict Detection / Supersession (#16)
  ↓
Evidence Arbitration (#27)
  ↓
Evidence Status (#20)
  ├── sufficient
  ├── insufficient
  ├── conflicting
  └── ambiguous
  ↓
Renderer (#28)
  ├── RAW
  ├── EVIDENCE
  └── STRUCTURED
  ↓
CONSUMING AGENT
```

The graph/trust target and the QUMem target are composable experiments, not one pre-approved architecture.

---

# Current retrieval baseline

The deterministic CI sanity suite currently protects:

- Hit@1: **75%**
- Hit@3: **100%**
- Hit@5: **100%**
- MRR: **0.875**
- Evidence hit rate: **100%**

This is a regression alarm, not a competitive benchmark. LongMemEval and future QUMem/personalized-memory tracks provide broader evidence and must remain separately reported.

---

# Documentation / research truth

Current-reference docs must distinguish:

```text
external paper behavior
!= TESSERA interpretation
!= current implementation
!= planned Test Card
!= validated TESSERA result
```

#146 is the immediate QUMem truth-reconciliation card. It coordinates with #78 rather than duplicating legacy/project-specific documentation cleanup.

Current-reference docs:

- `docs/OVERVIEW.md`
- `docs/FEATURES.md`
- `docs/CONCEPTS.md`
- `docs/ARCHITECTURE.md`
- `docs/OUTPUT_CONTRACT.md`
- `docs/QUERY_EXAMPLES.md`
- `docs/research/REFERENCES.md`
- `docs/research/PAPER_NOTES.md`
- `docs/research/COMPETITIVE_LANDSCAPE.md`
- `docs/research/DECISION_TRACE.md`

General documentation tracker: #38. QUMem program tracker: #145.

---

# Execution policy

- #14, #18, #38 and #145 are `TRACKER`s and do not produce direct implementation PRs.
- Readiness does not authorize unlimited parallel execution; keep the existing WIP discipline.
- P0 integrity/safety work (#135 and #16 containment) remains ahead of downstream state claims.
- #146 may proceed in parallel because it corrects documentation truth and has `NOT_APPLICABLE` benchmark routing.
- #25 and #28 are `READY`; execution order should follow current WIP and product/research priorities rather than stale roadmap blockers.
- #138 should not be treated as fully executable until its frozen baseline fixture/Definition of Ready is explicit.
- #142 fixture design can start before all children close, but final acceptance remains blocked on #135–#141.
- #140 owns WHAT evidence to retrieve; #17 owns HOW to retrieve it.
- #141 owns query-conditioned state reconstruction; #20 owns evidence sufficiency/conflict/ambiguity control-flow status.
- Feature cards depend on benchmark infrastructure; benchmark reruns are evidence, never reverse dependencies.
- Candidate commits and their canonical squash merges count as one capability delivery unless evidence proves otherwise.

---

# GitHub Project fields recommended

The GitHub Projects board should mirror Issues/Test Cards rather than become a second source of truth:

- `Phase`: Foundation / Productization / Memory Construction / Retrieval Planning / Temporal & Trust / Evaluation / Learning
- `Status`: Backlog / Ready / In Progress / Measuring / Decision / Done / Dropped
- `Decision`: Pending / Keep / Iterate / Revert / Drop / Defer
- `Test Card`: Draft / Ready / Updated
- `Impact`: Low / Medium / High / Transformational
- `Evidence`: Missing / Partial / Sufficient
- `Benchmark Gate`: N/A / Pending / Pass / Fail
- `PR`: linked PR

Operational note: Issues + versioned roadmap files remain the source of truth. The board is a visualization of those records.
