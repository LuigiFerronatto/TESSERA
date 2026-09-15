<!--
Language contract: write the PR title and authored prose in English.
Quoted source material, logs, commands, identifiers, and localized product
output may remain in their original language.

Lead with the delivered behavior and its purpose. Keep plans, verified results,
and post-merge work clearly separated.
-->

## Summary
<!-- In 2-4 lines: what changed? Describe the delivered behavior, not the work history. -->

## Purpose
<!-- Why is this change needed, and what user/product/maintenance outcome does it create? -->

## Issue / Test Card
Closes #

**Decision question:**

**Hypothesis:**

**Success gate:**

**Decision:** `PENDING | KEEP | ITERATE | REVERT | DROP | DEFER`

## Behavior change

### Before
<!-- Concrete trigger and previous output/behavior. -->
```text

```

### After
<!-- The same trigger and the resulting output/behavior. -->
```text

```

### User-visible impact
<!-- State what a user, integrator, or maintainer will notice. Use N/A with a reason when nothing is visible. -->

## Scope

### In scope
-

### Out of scope
<!-- Name adjacent work intentionally excluded from this PR. -->
-

## Technical implementation
<!-- Explain how the final change works. Keep chronological debugging history out unless it affects review. -->
-

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
<!-- Link changed docs or explain why no documentation is needed. -->

**Plain-language stage record:** `docs/test-cards/<issue>-<slug>.md | NOT_APPLICABLE`
<!-- Update status, PR/head evidence, before/after behavior, validation, and limitations. -->

## PR Evolution Audit
<!--
Reconstruct only the history needed to review this contract. Verify merged PRs,
canonical commits, changed surfaces, decisions, and superseded attempts. Do not
infer delivery from titles. Do not count identical heads or merge commits as
separate deliveries.
-->

| PR | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence | Supersedes |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

**Primary delivery type:** `runtime implementation | benchmark infrastructure | documentation correction | governance | architecture decision | superseded operational PR`

### Capability-state reconciliation
1. **Previous capability state:**
2. **Change introduced by this PR:**
3. **Candidate capability state:**
4. **What remains unimplemented:**
5. **Benchmark before/after:**
6. **Newly unlocked work:**
7. **Roadmap evolution entry:**

## Validation

### Reproducible tests
```bash
# Exact commands, or the exact CI jobs that cover this PR.
```

### Evaluation evidence
<!-- Evaluate observable behavior beyond “tests passed.” Link exact-head CI and benchmark artifacts. -->

| Metric / invariant | Baseline | This PR | Decision impact |
| --- | ---: | ---: | --- |
|  |  |  |  |

### Output examples
<!-- Real CLI/API/MCP output when behavior changes. For docs-only work, show the resulting contract. -->
```text

```

## Benchmark applicability
<!-- Replace the choices with exactly one value. Rationale is mandatory for SMOKE_ONLY and NOT_APPLICABLE. -->
Benchmark applicability: REQUIRED | SMOKE_ONLY | NOT_APPLICABLE
<!-- REQUIRED must name exactly one numeric Test Card issue, for example: Benchmark issue: #123 -->
Benchmark issue: #
Benchmark rationale:

## Risks, regressions, and limitations

### Known regressions
<!-- “None observed” requires evidence from the relevant gates. -->
-

### Risks and rollback
<!-- State migration/rebuild impact, rollback trigger, and exact revert path. -->
-

### Known limitations
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

### What failed or changed the approach
-

## Public-surface / architecture invariants
- [ ] Public docs, examples, fixtures, benchmark data, and runtime configuration remain project-agnostic.
- [ ] Source files remain authoritative; indexes and artifacts remain derived and rebuildable.
- [ ] TESSERA returns structured evidence without replacing consuming-agent cognition.
- [ ] Exactly three semantic drawers remain: `facts`, `preferences`, `insights`.
- [ ] New concepts remain facets/metadata unless a separate Test Card changes that contract.
- [ ] No mandatory generative LLM was introduced in the basic path.
- [ ] Retrieval relevance remains distinct from confidence, authority, temporal validity, relation confidence, and utility.
- [ ] User source files are never silently mutated.
- [ ] Current and target/experimental capabilities are not presented as the same state.

## Post-merge lifecycle sync
<!--
After merge, replace candidate/head evidence with the canonical merge commit and
reconcile the Issue decision, ROADMAP, dependencies, and stage record. If this
cannot happen in this PR, open and link one minimal lifecycle-sync PR.
-->

- [ ] Canonical merge commit recorded after merge
- [ ] Issue state and Decision reconciled
- [ ] Roadmap status and dependencies reconciled
- [ ] Plain-language record moved from IN_PROGRESS to final state only after merge
- [ ] Closed-unmerged/superseded operational PRs preserved in the audit

## Follow-ups
<!-- Unrelated work becomes a separate Issue/Test Card. -->
- [ ] None

## Merge gate
- [ ] Issue/Test Card linked
- [ ] Purpose and before/after behavior are explicit
- [ ] In-scope and out-of-scope boundaries are explicit
- [ ] PR category and contract surfaces declared
- [ ] Changelog updated or explicitly N/A with rationale
- [ ] Tests green
- [ ] Relevant contract, smoke, sanity, and benchmark gates green or explicitly waived with rationale
- [ ] Evidence and Learnings updated in the Issue/Test Card
- [ ] Plain-language stage record created/updated or explicitly NOT_APPLICABLE
- [ ] Regressions, risks, rollback, and limitations recorded
- [ ] Final decision recorded
- [ ] Repository evolution verified against canonical commits and changed files
- [ ] Post-merge lifecycle path declared
