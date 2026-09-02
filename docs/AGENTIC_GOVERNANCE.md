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

## Personas (content-level, not a separate GitHub identity)

Every workflow renders a distinct visual persona at the start of its
comment/report body, so a maintainer can tell at a glance which governance
role produced a given comment without reading the workflow name:

| Persona | Workflow | Role |
|---|---|---|
| 🧭 TESSERA Router | `tessera-issue-triage.md` | Issue triage |
| 🛡️ TESSERA Guardian | `tessera-pr-maintainer-audit.md` | Maintainer audit (KEEP/ITERATE/BLOCK) |
| 🔧 TESSERA Fixer | `tessera-pr-fixer.md` | Opt-in fix commits |
| 🔄 TESSERA Steward | `tessera-post-merge-lifecycle.md` | Post-merge lifecycle reconciliation |
| 🔎 TESSERA Sentinel | `tessera-documentation-drift.md` | Periodic documentation drift |

This is a **content-level** persona only: the real GitHub comment/review
author remains `github-actions[bot]` (or whichever token the workflow uses),
because gh-aw safe outputs are always written by the workflow's own GitHub
token. Giving each agent a truly distinct bot account/avatar
(`tessera-guardian[bot]`, etc.) would require registering and installing a
dedicated GitHub App per persona — legitimate, but deliberately deferred
past Stage A as unnecessary infrastructure for the current trust level.

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
  → tessera-merge-governor.yml (deterministic GitHub Actions, no AI), triggered
    by `pull_request` and `pull_request_review` events (so it re-evaluates the
    moment the audit submits its review, not on a fixed delay):
    publishes two independently-requirable check runs bound to the exact
    current head SHA — `TESSERA Maintainer Audit` (mirrors the latest
    KEEP/ITERATE/BLOCK decision, `failure` if stale) and
    `tessera-merge-governor` (the aggregate authorization gate). Never calls
    the merge API in Stage A.

human merges (branch protection enforced) → canonical merge on main
  → tessera-post-merge-lifecycle.md (Codex): reconciles ROADMAP / Test Card /
    PR Evolution / dependent-issue routing / CHANGELOG (per Change Policy);
    opens one minimal draft lifecycle PR only when actual drift is found

weekly (and workflow_dispatch)
  → tessera-documentation-drift.md (Gemini): one consolidated `[docs-drift]`
    issue when canonical main and repository documentation disagree
```

## Branch protection: GitHub is the authority, not convention

`main` is protected (`repos/.../branches/main/protection`) and requires, on
every pull request, **all** of the following to be green on the exact
current head before the Merge button unlocks — enforced by GitHub itself,
not by a maintainer remembering a checklist:

```text
Required status checks (strict: branch must be up to date)
  distribution (Python 3.9)
  distribution (Python 3.12)
  test (Python 3.9)
  test (Python 3.12)
  smoke
  sanity-eval
  benchmark-reporting (offline)
  TESSERA Maintainer Audit
  tessera-merge-governor

Required reviews
  >= 1 approving review (dismissed automatically on a new push)
  required_conversation_resolution: true (zero unresolved review threads)
