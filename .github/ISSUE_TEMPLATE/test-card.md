---
name: TESSERA Test Card
description: Propose and evaluate one TESSERA task as a testable hypothesis.
title: "[Phase] "
labels: enhancement
assignees: ''
---

## Executive takeaway
<!-- 2–4 lines: why this matters to TESSERA and what decision this card should enable. -->

## Portfolio routing
- **Type:** test-card | bug | benchmark | ADR | documentation
- **Status:** triage | ready | running | blocked | decision
- **Priority:** P0 | P1 | P2 | P3
- **Phase:** M0 | M1 | M2 | M3 | M4 | M5
- **Owner:**
- **Parent epic:**
- **Research source:**
- **Depends on:** <!-- Closed Issues only when status=ready. -->
- **Unlocks:**
- **Timebox:**
- **Compute budget:**

## Decision question
<!-- One binary or explicit multi-option decision. If there are several decisions, split the card. -->

## Em linguagem simples
<!-- Explain the problem as if you were telling another engineer why we are trying this. -->

## Plain-language stage record
- **Path:** `docs/test-cards/<issue>-<slug>.md`
- **Record status:** `PLANNED | IN_PROGRESS | IMPLEMENTED | VALIDATED | BLOCKED | SUPERSEDED`

<!--
Create the record from docs/test-cards/TEMPLATE.md. Keep current behavior,
target behavior, evidence and limitations separate. An open PR is never
IMPLEMENTED or VALIDATED.
-->

## Capability state and repository evolution

### Previous capability state
<!-- What exists on main now? Distinguish runtime, benchmark, documentation, governance and ADR state. -->

### Deliveries that established the current state
<!-- Audit relevant merged PRs and merge commits. Include closed-unmerged/superseded PRs. Do not infer delivery from titles alone. -->

| PR | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence | Supersedes |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

<!-- Do not count identical heads or merge commits as separate deliveries. -->

### Target capability state
<!-- State the exact observable contract if this card earns KEEP. -->

### What will remain unimplemented
<!-- Prevent this card from silently absorbing adjacent roadmap work. -->

### Roadmap evolution
<!-- Name the docs/ROADMAP.md entry/status/dependency change expected from this work. -->

## Objetivo
<!-- One concrete task. One Issue = one decisionable unit of work. -->

## Why now?
<!-- Dependency, observed failure, benchmark gap or product need. -->

## Test Card

### Hypothesis
<!-- If we implement/change X, we expect Y because Z. -->

### Baseline
<!-- What happens today? Include query/output/metric/artifact when possible. -->

### Experiment
<!-- What will change, what stays fixed and what is the comparison/control? -->

### Controls and fixed variables
<!-- Dataset/version, fixture, seed, reader, candidate set, token budget and environment. -->

### Metrics
<!-- Examples: Hit@k, MRR, nDCG, QA accuracy, evidence hit, tokens, latency, provenance correctness. -->

- **Primary decision metric:**
- **Quality/safety guardrails:**
- **Cost:** p50/p95, tokens, storage growth and write amplification when applicable.

### Success criteria
- [ ]

### Failure signals
- [ ]

### Stop criteria
- [ ] Dependency, baseline or metric becomes ambiguous.
- [ ] Timebox/compute budget is exhausted without new evidence.
- [ ] A high-risk silent behavior or source mutation is found.

### Evidence
<!-- Links to CI runs, benchmark artifacts, query outputs, screenshots or reproducible commands. -->

### Learnings
<!-- Update during the task. Capture surprises, failures and limitations, not only successes. -->

### Decision
- [ ] KEEP
- [ ] ITERATE
- [ ] REVERT
- [ ] DROP
- [ ] DEFER

### Decision rationale
<!-- Why did the evidence lead to this decision? -->

## Technical scope
### In scope
- 

### Out of scope
- 

## Dependencies
<!-- Link Issues, not hidden TODOs. -->

## Rollback
<!-- Feature flag, data migration/rebuild and exact revert path. -->

## Example / expected behavior
```text
query -> retrieval -> structured evidence
```

## PR
<!-- Add PR link when implementation starts. PR should use `Closes #<issue>` when appropriate. -->
