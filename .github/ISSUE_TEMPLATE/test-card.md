---
name: TESSERA Test Card
description: Define one TESSERA change, its purpose, and its measurable decision gate.
title: "[Phase] "
labels: enhancement
assignees: ''
---

<!--
Language contract: write the issue title and authored prose in English.
Quoted source material, logs, commands, identifiers, and localized product
output may remain in their original language.

Describe current behavior as verified fact. Describe target behavior as a plan
until a canonical merge and post-merge validation establish it.
-->

## Summary
<!-- In 2-4 lines: what is being proposed or investigated? -->

## Purpose
<!-- Why does TESSERA or its users need this? What decision will this issue enable? -->

## Problem and current behavior
<!-- What happens on canonical main today? Include a concrete trigger and output when possible. -->

## Target behavior
<!-- What observable result should exist if this card earns KEEP? -->

## User-visible example
```text
trigger/input -> current result -> expected result
```

## Scope

### In scope
-

### Out of scope
<!-- Name adjacent work this issue must not absorb. -->
-

## Portfolio routing
- **Type:** test-card | bug | benchmark | ADR | documentation | governance
- **Status:** triage | ready | running | blocked | decision
- **Priority:** P0 | P1 | P2 | P3
- **Phase:** M0 | M1 | M2 | M3 | M4 | M5
- **Owner:**
- **Parent epic:**
- **Research source:**
- **Depends on:** <!-- Closed issues only when status=ready. -->
- **Unlocks:**
- **Timebox:**
- **Compute budget:**

## Decision question
<!-- Ask one binary or explicit multi-option question. Split multiple decisions into separate cards. -->

## Success criteria
<!-- Each item must be objectively observable. -->
- [ ]

## Validation plan

### Baseline
<!-- Record current behavior, metric, artifact, or reproducible command. -->

### Hypothesis
<!-- If we implement/change X, we expect Y because Z. -->

### Experiment and controls
<!-- State what changes and what stays fixed: fixture, dataset, seed, reader, candidate set, budget, and environment. -->

### Metrics and guardrails
- **Primary decision metric:**
- **Quality/safety guardrails:**
- **Cost:** <!-- p50/p95, tokens, storage growth, and write amplification when applicable. -->

### Failure signals
- [ ]

### Stop criteria
- [ ] A dependency, baseline, or metric becomes ambiguous.
- [ ] The timebox or compute budget is exhausted without new evidence.
- [ ] A high-risk silent behavior or source mutation is found.

## Capability state and repository evolution

### Previous capability state
<!-- What exists on canonical main? Separate runtime, benchmark, docs, governance, and ADR state. -->

### Deliveries that established the current state
<!-- Verify merged PRs and commits; include closed-unmerged or superseded attempts. -->

| PR | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence | Supersedes |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

<!-- Do not count identical heads or merge commits as separate deliveries. -->

### Target capability state
<!-- Restate the exact observable contract if this card earns KEEP. -->

### What will remain unimplemented
<!-- Keep this synchronized with Out of scope. -->

### Roadmap evolution
<!-- Name the expected ROADMAP status or dependency change. -->

## Plain-language stage record
- **Path:** `docs/test-cards/<issue>-<slug>.md | NOT_APPLICABLE`
- **Record status:** `PLANNED | IN_PROGRESS | IMPLEMENTED | VALIDATED | BLOCKED | SUPERSEDED`

<!--
Create applicable records from docs/test-cards/TEMPLATE.md. Keep current and
target behavior, evidence, and limitations separate. An open PR is never
IMPLEMENTED or VALIDATED.
-->

## Dependencies
<!-- Link issues rather than recording hidden TODOs. -->

## Risks and rollback
<!-- State failure impact, feature flag/data rebuild needs, and the exact revert path. -->

## Evidence
<!-- Add CI runs, benchmark artifacts, outputs, screenshots, or reproducible commands during execution. -->

## Learnings
<!-- Record surprises, failures, and limitations as well as successful results. -->

## Decision
- [ ] KEEP
- [ ] ITERATE
- [ ] REVERT
- [ ] DROP
- [ ] DEFER

### Decision rationale
<!-- Explain how the evidence supports the selected decision. -->

## Pull request
<!-- Add the PR when implementation starts. Use `Closes #<issue>` when appropriate. -->
