# 194 — Deterministic CI and human review

| Field | Value |
|---|---|
| Issue | [#194](https://github.com/LuigiFerronatto/TESSERA/issues/194), operational tracker only; not closed by this PR |
| Record status | `IN_PROGRESS` |
| Capability type | `governance` |
| Pull request | Implementation draft; link recorded in PR metadata |
| Head commit | Exact candidate recorded in the implementation PR |
| Merge commit | Not merged |
| Decision | `PENDING` human review and exact-head CI |
| Benchmark applicability | `NOT_APPLICABLE` — governance only; no runtime/retrieval change |
| Last audited | 2026-10-02 |

## In one sentence

Replace automatic AI PR review with deterministic readiness and required human review.

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
human safeguards. The candidate retires only the PR reviewer and its gate.
Issue Triage, opt-in Fixer, Lifecycle and Documentation Drift remain available,
including their existing security controls on agent write outputs.

## How does it work now?

TARGET — NOT YET ON MAIN. The governor requires successful exact-name CI checks,
offline reporting, dev-50 success when the PR declares REQUIRED applicability,
GitHub aggregate approval plus a trusted non-bot human approval on the current
head, no review blocks, no unresolved threads, non-draft status and no conflicts.
Missing/ambiguous applicability or incomplete thread evidence fails closed.
Old AI comments and provider state do not influence readiness.

## Concrete example

A PR with all deterministic checks green and a current human approval can pass
without an AI provider. One failing Python job, bot-only approval, stale approval,
unresolved thread, or required dev-50 run still pending blocks it even if an old
AI comment says KEEP.

## How was it validated?

Run `python -m pytest tests/test_governance_workflows.py tests/test_deterministic_governor.py tests/test_plain_language_test_card_docs.py`.
These cover individual blocking conditions, exact names, review pagination,
bot/stale/dismissed approvals, benchmark applicability and AI-workflow removal.
The Fixer lock was compiled twice with checksum-verified gh-aw v0.87.10 and
`--strict`; both outputs had identical bytes. Exact-head CI and full-suite counts
are recorded in the implementation PR rather than inferred from these checks.

## What improved?

Focused regressions establish that old AI comments cannot authorize or block
readiness and that human/deterministic evidence is required. The governor now
queries real review threads instead of assuming that none are unresolved.

## What remains unimplemented?

The candidate is not merged. Repository settings still require a separate
administrator migration to remove only the retired AI required check. The PR
never changes settings, credentials, models, billing or merge authority.
Provider failures in separately scoped automation remain outside this change.

## What is unlocked next?

After authorized merge and settings migration, human-reviewed PRs can progress
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
| PR Evolution Audit | Original Stage A merged as `c349bac48c5fb1427f15615fc26e4fbc748ed320`; this candidate supersedes only automatic PR AI review |

## Evolution

AI review plus deterministic checks → owner-requested retirement of AI PR review
→ candidate deterministic/human-only policy → merge and settings migration pending.

See [current governance](../AGENTIC_GOVERNANCE.md). Historical audit evidence in
other Test Cards remains valid history and is not rewritten.
