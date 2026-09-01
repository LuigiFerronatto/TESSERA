# TESSERA Roadmap

> Authoritative portfolio audit: 2026-09-01 on canonical `main` `a13abbbba2138e48e237f14a182dd6746e3ec7d4` (PR #149, QUMem/product-release roadmap reconciliation). This document describes **validated current capability**, **live dependency routing**, and **planned experiments**. An Issue/Test Card existing is not evidence that a capability is implemented.

TESSERA is an agent-agnostic, text-first memory and evidence layer. Markdown source records remain authoritative; indexes, caches and benchmark artifacts are derived and rebuildable. The deterministic core must remain useful without a mandatory generative model.

Plain-language stage records live under `docs/test-cards/`; their index is `docs/test-cards/README.md`. Governance Issue #109 established that reusable stage-record layer; those records explain before/after behavior and evidence but never override current code, canonical merge evidence, or the authoritative routing below.

## Status contract

- `IMPLEMENTED` — canonical runtime/contract delivery is merged on `main`.
- `VALIDATED` — canonical delivery is merged and its required validation/lifecycle evidence is complete.
- `READY` — dependencies and Definition of Ready are satisfied; work may start when selected under WIP limits.
- `IN_PROGRESS` — an active unmerged implementation/documentation PR owns the current work.
- `BLOCKED` — a dependency, decision, fixture or gate is unresolved.
- `DEFERRED` — intentionally postponed.
- `TRACKER` — coordination epic only; child Test Cards own implementation and decisions.
- `DROPPED` — experiment rejected.
- `SUPERSEDED` — replaced by a later canonical delivery/record.

Candidate commits and their canonical merge commits represent one delivery when they contain the same capability. Lifecycle-only corrections are `DOCUMENTATION_CORRECTION`, not a second runtime capability.

## Non-negotiable product invariants

```text
Markdown/source truth
!= derived index/cache/ledger state

relevance
!= confidence
!= authority
!= relation confidence
!= temporal validity
!= utility

relation exists
!= relation is trustworthy
!= relation is useful for this query

conflict detected
!= conflict resolved

query-conditioned state
!= persistent source truth
```

Exactly three semantic drawers remain:

```text
facts
preferences
insights
```

QUMem-inspired work must not add a fourth semantic drawer. TESSERA-specific `procedural_anchor` semantics continue to map to the `insights` drawer where current code/contracts require it.

---

# Macro roadmap

## FASE 0 — FAZER FUNCIONAR

Status: `VALIDATED FOUNDATION`.

The engine already provides:

```text
source / memory
    -> canonical metadata + stable identity
    -> provenance / Evidence Ledger
    -> explicit relations + graph
    -> derived index
    -> deterministic retrieval
    -> structured evidence
```

Implemented foundation includes memory persistence, retrieval, basic graph relations, stable identity and source-backed evidence. Advanced graph/state/admission capabilities remain later experiments; their existence must not be inferred from the foundation modules.

## FASE 1 — FAZER SER VERDADE

Status: `MOSTLY VALIDATED`; the remaining high-risk work is containment/governance rather than rebuilding the foundation.

Already validated:

```text
#68  retrieval contract parity
#92  truthful write safety/path containment
#93  cross-surface storage parity
#94  Markdown persistence integrity
#95  runtime independence
#96  LongMemEval V1 reproducible retrieval baseline
#100 benchmark governance
#74  deterministic-core / optional-LLM architecture
#112 public identity
#114 lifecycle/evolution governance
```

Supporting governance already on `main` includes #109 plain-language stage records. It is a documentation/lifecycle capability, not a memory-runtime feature.

Still open:

```text
#16 P0 containment
    stop silent destructive newest-only conflict filtering

#67 Quality Gate v2
    still blocked on regression-gate integration
```

#16 became more urgent after the QUMem audit because preference trajectories require earlier and later evidence to remain available. The P0 containment is independent from the later full supersession experiment.

## FASE 2 — FAZER VIRAR PRODUTO

Status: repository architecture, packaging and configuration/discovery are validated; clean onboarding is the next release-critical productization step.

```text
#115 repository architecture        VALIDATED
  -> #116 package/distribution       VALIDATED
       -> #117 init/config/discovery VALIDATED
            -> #118 clean onboarding READY
                 -> #134 first PyPI release BLOCKED

#87 legal/repository entrypoint -----------------> #134

Parallel product work now unblocked:
  #119 CLI UX       READY
  #120 MCP runtime  READY
       -> #121 official Skills BLOCKED on #120

Configuration v2 refinement now active:
  #153 store / sources / index separation IN_PROGRESS
       -> #154 safe source discovery       BLOCKED pending #153 canonical reconciliation
       -> #155 source-picker init UX       BLOCKED pending #153 canonical reconciliation
```

#153 is an unmerged candidate and must not be described as implemented or
validated. This branch does not begin #154, #155, #157, or alter their
deliveries; downstream readiness may change only after #153 is canonically
merged and its post-merge lifecycle is synchronized.

The first PyPI release does **not** require #119/#120/#121 unless those cards discover a release-contract blocker before publication. #134 owns TestPyPI/PyPI publication, release workflow, distribution-name freeze and post-publication smoke. `tessera-agent-memory` is only a current candidate distribution name until #134 freezes it.

## FASE 3 — FAZER A MEMÓRIA MELHOR

Status: foundation primitives exist; advanced memory construction, graph, temporal/state, arbitration, admission and utility learning are experimental.

This phase now has two coordinated research families:

```text
Graph / evidence intelligence
#25 -> #26 -> #27 / #20

QUMem-derived construction/state
#145 tracker
  -> #135/#136/#137/#138
  -> #139/#140
  -> #15/#16
  -> #141
  -> #20/#142/#143
```

Neither family replaces the deterministic core. Experimental assisted cognition remains optional under ADR #74.

## FASE 4 — PROVAR QUE É MELHOR

Status: measurement infrastructure exists; broader answer-quality and personalized-memory evidence remain future work.

Already available:

```text
deterministic sanity fixture
LongMemEval V1 dev-50 historical baseline (#96)
Benchmark Ledger / applicability (#100)
conditional benchmark CI
```

Open evaluation tracks include:

```text
#28  rendering ablation
#103 frozen-evidence reader baseline
#104 calibrated LLM-as-a-judge
#105 LongMemEval V1 full-500
#106 LongMemEval-V2
#142 QUMem fidelity regression suite
#143 personalized-memory / preference-evolution benchmark
```

#143 complements LongMemEval; it does not replace it or make QUMem fidelity synonymous with benchmark quality.

---

## Reconciliation matrix

The first matching row for an Issue is the authoritative roadmap state used by static governance tests.

| Issue | GitHub state | Lifecycle status | Dependency / routing decision |
|---|---|---|---|
| [#68](https://github.com/LuigiFerronatto/TESSERA/issues/68) | closed | `VALIDATED` | Engine / CLI / MCP retrieval semantics aligned in PR #98. |
| [#74](https://github.com/LuigiFerronatto/TESSERA/issues/74) | closed | `VALIDATED` | ADR 0001 accepted in [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107), [merge `0c0b638`](https://github.com/LuigiFerronatto/TESSERA/commit/0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2). Core deterministic; assisted cognition optional. |
| [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) | closed | `VALIDATED` | Write safety implementation [PR #108](https://github.com/LuigiFerronatto/TESSERA/pull/108), canonical `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05`; lifecycle evidence in `docs/PR_EVOLUTION_92.md`. |
| [#93](https://github.com/LuigiFerronatto/TESSERA/issues/93) | closed | `VALIDATED` | `KEEP`; canonical implementation `c6124548f32b6dc5e1b7acf5127632bc6c75fccc`; lifecycle #132 complete; see `docs/PR_EVOLUTION_93.md`. |
| [#94](https://github.com/LuigiFerronatto/TESSERA/issues/94) | closed | `VALIDATED` | Canonical Markdown persistence integrity. |
| [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) | closed | `VALIDATED` | `KEEP`; canonical runtime `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`; lifecycle complete. |
| [#96](https://github.com/LuigiFerronatto/TESSERA/issues/96) | closed | `VALIDATED` | Reproducible LongMemEval V1 dev-50 retrieval baseline. |
| [#100](https://github.com/LuigiFerronatto/TESSERA/issues/100) | closed | `VALIDATED` | Benchmark applicability/ledger: `REQUIRED / SMOKE_ONLY / NOT_APPLICABLE`. |
| [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) | closed | `VALIDATED` | Public TESSERA identity/banner. |
| [#114](https://github.com/LuigiFerronatto/TESSERA/issues/114) | closed | `VALIDATED` | Evolution-auditable lifecycle governance. |
| [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) | closed | `VALIDATED` | ADR 0002 accepted in PR #128, canonical `b475f1cd805f86cc8ad9526e563e3c6fb8409ff1`; lifecycle #130; `KEEP`. |
| [#116](https://github.com/LuigiFerronatto/TESSERA/issues/116) | closed | `VALIDATED` | Packaging PR #131 canonical `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4`; lifecycle #133 canonical `b3be96f4aa842a81c135b6ac87d3311ed292d339`; `KEEP`. |
| [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117) | closed | `VALIDATED` | `KEEP`; implementation PR #150 canonical `61cf76fbd6ed61972f0f5abae515ba9bffca4b55`; lifecycle PR #152 canonical `fc0ed763ad47f5eba88775f3517cbee99d00a8b9`; candidate and merge count once as `CONFIGURATION_DISCOVERY`. |
| [#153](https://github.com/LuigiFerronatto/TESSERA/issues/153) | open | `IN_PROGRESS` | Dedicated `test-card/153-config-v2` candidate separates write store, explicit read sources, and derived index. #154/#155 remain blocked until canonical merge and lifecycle reconciliation; no downstream work started. |
| [#67](https://github.com/LuigiFerronatto/TESSERA/issues/67) | open | `BLOCKED` | #92, #93 and #95 dependencies are satisfied; still blocked on regression-gate integration. |
| [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16) | open | `READY` containment / `BLOCKED` full | P0 containment has no dependency; full supersession waits on #15/#73/#96. Preserve preference history for #141. |
| [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) | open | `READY` | #116/#117 validated. Clean-room onboarding may start; it is the remaining technical release gate for #134. |
| [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) | open | `READY` | #112/#116/#117 validated. CLI UX may start independently; not a mandatory blocker for first PyPI release. |
| [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) | open | `READY` | #68/#74/#92/#116/#117 validated. MCP lifecycle/robustness may start and should reuse #117 configuration primitives. |
| [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121) | open | `BLOCKED` | #117 is satisfied; remaining blocker is #120. Official Skills only after MCP/public-contract readiness. |
| [#87](https://github.com/LuigiFerronatto/TESSERA/issues/87) | open | `BLOCKED` | Owner legal decision required for standalone LICENSE/CONTRIBUTING; direct blocker for #134. |
| [#134](https://github.com/LuigiFerronatto/TESSERA/issues/134) | open | `BLOCKED` | #117 is satisfied; remaining blockers are #118 validation + #87. #119–#121 are follow-ups unless they surface a release blocker. |
| [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) | open | `BLOCKED` | Depends on #67/#94; incremental/idempotent indexing. |
| [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) | open | `BLOCKED` | Depends on #12/#94; text ingestion beyond Markdown. |
| [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) | open | `BLOCKED` | Depends on #12/#69; structural document segmentation, not conversational episodes. |
| [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) | open | `BLOCKED` | Depends on #12/#69/#70; corpus doctor, distinct from product/config doctor. |
| [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) | open | `BLOCKED` | Depends on #12/#94; revision history foundation for temporal/supersession. |
| [#14](https://github.com/LuigiFerronatto/TESSERA/issues/14) | open | `TRACKER` | Graph experiment epic coordinating #25/#26. |
| [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) | open | `READY` | #96 baseline complete. The previous "#25 graph-expansion card DoR completion" gate is superseded by live routing; this card may start when selected under WIP limits. |
| [#26](https://github.com/LuigiFerronatto/TESSERA/issues/26) | open | `BLOCKED` | Requires a frozen #25 baseline; tests relation origin/confidence separately from query relevance. |
| [#15](https://github.com/LuigiFerronatto/TESSERA/issues/15) | open | `BLOCKED` | Depends on #73/#96; temporal/state semantics. `temporal_position` from #137 is not validity time. |
| [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) | open | `BLOCKED` | Depends on #69/#70; harness adapter registry. |
| [#32](https://github.com/LuigiFerronatto/TESSERA/issues/32) | open | `BLOCKED` | Depends on #71; authority/scope/precedence policy. |
| [#72](https://github.com/LuigiFerronatto/TESSERA/issues/72) | open | `BLOCKED` | Depends on #71/#32; deterministic instruction resolver. |
| [#27](https://github.com/LuigiFerronatto/TESSERA/issues/27) | open | `BLOCKED` | Depends on #15/#16/#32/#72/#96; cross-source Evidence Arbitration. |
| [#20](https://github.com/LuigiFerronatto/TESSERA/issues/20) | open | `BLOCKED` | Owns only `sufficient / insufficient / conflicting / ambiguous` evidence status and abstention. Query-conditioned state moved to #141. |
| [#19](https://github.com/LuigiFerronatto/TESSERA/issues/19) | open | `DEFERRED` | Evidence-aware admission; `worth remembering?` remains distinct from #92 `safe to persist?`. |
| [#17](https://github.com/LuigiFerronatto/TESSERA/issues/17) | open | `DEFERRED` | Depends on #140/#20/#74/#96. Owns HOW a frozen retrieval operation executes, not WHAT to retrieve. |
| [#21](https://github.com/LuigiFerronatto/TESSERA/issues/21) | open | `DEFERRED` | Utility/experience learning after admission/state become trustworthy. |
| [#18](https://github.com/LuigiFerronatto/TESSERA/issues/18) | open | `TRACKER` | Measurement spine: #96/#100 complete; #28/#103–#106 open. |
| [#28](https://github.com/LuigiFerronatto/TESSERA/issues/28) | open | `READY` | #68/#96 complete; freeze evidence and vary renderer only. #28 rendering ablation is independent from retrieval changes. |
| [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103) | open | `BLOCKED` | Depends on #28/#74/#96/#100; frozen-evidence reader baseline. |
| [#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) | open | `BLOCKED` | Depends on #74/#100/#103; calibrated judge contract. |
| [#105](https://github.com/LuigiFerronatto/TESSERA/issues/105) | open | `BLOCKED` | Depends on #96/#100/#103/#104; full-500 preregistered V1 evaluation. |
| [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) | open | `BLOCKED` | Depends on #74/#100/#103/#104/#105; LongMemEval-V2 adapter/small tier. |
| [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135) | open | `READY` | P0 decomposition fallback integrity; no dependencies; `SMOKE_ONLY`. Fix contract mismatch before deeper decomposition experiments. |
| [#136](https://github.com/LuigiFerronatto/TESSERA/issues/136) | open | `BLOCKED` | Depends on #135/#74; F/P/I semantic fidelity plus one-pass vs three-pass ablation; `REQUIRED`. |
| [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) | open | `BLOCKED` | Hard dependency #135; coordinate sequencing with #136/#138/#15; source episode/supporting turns/temporal position; `REQUIRED`. |
| [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) | open | `BLOCKED` | #74 satisfied, but DoR still requires a frozen reviewed episode-boundary fixture. Role-aware adjacent-user continuity experiment; `REQUIRED`. |
| [#139](https://github.com/LuigiFerronatto/TESSERA/issues/139) | open | `READY` | #74 satisfied; bounded structured information needs before retrieval; `REQUIRED`. |
| [#140](https://github.com/LuigiFerronatto/TESSERA/issues/140) | open | `BLOCKED` | Depends on #139/#74/#96; owns WHAT sub-queries/stores retrieve evidence; `REQUIRED`. |
| [#141](https://github.com/LuigiFerronatto/TESSERA/issues/141) | open | `BLOCKED` | Principal QUMem gap. Depends on #140/#15/#16/#137/#74/#96; structured evidence-linked `Fq/Tq/Iq`; `REQUIRED`. |
| [#142](https://github.com/LuigiFerronatto/TESSERA/issues/142) | open | `BLOCKED` | Full suite depends on #135–#141; fixture design may start early, but acceptance waits for child decisions; `REQUIRED`. |
| [#143](https://github.com/LuigiFerronatto/TESSERA/issues/143) | open | `BLOCKED` | Personalized-memory/preference-evolution benchmark; depends on #136/#137/#138/#140/#141/#142/#96; `REQUIRED`. |
| [#144](https://github.com/LuigiFerronatto/TESSERA/issues/144) | open | `BLOCKED` | P2 public assisted-surface parity only after upstream semantic cards are validated; coordinate with #120. |
| [#145](https://github.com/LuigiFerronatto/TESSERA/issues/145) | open | `TRACKER` | QUMem portfolio epic; no direct implementation PR. Coordinates #135–#146 plus #15/#16/#17/#20/#27. |
| [#146](https://github.com/LuigiFerronatto/TESSERA/issues/146) | open | `READY` | QUMem paper-vs-runtime truth correction; `NOT_APPLICABLE`; broader docs audit remains separate from this roadmap-only sync. |
| [#147](https://github.com/LuigiFerronatto/TESSERA/issues/147) | closed | `VALIDATED` | `KEEP`; roadmap/governance PR #149 canonical `a13abbbba2138e48e237f14a182dd6746e3ec7d4`; final candidate `e8b52dbf882a15b1f15b935f30e41b1e0190d446`; documentation-only `NOT_APPLICABLE` delivery with final CI/Benchmark Ledger green. |

---

# Execution lanes

The roadmap is not one serial queue. Independent lanes may advance in parallel, subject to the repository WIP limit and shared-file conflict avoidance.

## Lane A — Contract & Safety

```text
#16 containment READY

#67 regression-gate integration BLOCKED
  -> #12 incremental indexing
```

Containment should preserve candidates rather than silently treating newest as truth. Full deterministic supersession remains later and requires temporal/revision foundations.

## Lane B — Productization and first public release

```text
#117 init/config/discovery VALIDATED
  -> #118 clean onboarding READY
       -> #134 first PyPI release BLOCKED

#87 LICENSE / contribution ownership
       -> #134

#119 CLI UX READY
#120 MCP robustness READY
  -> #121 official Skills BLOCKED
```

#134 is the release gate, not a packaging refactor. #116 already proved wheel/sdist ownership and clean installed-artifact behavior. #118 must prove the final onboarding flow against the #117 contract before publication. The remaining #134 blockers are #118 validation and #87.

## Lane C — QUMem-derived memory construction and state

Parent tracker: #145.

### Immediate integrity / truth work

```text
#135 decomposer fallback              READY
#16 P0 conflict containment           READY
#146 paper/runtime docs truth         READY
```

These are independent Test Cards. Selection still obeys WIP limits.

### Memory construction

```text
#138 role-aware episode continuity
     BLOCKED until frozen reviewed boundary fixture

#135
  -> #136 F/P/I semantics + 1-pass vs 3-pass

#135
  -> #137 source episode / supporting turns / temporal position
       recommended to consume decisions from #136/#138 when available
```

Important distinction:

```text
semantic episode membership (#138)
!= Beginning/Middle/End TESSERA representation

interaction temporal_position (#137)
!= temporal validity/state semantics (#15)
```

### Query-conditioned retrieval

```text
#139 information needs READY
  -> #140 bounded multi-query + multi-store plan
```

Ownership boundary:

```text
#139 = what historical facets must be established?
#140 = WHAT sub-queries/stores should retrieve them?
#17  = HOW each frozen retrieval operation should execute efficiently?
```

#17 stays later; it must not absorb query planning.

### Temporal/state foundation

```text
#73 revision history
  -> #15 temporal/state keys
       -> #16 full deterministic supersession
```

Historical preferences remain evidence even when superseded for current applicability.

### Principal QUMem gap

```text
#140 retrieval plan
#137 lineage
#15 temporal/state semantics
#16 conflict containment/full semantics
#74 optional-LLM boundary
#96 benchmark baseline
        -> #141 structured query-conditioned state Fq / Tq / Iq
```

#141 is an optional assisted state view over structured evidence. It is not a new source-of-truth store and must never overwrite persistent memories.

### Control flow and evaluation

```text
#27 cross-source arbitration
#15/#16 temporal conflict semantics
        -> #20 evidence status / abstention

#135–#141
        -> #142 frozen QUMem fidelity suite
        -> #143 personalized-memory benchmark

validated semantic contracts
        -> #144 Python / CLI / MCP assisted-surface parity
```

Ownership boundary:

```text
#141 = what state does evidence imply for this query?
#20  = is the evidence/state sufficient, insufficient, conflicting or ambiguous?
```

## Lane D — Graph and retrieval experiments

```text
#25 query-aware expansion READY
  -> frozen baseline
      -> #26 relation confidence
          -> later graph/arbitration integration
```

No relation-confidence value enters the default final relevance score merely because an edge exists.

## Lane E — Measurement spine

```text
#28 rendering READY
  -> #103 reader baseline
      -> #104 judge calibration
          -> #105 LongMemEval V1 full-500
              -> #106 LongMemEval-V2
```

The QUMem #142/#143 track runs alongside this spine and must keep construction/retrieval/state/reader effects separable.

---

# Target architecture — layered, not monolithic

## Deterministic core path

```text
QUERY
  |
  v
Configuration / Store Selection (#117)
  |
  v
Deterministic Candidate Retrieval
  |
  +--> lexical / basic relation signals today
  +--> query-aware graph expansion later (#25/#26)
  +--> temporal/state-aware retrieval later (#15/#16)
  +--> adaptive HOW-to-retrieve later (#17)
  |
  v
Structured Evidence
  |
  +--> provenance / source version
  +--> relations
  +--> temporal facets when validated
  +--> conflict/arbitration metadata when validated
  |
  v
CONSUMING AGENT
```

## Optional assisted memory-construction path

```text
CONVERSATION TURNS
  |
  v
Episode Membership (#138)
  |
  v
Typed F/P/I Decomposition (#136)
  |
  v
Source Episode + Supporting-Turn Lineage (#137)
  |
  v
Canonical Write Gate (#92)
  |
  v
MARKDOWN SOURCE MEMORIES
```

#135 first restores deterministic fallback integrity for the existing decomposer. It does not by itself validate QUMem fidelity.

## Optional assisted query-conditioned path

```text
QUERY / TASK
  |
  v
Information Needs (#139)
  |
  v
Retrieval Plan: WHAT to retrieve (#140)
  |
  v
Deterministic TESSERA Retrieval
  |
  v
Structured Fq / Tq / Iq State (#141)
  |
  v
Evidence Status / Abstention (#20)
  |
  v
CONSUMING AGENT
```

The consuming agent remains responsible for final reasoning/action. TESSERA returns evidence and optional structured derived state; it does not silently promote model output to persistent truth.

---

# Research-derived experiment map

External work changes the next experiment; it does not become implemented product capability merely because it is cited.

| Research signal | TESSERA experiment | Decision question |
|---|---|---|
| GraphMemix | #25 query-aware graph expansion | Which edges/evidence are useful for this query under a budget? |
| CaSKG | #26 relation confidence | Is an edge trustworthy independently of query relevance? |
| MemToC | #27 + #20 | How do we preserve disagreement and signal sufficiency/conflict/ambiguity? |
| RENDER | #28 rendering ablation | Does structured evidence presentation help when retrieval is frozen? |
| QUMem | #145 tracker; #135–#144 children | Which episode/decomposition/planning/state mechanisms improve TESSERA while preserving provenance and core independence? |
| Personalized-memory benchmarks | #143 | Do QUMem-inspired additions improve preference evolution/current-state tasks, not only factual recall? |

#146 owns broader paper-fidelity documentation truth. This roadmap only owns portfolio/routing truth. #147 canonically synchronized that routing in PR #149.

---

# Measurement policy

Benchmark applicability follows #100:

```text
REQUIRED
  semantic retrieval / memory-state experiment requires its declared benchmark evidence

SMOKE_ONLY
  config/runtime/release/integrity work that should preserve retrieval semantics

NOT_APPLICABLE
  documentation/governance-only work
```

LongMemEval is not run automatically for `SMOKE_ONLY` or `NOT_APPLICABLE` work. The deterministic sanity fixture remains the low-cost regression guard where required.

Historical deterministic sanity reference used by recent non-semantic changes:

```text
Hit@1             = 0.75
Hit@3             = 1.00
Hit@5             = 1.00
MRR               = 0.875
Evidence hit rate = 1.00
Missing evidence  = passed
```

This reference is not a substitute for feature-specific `REQUIRED` evaluation.

---

# Documentation and publication truth

Current-reference docs must distinguish:

```text
paper behavior
!= TESSERA interpretation
!= current implementation
!= validated benchmark result
```

#146 owns the QUMem-wide paper-fidelity audit. #78 owns project-specific legacy/deep-dive cleanup. #147 canonically synchronized roadmap routing in PR #149.

For publication:

```text
#117 VALIDATED
+
#118 VALIDATED
+
#87 owner-approved legal entrypoint
        -> #134 TestPyPI/PyPI release gate
```

No roadmap entry may imply that `tessera` is already the published PyPI distribution name. Distribution naming/version policy is frozen only inside #134.

---

# Immediate selection guidance

The repository uses bounded WIP rather than starting every `READY` card at once.

Current candidates with no unresolved hard dependency include:

```text
Productization:
#118 clean onboarding
#120 MCP robustness
#119 CLI UX

P0 safety/integrity:
#135 decomposer fallback
#16 containment

Documentation truth:
#146 QUMem fidelity correction

Independent research:
#139 structured information needs
#25 query-aware graph expansion
#28 rendering ablation
```

Prioritize by risk and the active product goal. A reasonable split is one productization card plus one safety/research card in separate worktrees, but the WIP policy remains authoritative over this example.

Do not start downstream cards simply because they are visible in this roadmap.

---

# Current concise map

```text
FOUNDATION / TRUTH
#68/#74/#92/#93/#94/#95/#96/#100/#112/#114  VALIDATED
#16 containment                                  READY
#67 quality gate                                 BLOCKED

PRODUCTIZATION / RELEASE
#115 VALIDATED
  -> #116 VALIDATED
       -> #117 VALIDATED
            -> #118 READY
                 -> #134 BLOCKED
#87 ----------------------------------------------^
#119 READY
#120 READY -> #121 BLOCKED

QUMEM EPIC #145                                   TRACKER
P0: #135 READY + #16 containment READY
Docs truth: #146 READY
Construction: #138 DoR-blocked; #136 blocked; #137 blocked
Planning: #139 READY -> #140 BLOCKED
Temporal: #73 -> #15 -> #16 full
Principal gap: #141 BLOCKED
Evaluation: #142/#143 BLOCKED
Public assisted parity: #144 BLOCKED

GRAPH / EVALUATION
#25 READY -> #26 BLOCKED
#28 READY -> #103 -> #104 -> #105 -> #106
```

This map is routing, not permission to bypass each Issue/Test Card's Definition of Ready, benchmark applicability, evidence requirement or lifecycle contract.