```

Each required check is enforced individually (defense in depth) *and* the
aggregate `tessera-merge-governor` check is required on top — a bug in the
aggregator alone cannot silently authorize a merge that a individual
required check would have blocked, and vice versa. `strict: true` means any
new commit resets every required check to pending for the new SHA, which is
what actually enforces the anti-stale-head invariant at the GitHub UI level
(a green check bound to an old SHA can never satisfy a required check for
the new SHA). `enforce_admins` is intentionally left `false` in Stage A so a
maintainer can still override in a genuine emergency; tightening this is a
candidate for a later stage once the system has a track record.

## Why pre-merge gates stay as separate workflows, not one mega-workflow

CI (`tessera-ci.yml`) and Benchmark Ledger (`benchmark.yml`) are pre-existing
workflows independent of this governance rollout; `tessera-pr-maintainer-audit.md`
is a gh-aw-compiled agentic workflow. GitHub Actions `needs:` can only
express dependencies between jobs **inside the same workflow run** — it
cannot gate a job in one workflow file on a job defined in a different
workflow file. Making all four literally one workflow would require either
(a) converting `tessera-ci.yml`/`benchmark.yml` into `workflow_call`-based
reusable workflows invoked as jobs from a new orchestrator, or (b) rewriting
their logic inline — both are bigger, riskier changes to already-established
CI infrastructure than this rollout's scope, and are tracked as a candidate
follow-up rather than done speculatively here.

What is already achieved without that rewrite: `tessera-merge-governor.yml`
re-evaluates automatically the instant the audit submits its review (via the
`pull_request_review` trigger, not polling), publishes both a `TESSERA
Maintainer Audit` check and the aggregate `tessera-merge-governor` check
bound to the exact head, and branch protection requires every individual
gate plus the aggregate. The net effect at the PR UI is the same ordering
the user asked for (`CI + Benchmark → Audit → Governor`) and the same
all-green-or-blocked outcome, without needing job-level `needs:` across
independently-versioned workflow files.

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
Runtime PR auto-merge, now that tessera-merge-governor and TESSERA
Maintainer Audit are both required branch-protection status checks (see
"Branch protection" above), gated on sustained human-override data from
Stage A/B before auto-merge itself is enabled.
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

## Generated maintenance workflow (`.github/workflows/agentics-maintenance.yml`)

gh-aw automatically generates and maintains this file — do not hand-edit it,
edit `.github/workflows/aw.json` (`{"maintenance": false}` disables
generation entirely) and recompile instead. It exists because
`tessera-documentation-drift.md` declares `close-older-issues: true`
(an expiring safe output): gh-aw needs a companion scheduled job to actually
close superseded `[docs-drift]` issues once a newer one is created.

**Default (daily `schedule`, no `operation` input) behavior** — the only
path that runs without a human explicitly choosing an operation — is
narrowly scoped to closing gh-aw's own already-expired
issues/discussions/PRs and pruning stale cache-memory entries
(`close-expired-issues`, `close-expired-discussions`,
`close-expired-pull-requests`, `cleanup-cache-memory`). Every job requires
`!github.event.repository.fork` and none of them touch content this
governance system did not itself create/label.

**Every other operation** (`disable`, `enable`, `update`, `upgrade`,
`safe_outputs` replay, `create_labels`, `activity_report`,
`close_agentic_workflows_issues`, `clean_cache_memories`,
`update_pull_request_branches`, `validate`, `forecast`) is gated behind
`workflow_dispatch`/`workflow_call` **and** an explicit non-default
`inputs.operation` selection — none of them ever run on the daily schedule.
A maintainer must deliberately pick that operation from the Actions tab (or
an explicit `workflow_call`); this is the same "explicit human action
required" pattern as `tessera-pr-fixer`'s `ai-fix-approved` label.
`tests/test_governance_workflows.py::test_generated_maintenance_workflow_write_operations_require_explicit_operation_input`
freezes this: every job outside the four default-cleanup jobs above must
require a non-empty, non-`"none"` `inputs.operation` to run.

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
- Because the check is not (yet) required, GitHub's `mergeStateStatus` can
  read `UNSTABLE` purely because the governor's own check is red, even once
  every gate the governor itself checks (CI, benchmark, audit `KEEP` on the
  exact head, no requested changes) is green — a self-referential loop that
  only resolves once `mergeable_state == clean` on a later governor re-run.
  This is cosmetic while the check is non-required: a human can still merge
  regardless of it. Making `tessera-merge-governor` a required check (Stage
  B+) needs this loop resolved first, e.g. by excluding the governor's own
  check from whatever `mergeable_state` computation gates it, or by having
  branch protection require only the underlying CI/benchmark/audit signals
  and treating the governor check as informational.
- This PR itself exercised `tessera-pr-maintainer-audit` and
  `tessera-merge-governor` live (Codex engine, real GitHub Actions runs) and
  both worked as designed, including correctly BLOCKing two earlier heads.
  `tessera-issue-triage`, `tessera-pr-fixer`, and
  `tessera-post-merge-lifecycle` have not yet executed against a live event
  in this delivery; compilation and static governance tests are the
  available pre-merge evidence for those three.
