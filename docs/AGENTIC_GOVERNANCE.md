# TESSERA Agentic Repository Governance

This document describes the automated governance loop that triages issues,
independently audits pull requests, reconciles lifecycle documentation after
a canonical merge, and periodically audits documentation truthfulness — all
without letting any single AI agent implement, review, and merge its own
change.

It is **repository-process automation**. It is not a TESSERA memory/runtime
feature, is never described as one, and grants no AI agent write-all access
or direct-to-`main` push capability.

## Why this exists

Before this system, a maintainer manually performed:

```text
issue triage
→ implementation review
→ merge-readiness judgment
→ post-merge lifecycle reconciliation (ROADMAP/Test Card/PR Evolution/CHANGELOG)
→ documentation-truth audits
```

This automation reduces that manual burden while preserving independent
judgment at each step and keeping deterministic authorization separate from
AI semantic judgment.

## Separation of duties

```text
TRIAGER != IMPLEMENTER != REVIEWER != MERGE AUTHORITY != LIFECYCLE RECONCILER
```

| Role | Workflow | Can implement code? | Can approve/merge? |
|---|---|---|---|
| Triager | `tessera-issue-triage.md` | No | No |
| Implementer | (a human or an existing coding-agent flow; out of scope here) | Yes | No |
| Reviewer | `tessera-pr-maintainer-audit.md` | No | No (records KEEP/ITERATE/BLOCK only) |
| Fixer (opt-in) | `tessera-pr-fixer.md` | Yes, only for named findings | No |
| Merge authority | `tessera-merge-governor.yml` (deterministic) | No | Report-only in Stage A; see rollout |
| Lifecycle reconciler | `tessera-post-merge-lifecycle.md` | No (docs/governance-tests only) | No |
| Drift auditor | `tessera-documentation-drift.md` | No | No |

No single AI agent both implements and reviews/approves/merges the same
change. The maintainer-audit reviewer cannot push to the branch it reviews;
the opt-in fixer cannot approve or merge its own fix; the lifecycle
reconciler cannot push to `main`.

## The governance loop

```text
issue opened/reopened
  → tessera-issue-triage.md (Gemini): comment + <=4 labels, read-only

pull request opened/synchronize/ready_for_review
  → TESSERA CI + Benchmark Ledger (deterministic, unchanged)
  → tessera-pr-maintainer-audit.md (Codex): KEEP | ITERATE | BLOCK bound to exact head SHA

ITERATE
  → maintainer applies `ai-fix-approved` label (opt-in, never automatic)
  → tessera-pr-fixer.md (Copilot): pushes a fix commit to the same PR branch
  → new head → tessera-pr-maintainer-audit.md re-runs automatically

KEEP + exact head unchanged + CI/Benchmark green + no unresolved threads
  → tessera-merge-governor.yml (deterministic GitHub Actions, no AI):
    publishes a `tessera-merge-governor` check run a maintainer can require
    for branch protection; never calls the merge API in Stage A

human merges (branch protection enforced) → canonical merge on main
  → tessera-post-merge-lifecycle.md (Codex): reconciles ROADMAP / Test Card /
    PR Evolution / dependent-issue routing / CHANGELOG (per Change Policy);
    opens one minimal draft lifecycle PR only when actual drift is found

weekly (and workflow_dispatch)
  → tessera-documentation-drift.md (Gemini): one consolidated `[docs-drift]`
    issue when canonical main and repository documentation disagree
```

## Anti-stale-head mechanism

`tessera-pr-maintainer-audit.md` records its decision as:

```markdown
## Maintainer audit — KEEP | ITERATE | BLOCK

Audited head: `<exact sha>`
```

`governance/merge_governor.py` (invoked by `tessera-merge-governor.yml`)
parses the most recent such comment and requires:

```text
decision == KEEP
audited_head_sha == current PR head SHA
```

Any new commit changes the head SHA and invalidates the previous KEEP until
a fresh audit runs against the new head — this is enforced by the
`synchronize` trigger on the maintainer-audit workflow and by the equality
check in `evaluate_runtime_pr_gates`. A mutable `audit/keep` label is never
treated as sufficient authorization by itself; it is a visual aid only. See
`tests/test_governance_workflows.py::test_merge_governor_binds_decision_to_current_head`
for the frozen behavior (a stale-SHA KEEP is proven not to authorize a newer
head).

## Engine assignment (initial hypothesis, not a benchmark claim)

