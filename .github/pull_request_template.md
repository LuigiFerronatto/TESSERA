## Executive takeaway
<!-- In 2–4 lines: what changed, why does it matter, and what is the decision impact? -->

## Em linguagem simples
<!-- Explain the task conversationally before implementation detail. -->

## Objective
<!-- One concrete problem this PR is trying to solve. -->

## Issue / Test Card
Closes #

**Hypothesis:**

**Baseline:**

**Success gate:**

**Decision:** `PENDING | KEEP | ITERATE | REVERT | DROP | DEFER`

## PR Evolution Audit

<!--
Before implementation, reconstruct the repository evolution relevant to this
contract. Inspect merged PRs, canonical merge commits, changed files, linked
issues/decisions, benchmark records, review-time P0 fixes and current main.
Include closed-unmerged PRs when superseded. Do not infer delivery from titles.
Do not count identical heads or merge commits as separate deliveries.
-->

| PR | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence | Supersedes |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

**Primary delivery type:** `runtime implementation | benchmark infrastructure | documentation correction | governance | architecture decision | superseded operational PR`

## Capability-state reconciliation

1. **Previous capability state:**
2. **PRs/commits that established it:**
3. **Change introduced by this PR:**
4. **Candidate/current capability state:**
5. **What remains unimplemented:**
6. **Benchmark before/after:**
7. **Newly unlocked work:**
8. **Roadmap evolution entry:**

## Change classification

**Category:** `Added | Changed | Fixed | Experimental | Deprecated | Removed | N/A`

**Contract surfaces affected:**
- [ ] Python Engine/API
- [ ] CLI
- [ ] MCP
- [ ] Persistence / index / schema
- [ ] Documentation
- [ ] Benchmark / evaluation
- [ ] None

**Documentation impact:** `YES | NO`
<!-- Link docs changed or explain why none are needed. -->

**Plain-language stage record:** `docs/test-cards/<issue>-<slug>.md | NOT_APPLICABLE`
<!-- Update status, PR/head evidence, before/after, validation and limitations. -->

## Benchmark applicability

<!-- Replace the choices below with exactly one value. A rationale is mandatory for SMOKE_ONLY and NOT_APPLICABLE. -->
Benchmark applicability: REQUIRED | SMOKE_ONLY | NOT_APPLICABLE
<!-- REQUIRED must name exactly one numeric Test Card issue, for example: Benchmark issue: #123 -->
Benchmark issue: #
Benchmark rationale:

## Technical implementation
<!-- What changed in code/data/docs? Keep this implementation-oriented. -->
- 

# Evaluation Card

## Tests
```bash
# Exact reproducible commands, or explain which existing CI jobs cover this PR.
```

## Evaluation
<!-- What behavior did you evaluate beyond “tests passed”? Include benchmark/sanity evidence when relevant. -->

| Metric | Baseline | This PR | Delta |
| --- | ---: | ---: | ---: |
|  |  |  |  |

## Before vs After
### Before
```text

```

### After
```text

```

## Output examples
<!-- Real CLI/API/MCP/output snippets when behavior changes. For docs-only work, show the resulting public contract/structure. -->
```text

```

## Known regressions
<!-- Be explicit. “None observed” is acceptable only after checking the relevant gates. -->
- 

## Changelog
- [ ] `CHANGELOG.md` updated
- [ ] N/A — rationale below

**Changelog category:** `Added | Changed | Fixed | Experimental | Deprecated | Removed | N/A`

**Rationale / entry:**
<!-- Required even for N/A. Follow docs/CHANGE_POLICY.md. -->

## Learnings
### What worked
- 

### What failed / surprised us
- 

### Known limitations
- 

## Public-surface / architecture invariants
- [ ] Public docs, examples, fixtures, benchmark data and runtime-facing configuration remain project-agnostic.
- [ ] Source files remain the source of truth; indexes/artifacts are derived and rebuildable.
- [ ] TESSERA returns structured evidence rather than silently replacing consuming-agent cognition.
- [ ] Exactly 3 semantic drawers remain: `facts`, `preferences`, `insights`.
- [ ] New concepts remain facets/metadata unless a separate Test Card explicitly changes that contract.
- [ ] No mandatory generative LLM was introduced in the basic path.
- [ ] Retrieval relevance was not conflated with confidence, authority, temporal validity, relation confidence or utility.
- [ ] No silent mutation of user source files.
- [ ] Current capabilities and target/experimental architecture are not presented as the same thing.

## Post-merge lifecycle sync
<!--
Before claiming completion, replace candidate/head evidence with the canonical
merge commit; update Evidence/Learnings/Decision, docs/ROADMAP.md and the
plain-language stage record. If this cannot happen in the implementation PR,
open a minimal lifecycle-sync PR and link it here.
-->

- [ ] Canonical merge commit recorded after merge
- [ ] Issue state and Decision reconciled
- [ ] Roadmap status/dependencies reconciled
- [ ] Plain-language record moved from IN_PROGRESS to final state only after merge
- [ ] Closed-unmerged/superseded operational PRs preserved in the audit

## Follow-ups
<!-- Unrelated/new work becomes a new Issue/Test Card. -->
- [ ] None

## Merge gate
- [ ] Issue/Test Card linked
- [ ] PR category + contract surfaces declared
- [ ] Changelog updated or explicitly N/A with rationale
- [ ] Tests green
- [ ] Relevant contract/smoke/sanity/benchmark gate green or explicitly waived with rationale
- [ ] Evidence & Learnings updated in the Issue/Test Card
- [ ] Plain-language stage record created/updated or explicitly NOT_APPLICABLE
- [ ] Known regressions recorded
- [ ] Final decision recorded
- [ ] PR Evolution Audit verified against canonical merge commits and changed files
- [ ] Capability-state reconciliation and roadmap evolution completed
- [ ] Post-merge lifecycle sync path declared
