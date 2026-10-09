# 194 — Deterministic CI and review objections

| Field | Value |
|---|---|
| Issue | [#194](https://github.com/LuigiFerronatto/TESSERA/issues/194), operational tracker only; not closed by this PR |
| Record status | `IN_PROGRESS` |
| Capability type | `governance` |
| Pull request | Implementation draft; link recorded in PR metadata |
| Head commit | Exact candidate recorded in the implementation PR |
| Merge commit | Not merged |
| Decision | `PENDING` exact-head CI and canonical adoption |
| Benchmark applicability | `NOT_APPLICABLE` — governance only; no runtime/retrieval change |
| Last audited | 2026-10-04 |

## In one sentence

Replace automatic AI PR review with deterministic readiness without mandatory positive approval.

## What problem existed?

The 2026-10-02 Detection Runs investigation found that the pinned runtime could
not resolve its `detection` and `evals` aliases. The owner then requested removal
of AI evaluators from CI. This was a tooling failure, not a security finding.

## How did TESSERA behave before?

PR events invoked an AI reviewer and required its exact-head KEEP comment and
`TESSERA Maintainer Audit` status. Provider/catalog failures could prevent review
or produce misleadingly green outer jobs with failing model execution inside.

## What changed or is being tested?

Hypothesis: removing the automatic reviewer can eliminate provider-dependent CI
review while retaining deterministic tests, builds, applicable benchmarks and
review-objection safeguards. On 2026-10-04 the owner also authorized removal
of the mandatory positive human-approval requirement.
Issue Triage, opt-in Fixer, Lifecycle and Documentation Drift remain available,
including their existing security controls on agent write outputs.

## How does it work now?

TARGET — NOT YET ON MAIN. The governor requires successful exact-name CI checks,
offline reporting, dev-50 success when the PR declares REQUIRED applicability,
no active requested changes, no unresolved threads, non-draft status and no
conflicts. Positive human approval is optional. All review pages are checked
for trusted non-author human objections even if the aggregate decision is empty.
Missing/ambiguous applicability or incomplete thread evidence fails closed.
Old AI comments and provider state do not influence readiness.
PR body edits refresh benchmark/governor evaluation. A terminal native benchmark
check binds same-run reporting/dev-50 success to the parsed applicability, issue
and rationale, so old green checks on an unchanged commit cannot satisfy newly
changed metadata. Unrelated prose edits preserve the contract identity.

## Concrete example

A PR with all deterministic checks green and no review objections can pass
without any approving review or AI provider. One failing Python job, active
requested changes, unresolved thread, or required dev-50 run still pending blocks it even if an old
AI comment says KEEP.
A change from NOT_APPLICABLE to REQUIRED remains blocked until the new contract
has successful reporting and dev-50 evidence, even if older jobs were green.

## How was it validated?

Run `python -m pytest tests/test_governance_workflows.py tests/test_deterministic_governor.py tests/test_plain_language_test_card_docs.py tests/test_benchmark_reporting.py`.
These cover individual blocking conditions, exact names, review pagination,
absent approvals, active/superseded/dismissed objections, empty aggregate decisions,
benchmark applicability, same-head metadata edits,
pending/failed terminal evidence, ignored title edits, publication-time contract
races, same-run terminal shell gates and AI-workflow removal.
The Fixer lock was compiled twice with checksum-verified gh-aw v0.87.10 and
`--strict`; both outputs had identical bytes. Exact-head CI and full-suite counts
are recorded in the implementation PR rather than inferred from these checks.

## What improved?

Focused regressions establish that old AI comments cannot authorize or block
readiness and that deterministic evidence and absence of review blocks are required. The governor now
queries real review threads instead of assuming that none are unresolved.

## What remains unimplemented?

The candidate is not merged. Repository settings still require a separate
administrator migration to remove the retired AI required check and the mandatory
positive approval requirement while preserving the other protections. The PR
never changes settings, credentials, models, billing or merge authority.
Provider failures in separately scoped automation remain outside this change.

## What is unlocked next?

After authorized merge and settings migration, PRs without active review blocks can progress
through deterministic CI without automatic AI review. No downstream product
capability or roadmap dependency is promoted by this governance change.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Detection Runs #194](https://github.com/LuigiFerronatto/TESSERA/issues/194); owner-requested CI policy change |
| Pull request | Implementation draft for this record |
| Merge commit | Not merged; base `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Evidence/Learnings/Decision | Run `36966868340`; model alias failure; `PENDING` candidate validation |
| Benchmark record | NOT_APPLICABLE for this change; offline reporting retained |
| PR Evolution Audit | Original Stage A merged as `c349bac48c5fb1427f15615fc26e4fbc748ed320`; this candidate supersedes automatic PR AI review and mandatory positive approval |

## Evolution

AI review plus deterministic checks → owner-requested retirement of AI PR review
→ owner-authorized removal of mandatory positive approval
→ deterministic policy with review objections retained → merge and settings migration pending.

See [current governance](../AGENTIC_GOVERNANCE.md). Historical audit evidence in
other Test Cards remains valid history and is not rewritten.