```text
Gemini  → issue triage and weekly documentation-drift reconnaissance (broad read)
Codex   → independent semantic PR audit and post-merge lifecycle reconciliation
          (deep contract reasoning, shell disabled for the reviewer)
Copilot → explicitly opt-in code fixing where branch mutation is authorized
GitHub Actions (deterministic) → merge authorization only
```

This assignment is an initial engineering hypothesis based on each engine's
documented strengths (Codex/Claude have native deep contract reasoning;
Gemini supports broad low-cost reconnaissance; Copilot has the broadest
engine-specific feature set for controlled code mutation). It is **not**
evidence that one model is objectively superior at each role. A future Test
Card should measure this directly by running, for a sample of PRs:

```text
R0: Codex reviewer only (current)
R1: Gemini reviewer only
R2: Codex + Gemini independent reviewers
```

and comparing: valid blocking findings, false-positive rate, unique valid
findings per model, defects caught before merge, human override rate,
latency, and cost. Dual mandatory reviewers are explicitly **not** enabled
in this initial delivery.

## Safe outputs and least privilege

Every AI workflow runs with read-only `permissions:` (`contents: read`,
`issues: read`, `pull-requests: read`). All repository mutation happens
through gh-aw `safe-outputs:`, executed by a separate, narrowly-permissioned
job — never by the agent directly:

| Workflow | Safe outputs allowed | Explicitly forbidden |
|---|---|---|
| `tessera-issue-triage.md` | `add-comment` (max 1), `add-labels` (max 4) | issue close/delete, code changes, PR creation/merge |
| `tessera-pr-maintainer-audit.md` | `add-comment`, `add-labels`, `create-pull-request-review-comment`, `submit-pull-request-review` | `push-to-pull-request-branch`, `create-pull-request`, `merge-pull-request`, direct file edits |
| `tessera-pr-fixer.md` | `push-to-pull-request-branch` (to the existing PR branch only), `add-comment` | merge, approve/submit-review, push to `main`, create new PRs |
| `tessera-post-merge-lifecycle.md` | `create-pull-request` (**draft: true**), `add-comment` | push to `main`, `push-to-pull-request-branch` |
| `tessera-documentation-drift.md` | `create-issue` (max 1, `close-older-issues`) | PR creation, file edits |
| `tessera-merge-governor.yml` | (not a safe-output workflow; plain `checks: write`) | any merge/auto-merge API call in Stage A |

No workflow requests `write-all`. `tessera-pr-maintainer-audit.md` disables
`tools.bash` entirely (`bash: false`, `cli-proxy: false`) so the reviewer can
only read repository state through the GitHub MCP toolset, never execute
arbitrary shell. `tessera-pr-fixer.md` uses a narrow bash allowlist (pytest,
build, editable install, read-only git inspection) rather than unrestricted
shell.

Untrusted input (issue bodies, PR descriptions, comments) is treated as
untrusted throughout: prompts instruct agents to ground every claim in
repository evidence they actually inspected, and gh-aw's own safe-output
sanitization applies to all generated content.

## Authentication and required secrets/configuration

No secrets are committed by this change. A maintainer must configure:

- **Gemini** (`tessera-issue-triage.md`, `tessera-documentation-drift.md`):
  `GEMINI_API_KEY` repository/organization secret, or Google Workload
  Identity Federation if the installed gh-aw version's Gemini engine
  supports it in this environment.
- **Codex** (`tessera-pr-maintainer-audit.md`, `tessera-post-merge-lifecycle.md`):
  `CODEX_API_KEY`/`OPENAI_API_KEY` per the installed gh-aw Codex engine
  configuration. Verify against the currently installed gh-aw version's
  documented Codex auth options before enabling; do not assume a specific
  Copilot-billed Codex model alias without confirming it is supported.
- **Copilot** (`tessera-pr-fixer.md`): prefer organization-billed Copilot
  requests (`copilot-requests: write`) if your GitHub plan/organization
  supports it; otherwise configure the documented Copilot CLI authentication
  for gh-aw.

Compile-time secret detection (`gh aw compile`) will flag any new secret
requirement the first time a workflow using it is compiled; each one listed
above was reviewed during this delivery and is a standard, documented
credential for its engine — not a newly invented one.

## Labels

Deterministically created in this PR (not invented at runtime by any agent):
`type/research`, `type/benchmark`, `type/architecture`, `type/tracker`,
`priority/p0`..`p3`, `status/needs-info`, `status/blocked`,
`status/deferred`, `status/ready`, `phase/m0-contract-safety` .. 
`phase/m5-admission-learning` (matching `docs/ROADMAP.md`'s actual M0–M5
phases), `audit/keep`, `audit/iterate`, `audit/block`, `automation`,
`governance`, `triage`, `review`, `lifecycle`, `ai-fix-approved`. Existing
labels (`bug`, `enhancement`, `documentation`, `duplicate`, etc.) are reused
where they already cover a category.

