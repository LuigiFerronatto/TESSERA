# TESSERA Test Card Operating Model

TESSERA uses Test Cards to make one auditable decision at a time. A paper is a research signal, an implementation is a candidate, and only reproducible evidence can produce a KEEP decision.

## Portfolio structure

| Type | Purpose | Produces a direct implementation PR? |
| --- | --- | --- |
| Epic | Tracks a research/program outcome and child cards | No |
| Test Card | Answers one explicit product or architecture question | Usually |
| Bug | Restores an already-promised contract | Yes |
| Benchmark | Creates a reproducible measurement capability | Yes |
| ADR | Decides a boundary before implementation | Documentation first |
| Documentation | Aligns public/current/target descriptions | Yes, docs-only |

Authoritative phases:

1. **M0 — Contract & Safety**
2. **M1 — Measurement Spine**
3. **M2 — Storage & Identity**
4. **M3 — Retrieval & Graph**
5. **M4 — Temporal & Trust**
6. **M5 — Adaptive Learning**

## Definition of Ready

A card is ready only when:

- it asks exactly one decision question;
- every dependency is closed;
- baseline, fixture and reproducible command are defined;
- primary metric and regression guardrails are explicit;
- success, failure and stop conditions are objectively observable;
- in-scope, out-of-scope, timebox, cost budget and rollback are explicit;
- risky behavior is protected by a feature flag or an equivalent reversible mechanism.

## Work-in-progress policy

- Maximum **two implementation cards** running at once.
- One benchmark or documentation lane may run in parallel.
- Epics never consume implementation WIP.
- New discoveries become triage issues instead of expanding the active card.
- A benchmark rerun is evidence for a feature PR, not a reverse dependency from the harness to that feature.

## Execution loop

1. Select the highest-priority ready card.
2. Create branch test-card/ISSUE-SLUG.
3. Capture and attach the baseline before changing behavior.
4. Implement the smallest controlled experiment.
5. Run unit, contract, smoke, sanity and card-specific benchmark gates.
6. Update **Evidence** and **Learnings**, including failed hypotheses.
7. Record KEEP, ITERATE, REVERT, DROP or DEFER.
8. Open/complete the PR with exact commands, before/after metrics, costs and regressions.
9. Merge only when the success gate and recorded decision allow it.

## Benchmark applicability

Every pull request declares exactly one benchmark level:

- `REQUIRED` for changes that can affect ingestion, segmentation, canonical
  memory representation, indexing, retrieval/ranking, query compilation, graph
  expansion, temporal/conflict behavior, evidence selection/reconstruction, or
  benchmark adapters and metrics.
- `SMOKE_ONLY` for integration work that should not alter retrieval quality,
  such as write validation, configuration parity, transport, diagnostics,
  packaging, and isolated public-contract fixes. A rationale is mandatory.
- `NOT_APPLICABLE` for documentation, governance, branding, or non-executable
  repository metadata. A rationale is mandatory.

The declaration and PR evidence are authoritative and reviewable; a filename by
itself does not decide applicability. See [`BENCHMARK_CI.md`](BENCHMARK_CI.md)
for CI tiers, frozen inputs, and failure semantics.

## Stop conditions

Move a card to blocked when:

- its dependency graph becomes ambiguous or cyclic;
- no reproducible baseline exists;
- the primary metric cannot be computed;
- source text/evidence is mutated without an auditable lifecycle;
- a mandatory LLM enters the basic path without an approved ADR;
- current and experimental behavior cannot be distinguished;
- the timebox or compute budget is exhausted without new evidence;
- a high-risk silent behavior is discovered.

## Current execution waves

### M0 — Contract & Safety

- #68 Engine/CLI/MCP response contract
- #92 truthful write-gate contract
- #93 storage configuration parity
- #94 persist-format contract
- #95 legacy runtime decoupling
- #67 regression gates for those contracts
- #74 deterministic core versus optional LLM ADR
- #16 immediate containment of the silent conflict resolver

### M1 — Measurement Spine

- #96 LongMemEval V1 minimal reproducible baseline
- #28 structured-evidence rendering ablation

### M2–M5

Continue in the authoritative dependency order recorded in each GitHub issue:

storage/identity → retrieval/graph → temporal/trust → adaptive learning.

## Codex handoff contract

Every Codex task must return:

- decision and rationale;
- exact commands;
- before/after metrics;
- evidence/artifact links;
- regressions, safety findings and costs;
- the next card that became ready.

Passing tests is necessary but not sufficient. A research-derived capability is not a TESSERA claim until its Test Card records reproducible evidence and a decision.
