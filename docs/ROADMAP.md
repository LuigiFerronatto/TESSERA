# TESSERA Roadmap

> Authoritative portfolio audit: 2026-09-04 against canonical `main` `99f05fb54836679dac34f050e55f0529cfd3a7e9` (PR #200, project-board sync). Issue #172 owns the portfolio taxonomy; this lifecycle correction reconciles #154/#155/#181 against the current canonical main. This document separates **validated capability**, **dependency readiness**, and **selected WIP**. An open Issue/Test Card is not evidence that a capability is implemented, validated, or currently selected.

TESSERA is an agent-agnostic, text-first memory and evidence layer. Markdown/source records remain authoritative; indexes, caches, semantic vectors, context packets and benchmark artifacts are derived and rebuildable. The deterministic core must remain useful without a mandatory generative model.

Plain-language stage records live under `docs/test-cards/`; their index is `docs/test-cards/README.md`. Governance Issue #109 established that reusable stage-record layer; those records explain before/after behavior and evidence but never override current code, canonical merge evidence, or the authoritative routing below.

## Status contract

- `IMPLEMENTED` — canonical runtime/contract delivery is merged on `main`.
- `VALIDATED` — canonical delivery is merged and its required validation/lifecycle evidence is complete.
- `READY` — Definition of Ready and hard dependencies are satisfied; the card may be selected under WIP limits.
- `IN_PROGRESS` — active unmerged work owns the current delivery.
- `BLOCKED` — one or more explicit prerequisites, decisions, fixtures or gates are unresolved.
- `DEFERRED` — valid work intentionally parked even if no hard dependency prevents design/execution.
- `TRACKER` — coordination epic only; child Test Cards own implementation and decisions.
- `DROPPED` — experiment explicitly rejected.
- `SUPERSEDED` — replaced by a later canonical delivery/record.

Candidate commits and their canonical merge commits represent one delivery when they contain the same capability. Lifecycle-only corrections are `DOCUMENTATION_CORRECTION`, not a second runtime capability.

## Portfolio/WIP contract

```text
OPEN
!= READY
!= NOW
```

Technical executable WIP is bounded:

```text
NOW executable cards       <= 2
READY executable backlog   <= 8
```

A card may be technically executable but intentionally `DEFERRED` to keep architecture exploration from becoming simultaneous implementation. Trackers never consume executable WIP.

Current reconciliation-matrix counts:

```text
NOW executable                 0
READY                          7 total / 4 executable
BLOCKED                        39 full cards + #16 full phase
TRACKER                        5 non-executable epics
```

## Non-negotiable product invariants

```text
Markdown/source truth
!= derived index/cache/ledger state
!= semantic vector state
!= query-conditioned state
!= working context
!= final answer

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

persistent memory
!= working context

more context
!= better context
```

Exactly three semantic drawers remain:

```text
facts
preferences
insights
```

QUMem-inspired work, intelligence/model work and Cognitive Continuity must not add a fourth semantic drawer. Additional concepts are facets, derived views or execution layers.

---

# Canonical execution board

This board is selection guidance, not permission to bypass the owning Test Card.

**73 open issues is not a 73-item queue.** At any moment the team selects from
`NOW` only (at most 2–4 concurrent items). `NEXT` and the rest of the
`Full execution queue` exist so the next pick is already known once a `NOW`
item lands — nobody should be choosing between 73 open cards. Everything that
is not in the queue below is a tracker/epic (coordination only, never a direct
implementation PR), research, documentation, a benchmark that enters only when
its capability needs evidence, or work intentionally deferred to control WIP.
Of the 73 open issues, roughly 40–50 are executable capabilities/tasks; the
rest are epics, trackers, docs, benchmarks, research and governance/automation
noise (see the buckets after the queue).

## NOW — pick only from here

```text
🥇 #155 Init UX / source selection              P0 release-critical
🥈 #135 Decomposer fallback integrity           P0 contract integrity
🥉 #16  Conflict resolver containment           P0 state safety
```

`#155` is the next release-critical executable card in the validated chain
`#153 -> #154 -> #155 -> #118 -> #134`. `#135`/`#16` run in parallel as a
Technical Integrity lane: `#135` fixes a live contract break (documented
`LLM failure -> heuristic fallback`, actual runtime `LLM failure -> []`) and
`#16` is the P0 destructive-newest-only-filtering containment fix. Neither
blocks `#155`; neither should be forgotten. When one of these three ships,
pull the next unblocked item from `NEXT` below.

## NEXT

```text
#118 Clean-room onboarding / CI bootstrap        after #155
#120 MCP transport/runtime robustness            can start in parallel
#87  LICENSE / CONTRIBUTING owner decision       can start in parallel
#134 PyPI release                                after #118 + #87
```

## Full execution queue

The complete ordering behind `NOW`/`NEXT`, grouped by phase. This is a
priority/dependency ordering, not a commitment that all 48 items become
active WIP soon — items later in the queue may still be individually labeled
`DEFERRED` until WIP allows (see `Deferred` below); their position here is
where they resume once selected.

```text
NOW — Product foundation
1  #155 Init UX / source selection
2  #135 Decomposer fallback integrity      (parallel)
3  #16  Conflict resolver containment      (parallel)
4  #118 Clean-room onboarding
5  #120 MCP transport/runtime robustness
6  #87  LICENSE / CONTRIBUTING             (parallel)
7  #134 PyPI release
-> TESSERA can be installed, configured, index a real project, and be used via MCP.

NEXT — Real memory system
8  #67  Quality Gate v2
9  #12  Incremental/idempotent indexing
10 #69  Text ingestion beyond Markdown
11 #70  Structural segmentation
12 #13  Corpus/metadata doctor
13 #157 Typed model profiles
14 #163 Local model lifecycle
15 #160 Capability pipeline
16 #158 Semantic embeddings
17 #176 AI legacy corpus enrichment
18 #192 Resumable/incremental enrichment runtime
-> TESSERA understands real corpora, indexes incrementally, does semantic
   retrieval, and can enrich legacy knowledge.

NEXT+ — Memory construction
19 #138 Role-aware episode construction
20 #136 Typed F/P/I decomposition
21 #137 Source episode / lineage preservation
22 #73  Versioned revision history
23 #15  Temporal model / state keys
24 #16  Full conflict/supersession (revisits the #16 containment fix above
        with the complete temporal-supersession semantics, once #73/#15 land)
-> Interactions become auditable, evolving memories (state evolves, newest
   does not always win).

THEN — Query intelligence
25 #139 Multiple query-conditioned information needs
26 #140 Bounded multi-query/multi-store retrieval planning
27 #25  Query-aware graph expansion
28 #26  Relation confidence
29 #159 Reranking
30 #141 Structured query-conditioned state (Fq/Tq/Iq)
-> Query -> correct evidence -> reconstructed state.

THEN — Trust and context
31 #71  Harness adapter registry
32 #32  Source authority/scope
33 #72  Instruction Resolver
34 #27  Evidence arbitration (source arbitration)
35 #20  Evidence sufficiency / conflict status / abstention
36 #169 Context Compiler
37 #167 Working Context
-> Minimum sufficient, trusted current state.

THEN — Agent integration
38 #171 Agent-facing semantic API (search/context/evidence/remember/inspect)
39 #196 Hooks Core (project/runtime-agnostic lifecycle hook contract)
40 #177 Runtime adapters (Claude/Codex/Gemini/Copilot/...)
41 #190 Integration UX (`tessera integrate <runtime>` / `tessera mcp setup`)
42 #191 Historical conversation import
43 #121 Official TESSERA Skills
44 #193 Skills/plugin/MCP distribution
-> Every integrated agent runtime shares the same TESSERA memory.

FINALLY — Autonomous learning
45 #19  Evidence-aware memory admission
46 #168 Long-Term Memory architecture contract (full)
47 #21  Experience traces / utility learning
48 #17  Adaptive HOW-to-retrieve strategy
-> Closes the loop: READ BEFORE REASONING, WRITE AFTER LEARNING.
```

## Deferred

Valid work intentionally parked to control WIP or avoid rework. Each is still
present in the `Full execution queue` above at the position it resumes from;
`DEFERRED` only means "not selectable right now."

```text
#17  adaptive HOW-to-retrieve strategy       -> queue #48
#19  evidence-aware memory admission          -> queue #45
#21  utility / experience learning             -> queue #47
#25  query-aware graph expansion               -> queue #27
#28  structured-evidence rendering ablation    -> benchmark, enters with #25/#26/#159 evidence
#119 broad CLI redesign umbrella               -> not yet queued; needs #166 first
#139 QUMem information-needs implementation    -> queue #25
#157 typed model profiles                      -> queue #13
#166 unified CLI presentation system           -> not yet queued
#80  architecture/roadmap visual assets        -> documentation-only, no dependency gate
```

`#25`, `#28`, `#139`, `#157` and `#166` have technically executable or
previously `READY` definitions, but this portfolio intentionally parks them
until the active release/safety foundations reduce WIP or their surrounding
semantics stabilize.

## Dependency graph

```text
FIRST PUBLIC RELEASE
#153 VALIDATED
  -> #154 source discovery VALIDATED
      -> #155 init UX READY
          -> #118 clean onboarding BLOCKED
              -> #134 PyPI release BLOCKED

#87 owner-approved LICENSE/contribution decision
  -------------------------------------> #134


INTELLIGENCE
#153 VALIDATED -> #157 typed model profiles DEFERRED by WIP
          ├-> #163 local model lifecycle
          ├-> #160 capability pipeline
          └-> #158 semantic embeddings
                 -> #159 reranking

#157 + #160 + #155 + validated retrieval capabilities
  -> #161 presets
#157 + #160 -> #162 diagnostics
#157 + #160 + #163 -> #165 local generation


QUMEM / QUERY STATE
#135 -> #136 typed F/P/I decomposition
     -> #137 lineage

#139 -> #140 retrieval planning

#73 -> #15 temporal/state semantics
          -> #16 full supersession

#140 + #137 + #15 + #16
  -> #141 Fq/Tq/Iq state
      -> #20 evidence status
      -> #142/#143 evaluation


AGENT COGNITIVE CONTINUITY
#168 Long-Term Memory
        +
#139 -> #140 -> #141 -> #20
        ↓
#169 Context Compiler
        ↓
#167 Working Context
        ↓
#171 Agent-facing semantic API
        ↓
consuming agent

#120 remains the separate MCP transport/runtime dependency for #171.
```

## Epics / trackers

```text
#14  Graph experiments
#18  Measurement / LongMemEval
#145 QUMem
#164 Intelligence
#170 Agent Cognitive Continuity
#178 End-to-end onboarding/integration/lifecycle UX epic
```

Epics/trackers do not receive direct feature implementation PRs; they are
coordination umbrellas whose children are the actual queue items above.

## Research

```text
#179 Cross-system memory lifecycle/hook architecture survey
      (MemPalace, Mem0, MemOS, Letta, Graphiti)
```

Research issues inform design (e.g. `#196`/`#177` above drew on `#179`'s
findings) but are not themselves implementation work.

## Benchmarks (parallel lane, not a final phase)

```text
#96  closed  LongMemEval V1 minimal reproducible baseline
#100 closed  Versioned benchmark ledger
#28  Structured Evidence rendering ablation
#103 LongMemEval V1 frozen-evidence reader baseline
#104 Versioned/calibrated LLM-as-a-judge contract
#105 LongMemEval V1 full-500 preregistered evaluation
#106 LongMemEval-V2 multimodal adapter
#142 QUMem frozen fidelity regression suite
#143 QUMem-aligned personalized-memory benchmark
```

Benchmarks enter the active queue only when the capability they measure needs
evidence — they are not scheduled as a terminal "phase 15".

## Documentation-only (not part of the execution queue)

```text
#78  remove project-specific references from legacy/deep-dive docs
#80  architecture/roadmap visual assets
#146 QUMem documentation truth (reconcile paper-fidelity claims)
```

## Owner decisions / admin

```text
#87 LICENSE / copyright ownership / CONTRIBUTING
```

`#87` is a direct release blocker (queue #6, parallel to `#155`) and must not
be solved by an agent inventing legal ownership.

## Automation noise (`[aw]`)

```text
#189 lifecycle drift reconciliation record       -> fixed by PR #197
#194 Detection Runs                              -> left open as audit trail
#195 TESSERA Issue Triage failed (Gemini AWF bug) -> fixed by PR #198
```

`[aw]`-prefixed issues are auto-filed failure/detection records from gh-aw
workflows, not roadmap features; they are closed once their underlying
automation problem is fixed, matching the existing pattern for `#183`-`#188`.

---

# Macro roadmap

## FASE 0 — FAZER FUNCIONAR

Status: `VALIDATED FOUNDATION`.

```text
source / memory
    -> canonical metadata + stable identity
    -> provenance / Evidence Ledger
    -> explicit relations + graph
    -> derived index
    -> deterministic retrieval
    -> structured evidence
```

Implemented foundation includes persistence, stable identity, source-backed evidence, basic relations/graph and deterministic retrieval. Advanced temporal/state/admission/intelligence/context capabilities remain experiments.

## FASE 1 — FAZER SER VERDADE

Status: `MOSTLY VALIDATED`.

Already validated:

```text
#68  retrieval contract parity
#74  deterministic-core / optional-LLM architecture
#92  truthful write safety/path containment
#93  cross-surface storage parity
#94  Markdown persistence integrity
#95  runtime independence
#96  LongMemEval V1 reproducible retrieval baseline
#100 benchmark governance
#112 public identity
#114 lifecycle/evolution governance
```

Still open:

```text
#16 P0 containment
#67 Quality Gate v2 / regression-gate integration
```

The P0 containment of #16 is independent from the later full temporal supersession experiment.

## FASE 2 — FAZER VIRAR PRODUTO

Status: architecture, packaging and Configuration v1 are validated. Productization v2 now owns the route to a trustworthy first public release.

```text
#115 repository architecture        VALIDATED
  -> #116 package/distribution       VALIDATED
       -> #117 config/discovery v1   VALIDATED
            -> #153 config v2        VALIDATED
                 -> #154 sources     VALIDATED
                      -> #155 init UX READY
                           -> #118 clean onboarding BLOCKED
                                -> #134 first PyPI release BLOCKED

#87 legal/repository entrypoint -------------------------------> #134

Parallel product surfaces:
#120 MCP runtime             READY
  -> #121 official Skills    BLOCKED

#119 broad CLI umbrella      DEFERRED
#166 presentation child      DEFERRED
```

#153 and #154 are satisfied. #155 is now the only remaining productization
implementation blocker before #118; #118 therefore stays `BLOCKED` until #155
is canonically validated.

The first PyPI release does not require #119/#120/#121 unless those cards discover a release-contract blocker before publication.

## FASE 3 — FAZER A MEMÓRIA E O RETRIEVAL MELHORES

Status: multiple experimental families exist, but they are dependency-routed and WIP-limited.

### Durable-memory lifecycle

```text
#67
 -> #12 incremental/idempotent indexing
     -> #73 revision history
         -> #15 temporal/state semantics
             -> #16 full supersession

#69 broader text ingestion
 -> #70 structural segmentation
     -> #13 corpus doctor

#19 admission and #21 utility remain later layers.
```

### Graph/evidence intelligence

```text
#14 TRACKER
#25 query-aware expansion
 -> #26 relation confidence
     -> #27 arbitration / #20 evidence status
```

### QUMem-derived construction/state

```text
#145 TRACKER

#135 fallback integrity
 -> #136 typed F/P/I
 -> #137 source episode/supporting-turn lineage

#138 role-aware episode construction

#139 information needs
 -> #140 multi-query/multi-store plan

#15/#16 temporal semantics
        +
#137/#140
 -> #141 structured Fq/Tq/Iq
     -> #20 evidence status
     -> #142/#143 evaluation

#144 public assisted parity only after semantics are validated.
```

Neither QUMem nor graph work replaces the deterministic core.

## FASE 4 — ADICIONAR INTELIGÊNCIA SEM PERDER O CORE

Parent tracker: #164.

```text
#153 configuration v2 VALIDATED
  -> #157 typed model profiles DEFERRED by portfolio WIP
       ├-> #163 local-model artifact lifecycle
       ├-> #158 semantic embeddings/index
       │    -> #159 reranking
       └-> #160 pipeline capability/fallback configuration
             ├-> #162 diagnostics
             └-> #165 local generative experiments

#155 + #157/#158/#160
  -> #161 Local / Private Hybrid / Cloud presets

validated retrieval capabilities
  -> #17 adaptive HOW-to-retrieve experiments
```

Provider/model identity is configuration, not product architecture:

```text
capability
-> typed profile
-> provider/model
```

The deterministic core must continue to operate with zero provider/model configuration.

## FASE 5 — CONTINUIDADE COGNITIVA DO AGENTE

Parent tracker: #170.

The architectural objective is not merely “the agent can search memory”; it is “the agent starts a bounded task with the right evidence-backed state and writes only durable learning afterward”.

```text
#168 LONG-TERM MEMORY
        ↓
#139 Information Needs
        ↓
#140 Retrieval Plan
        ↓
deterministic evidence retrieval
        ↓
#141 Query-Conditioned State
        ↓
#20 Evidence Status
        ↓
#169 Context Compiler
        ↓
#167 Working Context
        ↓
#171 Agent-facing Memory API
        ↓
CONSUMING AGENT
```

Ownership boundaries:

```text
#168 = durable memory boundary
#169 = selection + synthesis + context budgeting
#167 = packet identity + bootstrap + reuse + freshness/invalidation
#171 = semantic intents: search / context / evidence / remember / inspect
#120 = MCP server/transport/config/errors/timeouts/concurrency
```

Critical rule:

```text
READ BEFORE REASONING
WRITE AFTER LEARNING
```

but neither read nor write is blind: compilation is bounded/evidence-backed, and durable write remains admission/write-gated.

## FASE 6 — PROVAR QUE É MELHOR

Status: measurement infrastructure exists; broader answer-quality, personalized-memory and cognitive-continuity evidence remain future work.

Already available:

```text
deterministic sanity fixture
LongMemEval V1 dev-50 historical baseline (#96)
Benchmark Ledger / applicability (#100)
conditional benchmark CI
```

Open measurement tracks:

```text
#28  rendering ablation
#103 frozen-evidence reader
#104 calibrated judge
#105 LongMemEval V1 full-500
#106 LongMemEval-V2

#142 QUMem fidelity regression
#143 personalized-memory / preference-evolution

future Cognitive Continuity metrics:
time-to-first-reasoning
memory tool calls/run
context tokens
critical-context recall
cross-agent context drift
stale-context failures
```

---

## Reconciliation matrix

The first matching row for an Issue is the authoritative roadmap classification. `Class` distinguishes executable WIP from trackers, docs, architecture, evaluation and owner decisions.

| Issue | GitHub state | Lifecycle status | Class | Lane | Dependency / routing decision |
|---|---|---|---|---|---|
| [#68](https://github.com/LuigiFerronatto/TESSERA/issues/68) | closed | `VALIDATED` | FOUNDATION | Contract | Engine / CLI / MCP retrieval semantics aligned in PR #98. |
| [#74](https://github.com/LuigiFerronatto/TESSERA/issues/74) | closed | `VALIDATED` | FOUNDATION | Contract | ADR 0001 accepted in [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107), merge `0c0b638`, canonical `0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2`. |
| [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) | closed | `VALIDATED` | FOUNDATION | Contract | [PR #108](https://github.com/LuigiFerronatto/TESSERA/pull/108), canonical `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05`; see `PR_EVOLUTION_92.md`. |
| [#93](https://github.com/LuigiFerronatto/TESSERA/issues/93) | closed | `VALIDATED` | FOUNDATION | Contract | `KEEP`; canonical `c6124548f32b6dc5e1b7acf5127632bc6c75fccc`; see `PR_EVOLUTION_93.md`. |
| [#94](https://github.com/LuigiFerronatto/TESSERA/issues/94) | closed | `VALIDATED` | FOUNDATION | Contract | Canonical Markdown persistence integrity. |
| [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) | closed | `VALIDATED` | FOUNDATION | Contract | `KEEP`; canonical `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`. |
| [#96](https://github.com/LuigiFerronatto/TESSERA/issues/96) | closed | `VALIDATED` | FOUNDATION | Measurement | Reproducible LongMemEval V1 dev-50 historical retrieval baseline. |
| [#100](https://github.com/LuigiFerronatto/TESSERA/issues/100) | closed | `VALIDATED` | FOUNDATION | Measurement | Benchmark Ledger and `REQUIRED / SMOKE_ONLY / NOT_APPLICABLE`. |
| [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) | closed | `VALIDATED` | FOUNDATION | Product | Public identity/banner. |
| [#114](https://github.com/LuigiFerronatto/TESSERA/issues/114) | closed | `VALIDATED` | FOUNDATION | Governance | Evolution-auditable lifecycle governance. |
| [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) | closed | `VALIDATED` | FOUNDATION | Product | ADR 0002 / PR #128; canonical `b475f1cd805f86cc8ad9526e563e3c6fb8409ff1`; `KEEP`. |
| [#116](https://github.com/LuigiFerronatto/TESSERA/issues/116) | closed | `VALIDATED` | FOUNDATION | Product | Packaging PR #131 canonical `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4`; lifecycle `b3be96f4aa842a81c135b6ac87d3311ed292d339`. |
| [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117) | closed | `VALIDATED` | FOUNDATION | Product | `KEEP`; implementation `61cf76fbd6ed61972f0f5abae515ba9bffca4b55`; lifecycle `fc0ed763ad47f5eba88775f3517cbee99d00a8b9`. |
| [#147](https://github.com/LuigiFerronatto/TESSERA/issues/147) | closed | `VALIDATED` | GOVERNANCE | Docs | Roadmap/QUMem reconciliation #149 canonical `a13abbbba2138e48e237f14a182dd6746e3ec7d4`; lifecycle #156 canonical `0880ef3ec417735c105898039cc202450407af2b`. |
| [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16) | open | `READY` containment / `BLOCKED` full | EXECUTABLE | Safety | P0 containment can be selected; full supersession waits on #15/#73/#96. |
| [#67](https://github.com/LuigiFerronatto/TESSERA/issues/67) | open | `BLOCKED` | EXECUTABLE | Safety | #92, #93 and #95 dependencies are satisfied; still blocked on regression-gate integration. |
| [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) | open | `BLOCKED` | EXECUTABLE | Storage | Depends on #67/#94; incremental/idempotent indexing. |
| [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) | open | `BLOCKED` | EXECUTABLE | Sources | Depends on #12/#94; text ingestion beyond Markdown. |
| [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) | open | `BLOCKED` | EXECUTABLE | Sources | Depends on #12/#69; structural segmentation. |
| [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) | open | `BLOCKED` | EXECUTABLE | Sources | Depends on #12/#69/#70; corpus doctor, distinct from config/model doctor. |
| [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) | open | `BLOCKED` | EXECUTABLE | Storage | Depends on #12/#94; source/memory revision history. |
| [#15](https://github.com/LuigiFerronatto/TESSERA/issues/15) | open | `BLOCKED` | EXECUTABLE | Temporal | Depends on #73/#96; temporal/state semantics. `temporal_position` from #137 is not validity time. |
| [#19](https://github.com/LuigiFerronatto/TESSERA/issues/19) | open | `DEFERRED` | EXECUTABLE | Durable Memory | Evidence-aware admission: `worth remembering?` remains distinct from #92 `safe to persist?`. |
| [#21](https://github.com/LuigiFerronatto/TESSERA/issues/21) | open | `DEFERRED` | EXECUTABLE | Durable Memory | Utility/experience learning after admission/state become trustworthy. |
| [#14](https://github.com/LuigiFerronatto/TESSERA/issues/14) | open | `TRACKER` | TRACKER | Graph | Graph experiment epic; child execution in #25/#26. |
| [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) | open | `DEFERRED` | EXECUTABLE | Graph | #96 baseline complete. The previous "#25 graph-expansion card DoR completion" gate is superseded by live routing; technically executable but parked by WIP. |
| [#26](https://github.com/LuigiFerronatto/TESSERA/issues/26) | open | `BLOCKED` | EXECUTABLE | Graph | Requires a frozen #25 baseline; relation confidence separate from relevance. |
| [#32](https://github.com/LuigiFerronatto/TESSERA/issues/32) | open | `BLOCKED` | EXECUTABLE | Trust | Depends on #71; source authority/scope/precedence. |
| [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) | open | `BLOCKED` | EXECUTABLE | Trust | Depends on #69/#70; harness adapter registry. |
| [#72](https://github.com/LuigiFerronatto/TESSERA/issues/72) | open | `BLOCKED` | EXECUTABLE | Trust | Depends on #71/#32; deterministic instruction resolver. |
| [#27](https://github.com/LuigiFerronatto/TESSERA/issues/27) | open | `BLOCKED` | EXECUTABLE | Trust | Depends on #15/#16/#32/#72/#96; cross-source Evidence Arbitration. |
| [#20](https://github.com/LuigiFerronatto/TESSERA/issues/20) | open | `BLOCKED` | EXECUTABLE | Trust | Owns `sufficient / insufficient / conflicting / ambiguous`; state reconstruction belongs #141. |
| [#17](https://github.com/LuigiFerronatto/TESSERA/issues/17) | open | `DEFERRED` | EXECUTABLE | Retrieval | Owns HOW validated retrieval capabilities are selected/combined; depends on #140/#20/#74/#96 and relevant capability baselines. |
| [#18](https://github.com/LuigiFerronatto/TESSERA/issues/18) | open | `TRACKER` | TRACKER | Measurement | Measurement spine; #96/#100 complete, #28/#103–#106 open. |
| [#28](https://github.com/LuigiFerronatto/TESSERA/issues/28) | open | `DEFERRED` | EVALUATION | Measurement | #68/#96 complete; freeze evidence and vary renderer only. |
| [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103) | open | `BLOCKED` | EVALUATION | Measurement | Depends on #28/#74/#96/#100; frozen-evidence reader. |
| [#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) | open | `BLOCKED` | EVALUATION | Measurement | Depends on #74/#100/#103; calibrated judge. |
| [#105](https://github.com/LuigiFerronatto/TESSERA/issues/105) | open | `BLOCKED` | BENCHMARK | Measurement | Depends on #96/#100/#103/#104; LongMemEval V1 full-500. |
| [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) | open | `BLOCKED` | BENCHMARK | Measurement | Depends on #74/#100/#103/#104/#105; LongMemEval-V2. |
| [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) | open | `BLOCKED` | EXECUTABLE | Productization | #116/#117/#153/#154 are satisfied; remaining blocker is #155 Init UX. |
| [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) | open | `DEFERRED` | EXECUTABLE | CLI | Previous/live `READY` umbrella intentionally parked while #155 semantics stabilize; #166 owns presentation architecture. |
| [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) | open | `READY` | EXECUTABLE | Agent Integration | MCP startup/transport/config/schema/errors/timeouts/concurrency. Semantic memory intents belong #171. |
| [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121) | open | `BLOCKED` | EXECUTABLE | Agent Integration | Remaining blocker #120; official Skills only. |
| [#87](https://github.com/LuigiFerronatto/TESSERA/issues/87) | open | `BLOCKED` | ADMIN | Release | Owner legal decision required for LICENSE/copyright/CONTRIBUTING; direct #134 blocker. |
| [#134](https://github.com/LuigiFerronatto/TESSERA/issues/134) | open | `BLOCKED` | RELEASE_GATE | Productization | Requires #118 VALIDATED + #87. #153/#154 are satisfied; #155 remains the transitive productization blocker through #118. |
| [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135) | open | `READY` | EXECUTABLE | QUMem | P0 deterministic decomposition fallback; no hard dependency. |
| [#136](https://github.com/LuigiFerronatto/TESSERA/issues/136) | open | `BLOCKED` | EXECUTABLE | QUMem | Depends on #135/#74; F/P/I fidelity + 1-pass vs 3-pass. |
| [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) | open | `BLOCKED` | EXECUTABLE | QUMem | Depends on #135; source episode/supporting turns/temporal position. |
| [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) | open | `BLOCKED` | EXECUTABLE | QUMem | #74 satisfied; DoR still requires frozen reviewed episode-boundary fixture. |
| [#139](https://github.com/LuigiFerronatto/TESSERA/issues/139) | open | `DEFERRED` | EXECUTABLE | QUMem | Hard dependency #74 is satisfied; intentionally parked while release/safety lane is selected. |
| [#140](https://github.com/LuigiFerronatto/TESSERA/issues/140) | open | `BLOCKED` | EXECUTABLE | QUMem | Depends on #139/#74/#96; owns WHAT subqueries/stores retrieve evidence. |
| [#141](https://github.com/LuigiFerronatto/TESSERA/issues/141) | open | `BLOCKED` | EXECUTABLE | QUMem | Principal QUMem gap; depends on #140/#15/#16/#137/#74/#96; structured evidence-linked Fq/Tq/Iq. |
| [#142](https://github.com/LuigiFerronatto/TESSERA/issues/142) | open | `BLOCKED` | EVALUATION | QUMem | Full suite depends #135–#141; fixture design may start early, final acceptance waits for children. |
| [#143](https://github.com/LuigiFerronatto/TESSERA/issues/143) | open | `BLOCKED` | BENCHMARK | QUMem | Personalized-memory/preference-evolution benchmark after #136/#137/#138/#140/#141/#142/#96. |
| [#144](https://github.com/LuigiFerronatto/TESSERA/issues/144) | open | `BLOCKED` | EXECUTABLE | Agent Integration | Expose only validated assisted contracts across Python/CLI/MCP; coordinate #120/#171. |
| [#145](https://github.com/LuigiFerronatto/TESSERA/issues/145) | open | `TRACKER` | TRACKER | QUMem | QUMem epic; no direct implementation PR. |
| [#146](https://github.com/LuigiFerronatto/TESSERA/issues/146) | open | `READY` | DOCUMENTATION | Docs | QUMem paper-vs-runtime truth correction; `NOT_APPLICABLE`. |
| [#153](https://github.com/LuigiFerronatto/TESSERA/issues/153) | closed | `VALIDATED` | FOUNDATION | Productization | `KEEP`; PR #173 final candidate `72b2b0c44ecbdc6e5f45ed612f4eb9bb69c57cd4`, runtime commit `53f772cdd0fae369a2ed3954751667d5e4ea52c4`, canonical squash merge `2508676d472088733702b6ed920fc829df9a7681`. Candidate and merge are one delivery. |
| [#154](https://github.com/LuigiFerronatto/TESSERA/issues/154) | closed | `VALIDATED` | FOUNDATION | Productization | `KEEP`; PR #175 final candidate `06521763b4c3cf033c4d1e6a771ae105aad98e37`, canonical squash merge `05ce0dd234a7756d4a5ba315b77e4a6ec33c9429`; safe source discovery and `.tessera-ignore` are canonical. |
| [#155](https://github.com/LuigiFerronatto/TESSERA/issues/155) | open | `READY` | EXECUTABLE | Productization | #117/#153/#154 are satisfied; no active blocker remains. Owns interactive/non-interactive Init UX and is the next release-critical implementation candidate. |
| [#157](https://github.com/LuigiFerronatto/TESSERA/issues/157) | open | `DEFERRED` | EXECUTABLE | Intelligence | #153 and #74 are satisfied; no hard dependency remains, but typed model profiles are deliberately parked under portfolio WIP while the release-critical #155 lane is primary. |
| [#158](https://github.com/LuigiFerronatto/TESSERA/issues/158) | open | `BLOCKED` | EXECUTABLE | Intelligence | Depends on #157/#153/#96; optional semantic embeddings + versioned semantic index. |
| [#159](https://github.com/LuigiFerronatto/TESSERA/issues/159) | open | `BLOCKED` | EVALUATION | Intelligence | Depends on #157/#158/#96; reranking over frozen candidates. |
| [#160](https://github.com/LuigiFerronatto/TESSERA/issues/160) | open | `BLOCKED` | EXECUTABLE | Intelligence | Depends on #157/#74; capability-level pipeline modes/fallbacks. |
| [#161](https://github.com/LuigiFerronatto/TESSERA/issues/161) | open | `BLOCKED` | EXECUTABLE | Intelligence | Depends on #157/#158/#160/#155; Local/Private Hybrid/Cloud presets. |
| [#162](https://github.com/LuigiFerronatto/TESSERA/issues/162) | open | `BLOCKED` | EXECUTABLE | Intelligence | Depends on #157/#160; model/pipeline diagnostics. |
| [#163](https://github.com/LuigiFerronatto/TESSERA/issues/163) | open | `BLOCKED` | EXECUTABLE | Intelligence | Depends on #157; explicit local model artifact/cache/device/offline lifecycle. |
| [#164](https://github.com/LuigiFerronatto/TESSERA/issues/164) | open | `TRACKER` | TRACKER | Intelligence | Provider-agnostic Intelligence epic; child cards #157–#163/#165 own decisions. |
| [#165](https://github.com/LuigiFerronatto/TESSERA/issues/165) | open | `BLOCKED` | EVALUATION | Intelligence | Depends on #157/#160/#163; local generative memory organization/reasoning. |
| [#166](https://github.com/LuigiFerronatto/TESSERA/issues/166) | open | `DEFERRED` | EXECUTABLE | CLI | Technically executable from validated #112/#116/#117, but parked until #155 semantics stabilize. |
| [#167](https://github.com/LuigiFerronatto/TESSERA/issues/167) | open | `BLOCKED` | EXECUTABLE | Cognitive Continuity | Working Context packet identity/bootstrap/reuse/freshness; depends on #169 and #20 as applicable; consumes #168. |
| [#168](https://github.com/LuigiFerronatto/TESSERA/issues/168) | open | `READY` | ARCHITECTURE | Cognitive Continuity | Long-Term Memory durable boundary; validated foundation satisfied; implementation behavior remains dependency-routed to child cards. |
| [#169](https://github.com/LuigiFerronatto/TESSERA/issues/169) | open | `BLOCKED` | EXECUTABLE | Cognitive Continuity | Context Compiler; depends on #139/#140/#141/#20 and consumes #168. |
| [#170](https://github.com/LuigiFerronatto/TESSERA/issues/170) | open | `TRACKER` | TRACKER | Cognitive Continuity | Agent Cognitive Continuity epic; no direct feature PR. |
| [#171](https://github.com/LuigiFerronatto/TESSERA/issues/171) | open | `BLOCKED` | EXECUTABLE | Agent Integration | Semantic `search/context/evidence/remember/inspect`; depends on #120 + #167/#169, with #19/#92 governing durable remember. |
| [#78](https://github.com/LuigiFerronatto/TESSERA/issues/78) | open | `READY` | DOCUMENTATION | Docs | Project-agnostic legacy/deep-dive cleanup; coordinate #146, not technical WIP. |
| [#80](https://github.com/LuigiFerronatto/TESSERA/issues/80) | open | `DEFERRED` | DOCUMENTATION | Docs | Visual/architecture documentation after target contracts stabilize. |
| [#172](https://github.com/LuigiFerronatto/TESSERA/issues/172) | closed | `VALIDATED` | GOVERNANCE | Portfolio | `KEEP`; canonical execution funnel and WIP taxonomy reconciled by PR #174 after the #173 merge. |
| [#181](https://github.com/LuigiFerronatto/TESSERA/issues/181) | closed | `TRACKER` (`IMPLEMENTED`, Stage A) | TRACKER | Governance | Coordination epic for the agentic repository-governance system; not itself executable. `KEEP`; PR #182 final candidate `30bfdfa02735c9d68ce546182e00a68c205a1b6b`, canonical merge `c349bac48c5fb1427f15615fc26e4fbc748ed320`. Delivered Stage A (report-only/comment-only/draft-only) governance automation; not `VALIDATED`: Stage B+ auto-merge wiring, the real GraphQL unresolved-thread check, and cross-engine review evaluation remain follow-ups under this tracker. No downstream routing changes. |

---

# Ownership boundaries that must not collapse

## QUMem / retrieval

```text
#139 = what historical facets must be established?
#140 = WHAT sub-queries/stores should retrieve them?
#17  = HOW each frozen retrieval operation should execute efficiently?

#141 = what state does evidence imply for this query?
#20  = is the evidence/state sufficient, insufficient, conflicting or ambiguous?

interaction temporal_position (#137)
!= temporal validity/state semantics (#15)

semantic episode membership (#138)
!= Beginning/Middle/End TESSERA representation
```

## Intelligence

```text
#157 = typed capability/model profiles
#158 = semantic candidate generation/index
#159 = reranking a frozen candidate set
#160 = execution mode/profile/fallback per pipeline capability
#163 = local model artifact lifecycle
#165 = local generative behavior experiments
#17  = adaptive runtime choice among validated retrieval capabilities
```

## Cognitive Continuity

```text
#168 Long-Term Memory
!=
#169 Context Compiler
!=
#167 Working Context
!=
#171 Agent-facing semantic API
!=
#120 MCP transport/runtime
```

The intended direction is:

```text
Long-Term Memory
-> Context Compiler
-> Working Context
-> Agent
```

Raw search/evidence remain available for drill-down; working context does not become durable truth.

---

# Target architecture — layered, not monolithic

## Deterministic core path

```text
QUERY
  |
  v
Configuration / Source Selection
  |
  v
Deterministic Candidate Retrieval
  |
  +--> lexical/basic relation signals today
  +--> semantic lane later (#158)
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
Admission (#19, when validated)
  |
  v
Canonical Write Gate (#92)
  |
  v
LONG-TERM MEMORY (#168 boundary)
```

#135 first restores deterministic fallback integrity. It does not by itself validate QUMem fidelity.

## Optional query-conditioned/context path

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
TESSERA Evidence Retrieval
  |
  v
Structured Fq / Tq / Iq State (#141)
  |
  v
Evidence Status / Abstention (#20)
  |
  v
Context Compiler (#169)
  |
  v
Working Context Packet (#167)
  |
  v
Agent-facing API (#171)
  |
  v
CONSUMING AGENT
```

TESSERA returns evidence and optional structured derived state/context; it does not take final-answer authority from the consuming agent.

---

# Research-derived experiment map

External work changes the next experiment; citation does not equal implementation.

| Research signal | TESSERA experiment | Decision question |
|---|---|---|
| GraphMemix | #25 query-aware graph expansion | Which edges/evidence are useful for this query under a budget? |
| CaSKG | #26 relation confidence | Is an edge trustworthy independently of query relevance? |
| MemToC | #27 + #20 | How do we preserve disagreement and signal sufficiency/conflict/ambiguity? |
| RENDER | #28 rendering ablation | Does structured evidence presentation help when retrieval is frozen? |
| QUMem | #145 / #135–#144 | Which construction/planning/state mechanisms improve TESSERA while preserving provenance/core independence? |
| Personalized-memory benchmarks | #143 | Do additions improve preference evolution/current-state tasks, not only factual recall? |

#146 owns broader QUMem paper-fidelity documentation truth.

---

# Measurement policy

Benchmark applicability follows #100:

```text
REQUIRED
  semantic retrieval / memory-state experiment requires declared benchmark evidence

SMOKE_ONLY
  config/runtime/release/integrity work that should preserve retrieval semantics

NOT_APPLICABLE
  documentation/governance-only work
```

LongMemEval is not run automatically for `SMOKE_ONLY` or `NOT_APPLICABLE`.

Historical deterministic sanity reference:

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

#146 owns QUMem research-fidelity truth. #78 owns project-agnostic legacy/deep-dive cleanup. #80 is deferred visual documentation.

For the first public release:

```text
#153 VALIDATED
-> #154 VALIDATED
-> #155 VALIDATED
-> #118 VALIDATED

AND

#87 owner-approved legal entrypoint

=> #134 TestPyPI/PyPI release gate
```

No roadmap entry may imply that `tessera` is already the published PyPI distribution name.

---

# Immediate selection guidance

The repository uses bounded WIP rather than starting every technically executable card at once.

After the #154 canonical merge and lifecycle reconciliation:

```text
#154 Safe project source discovery + .tessera-ignore  VALIDATED
#155 Init UX / source selection                          READY — next primary
#135/#16 optional parallel integrity lane              not selected
```

Why #155 is next:
- #153 validated the store/source/index boundary;
- #154 now validates safe discovery, classification, clustering and ignore policy;
- #155 is the remaining onboarding implementation needed before the clean-room #118 gate;
- #155 directly unlocks #118, which gates #134.

Why one integrity card may still run later in parallel:
- #135 fixes a concrete P0 contract mismatch and unlocks #136/#137;
- #16 containment prevents destructive preference/history loss needed by later state work.

Do not start #166 before #155 semantics stabilize. Keep #157 deliberately deferred while the release-critical product lane is selected. Do not start #167/#169/#171 before their state/context prerequisites.

---

# Current concise map

```text
FOUNDATION / TRUTH
#68/#74/#92/#93/#94/#95/#96/#100/#112/#114  VALIDATED
#16 containment                                  READY
#67 Quality Gate                                 BLOCKED

PRODUCTIZATION / RELEASE
#115 VALIDATED
 -> #116 VALIDATED
     -> #117 VALIDATED
         -> #153 VALIDATED
             -> #154 VALIDATED
                 -> #155 READY
                     -> #118 BLOCKED
                         -> #134 BLOCKED
#87 ADMIN ------------------------------------------^

#120 READY -> #121 BLOCKED
#119/#166 DEFERRED

INTELLIGENCE EPIC #164                             TRACKER
#153 VALIDATED -> #157 DEFERRED -> #158/#160/#163 -> #159/#162/#165
#155 + validated intelligence -> #161
later #17 adaptive retrieval

QUMEM EPIC #145                                    TRACKER
#135 READY
#136/#137 BLOCKED
#138 BLOCKED
#139 DEFERRED -> #140 BLOCKED
#73 -> #15 -> #16 full
#141/#142/#143/#144 BLOCKED
#146 READY docs

COGNITIVE CONTINUITY EPIC #170                     TRACKER
#168 READY architecture
#139 -> #140 -> #141 -> #20 -> #169 -> #167 -> #171
#120 provides MCP transport, not context semantics

GRAPH / MEASUREMENT
#25 DEFERRED -> #26 BLOCKED
#28 DEFERRED -> #103 -> #104 -> #105 -> #106
```

This map is routing, not permission to bypass each Issue/Test Card's Definition of Ready, benchmark applicability, evidence requirement or lifecycle contract.