`tessera-issue-triage.md` is instructed to apply at most one type, one
priority, one phase, and one exceptional status label per run, and to
prefer omitting a label over guessing.

## Rollout stages

**Stage A (this delivery — enabled by default):**

```text
Issue triage       → comment + labels only
PR reviewer        → comment/review only, no code mutation
Fixer              → disabled by default; opt-in only via ai-fix-approved label
Lifecycle          → creates DRAFT lifecycle PRs only
Merge governor     → report-only: publishes a check run, never calls merge/auto-merge APIs
Documentation drift → one consolidated issue only, no PRs
```

**Stage B (future, requires a Test Card/decision before enabling):**

```text
Lifecycle/documentation PRs may auto-merge once: allowed-paths-only + CI
green + Benchmark Ledger green/appropriate + mergeable + no review blocks.
See governance.merge_governor.evaluate_lifecycle_pr_gates, which already
implements and freezes this gate logic even though nothing calls it yet.
```

**Stage C (future):**

```text
Optional fixer expansion beyond the current narrow bash allowlist.
```

**Stage D (future, only after measured trust):**

```text
Runtime PR auto-merge, gated on tessera-merge-governor's check run being a
required branch-protection status check plus sustained human-override data
from Stage A/B.
```

## How a maintainer overrides a bad AI decision

- **Bad triage** — edit labels/comment manually; the triage workflow does
  not re-run unless the issue is reopened.
- **Bad KEEP/ITERATE/BLOCK** — comment or push a new commit; a new commit
  automatically invalidates the prior audit (new head SHA) and re-triggers
  `tessera-pr-maintainer-audit.md`. A maintainer can also simply disregard
  the audit comment and merge through normal repository permissions — this
  automation does not remove human merge ability, it only offers an
  additional optional required check.
- **Unwanted fixer run** — do not apply `ai-fix-approved`; if already
  applied, the label is auto-removed after one run (one-shot), so no
  additional action is needed to stop it recurring.
- **Bad lifecycle PR** — it is a draft PR; close it without merging, or
  request changes before marking it ready for review.
- **False documentation-drift report** — close the `[docs-drift]` issue;
  `close-older-issues` ensures only the latest report stays open.
- **Disable any workflow entirely** — `gh aw disable <workflow-id>`, or
  remove/comment out its trigger and recompile.

## Manual triggers

- `tessera-issue-triage.md` — `workflow_dispatch`, or re-trigger by
  reopening the issue.
- `tessera-pr-maintainer-audit.md` — push an empty/no-op commit to the PR
  branch, or re-run the workflow from the Actions tab.
- `tessera-pr-fixer.md` — apply the `ai-fix-approved` label to the PR.
- `tessera-post-merge-lifecycle.md` — `workflow_dispatch`.
- `tessera-documentation-drift.md` — `workflow_dispatch`.
- `tessera-merge-governor.yml` — `workflow_dispatch` with a `pr_number` input.

## Compilation

All five AI workflows are gh-aw Markdown sources compiled with the installed
`gh aw compile` (v0.87.10 at the time of this delivery) into committed
`.lock.yml` files. Do not hand-edit a `.lock.yml` file; edit the `.md`
source and recompile. `tests/test_governance_workflows.py` freezes that the
committed lock files are exactly what recompiling the source currently
produces (module the compiler's own content hash and any third-party action
SHA bumps).

`tessera-merge-governor.yml` is a plain, deterministic GitHub Actions
workflow (no `engine:`), reviewed like any other CI change.

## Known limitations

- The merge governor's unresolved-review-thread check is currently a
  conservative placeholder (`has_unresolved_threads: False` from the
  workflow, i.e. it does not yet block on unresolved threads) because
  `gh pr view --json` does not expose `reviewThreads(isResolved: false)`;
  wiring the exact GraphQL query is called out explicitly in the workflow
  and should be completed before treating its check run as a sole required
  gate.
- The merge governor publishes a check run but does not (yet) enforce it via
  branch protection; a maintainer must add `tessera-merge-governor` to the
  repository's required status checks to make it binding.
- None of these workflows have executed against live GitHub Actions yet in
  this delivery (no engine secrets are configured); compilation, static
  governance tests, and repository test suite are the available
  pre-merge evidence.
