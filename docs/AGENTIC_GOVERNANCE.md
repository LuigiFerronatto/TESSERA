# TESSERA repository governance

## Current CI policy

Pull-request CI uses deterministic tests, builds, smoke checks and the offline
Benchmark Ledger. Automatic AI Maintainer Audit review has been retired, including
its generated detection and model-evaluation jobs. No AI comment, KEEP label,
provider quota, model alias or engine-failure override is a merge prerequisite.
Positive human approval is not required. Active review objections still block
readiness. Nothing in this repository automatically merges PRs.

The deterministic Merge Governor verifies the current PR head, non-draft status,
conflict-free mergeability, each named CI job, the offline benchmark check,
no requested changes, and no unresolved review threads. REQUIRED
benchmark applicability also requires `longmemeval-v1-dev-50` success; missing or
malformed applicability is blocking. The governor checks both GitHub aggregate
requested changes and active objections from trusted, non-author human reviewers
across every review page. This works even when GitHub returns an empty aggregate
decision because required approvals are disabled. A later approval or dismissal
clears that reviewer's objection; a comment or new head alone does not. Empty
review history is valid; missing review evidence fails closed. Missing,
pending, skipped or failed check evidence does not count as success. GraphQL thread
pagination is complete or the gather step fails; missing data never means zero
unresolved threads.

Benchmark readiness also requires a successful native `benchmark-contract (...)`
check whose digest covers the parsed applicability, issue and rationale. The
terminal job certifies that the offline check and any REQUIRED dev-50 job passed
in the same workflow run. Check evidence is already bound to the candidate SHA;
the digest prevents older green jobs on that SHA from satisfying changed metadata
before replacement jobs appear. Evidence for unchanged metadata remains reusable,
including after unrelated prose edits. No artifacts or extra token permissions
are needed, and the terminal check is enforced by the existing governor rather
than added as a variable-name branch-protection requirement.

The governor and Benchmark Ledger react to PR body edits; title-only edits are
ignored without replacing the authoritative check names or cancelling active
evaluations. The governor also runs on PR/review changes and completion of TESSERA
CI or the Benchmark Ledger. A completed workflow for a superseded head cannot
publish readiness for a new head. The publish step rechecks the head and parsed
benchmark contract immediately before writing its result.
A workflow completion without an associated PR is ignored; `workflow_dispatch`
with `pr_number` remains available for thread-only updates or manual reevaluation.

## Branch-protection migration

Workflow changes do not edit GitHub repository settings. At investigation time,
`main` required the obsolete `TESSERA Maintainer Audit` check as well as the eight
checks below. An authorized administrator must remove **only** that AI check from
required checks for the new policy to take effect without a permanently pending
requirement. The owner additionally authorized removal of mandatory positive
human approval on 2026-10-04. Retain the deterministic governor, strict
up-to-date requirement and conversation-resolution protection.

```text
distribution (Python 3.9)
distribution (Python 3.12)
test (Python 3.9)
test (Python 3.12)
smoke
sanity-eval
benchmark-reporting (offline)
tessera-merge-governor
```

Remove the mandatory approving-review requirement separately in repository
settings; retain resolved conversations and every required check listed above.
Active requested changes remain a governor blocker. GitHub branch protection
is the final authority. This PR does not claim settings were changed or
authorize merging itself.

Existing heads whose successful benchmark runs predate contract checks need a
fresh Benchmark Ledger evaluation before the new governor can authorize them.
The completion-triggered refresh becomes active once this workflow reaches the
default branch; it does not retroactively reevaluate already completed runs.

## Retained, separately scoped automation

| Workflow | Trigger and scope | Mutation boundary |
|---|---|---|
| Issue Triage | Issue opened/reopened; comment and labels | No code changes, issue closure or merge |
| PR Fixer | Explicit `ai-fix-approved` label; named human-review findings | Existing PR branch only; no approval or merge |
| Post-merge Lifecycle | Canonical merge; reconcile factual documentation | Draft documentation/governance PR only |
| Documentation Drift | Weekly/manual audit of canonical documentation | One consolidated report issue |

These workflows are not automatic AI PR review gates. Their existing output
sanitization, threat detection, permissions, opt-in restrictions and evaluation
configuration remain intact. Retiring the PR reviewer does not disable security
checks on other agents' write outputs, expand model/secret permissions, alter
scheduled documentation work or reconfigure provider billing.

The opt-in fixer now requires findings explicitly selected by a human maintainer.
Missing or ambiguous findings result in a report without a fix commit. An old AI
audit comment alone cannot authorize new work. Every pushed fix still requires
deterministic CI and resolution of active review blocks; positive approval is
optional. The fixer still cannot approve or merge its own changes.

## Maintenance and validation

The four remaining AI workflows are Markdown sources compiled into `.lock.yml`
with their pinned gh-aw version. Edit the source and recompile; do not hand-edit
generated locks. The removed reviewer has no source or generated workflow to
recompile. The governor is plain deterministic YAML and Python.

The generated `agentics-maintenance.yml` retains its existing narrow daily cleanup
of already-expired automation outputs. Administrative operations still require an
explicit operation input. No cleanup settings change is part of this transition.

Run `python -m pytest tests/test_governance_workflows.py` for static workflow
boundaries and `python -m pytest tests/test_deterministic_governor.py` for gate,
check-name, review-objection, pagination and CLI regressions. Full deterministic CI and
Benchmark Ledger must run on the published candidate head.

## Evidence and history

The 2026-10-02 investigation of [Detection Runs #194](https://github.com/LuigiFerronatto/TESSERA/issues/194)
found an engine tooling failure, not a detected security threat: the pinned
runtime could not resolve the `detection` and `evals` aliases from its live model
catalog. The repository owner then chose to remove automatic AI CI review rather
than continue pursuing provider/model workarounds. #194 is an automatically
managed tracker and is not closed by this change.

[Documentation Drift #281](https://github.com/LuigiFerronatto/TESSERA/issues/281)
recorded a separate historical HTTP 429. Its authorized retry failed before model
execution because the old activation artifact had expired; no further AI retry
was made after the CI policy change. This does not establish a current quota
failure or claim that the drift audit completed.

The [historical Stage A record](https://github.com/LuigiFerronatto/TESSERA/blob/20814a47ec0f72d7bea0639e0b057df1ecf5cded/docs/AGENTIC_GOVERNANCE.md) preserves
past architecture, engine incidents and delivery evidence. Its AI-review policy
is superseded by this document; historical PR/Test Card audit evidence remains
valid history and is not rewritten.
