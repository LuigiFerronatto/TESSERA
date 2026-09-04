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
  → tessera-issue-triage.md (Copilot): comment + <=4 labels, read-only

pull request opened/synchronize/ready_for_review
  → TESSERA CI + Benchmark Ledger (deterministic, unchanged)
  → tessera-pr-maintainer-audit.md (Copilot): KEEP | ITERATE | BLOCK bound to exact head SHA

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
  → tessera-post-merge-lifecycle.md (Copilot): reconciles ROADMAP / Test Card /
    PR Evolution / dependent-issue routing / CHANGELOG (per Change Policy);
    opens one minimal draft lifecycle PR only when actual drift is found

weekly (and workflow_dispatch)
  → tessera-documentation-drift.md (Copilot): one consolidated `[docs-drift]`
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

## Engine-failure resilience: `ENGINE_UNAVAILABLE` and human override

An AI provider running out of credits/quota, timing out, or hitting an auth
failure is a distinct state from a completed audit that found a problem:

```text
BLOCK               "I analyzed this and found a problem."
ENGINE_UNAVAILABLE   "I could not analyze this at all."
```

These must never be conflated. If the maintainer-audit workflow simply
fails to produce a comment (for any reason, including engine failure), the
absence of a parseable `AuditRecord` **fails closed** by default: no audit
comment means no authorization, full stop. `is_engine_unavailable()`
classifies the maintainer-audit workflow's own GitHub Actions run
conclusion (`failure`, `timed_out`, `cancelled`, `action_required`) so the
calling workflow can render an honest, explicit `ENGINE_UNAVAILABLE` state
on the dedicated `TESSERA Maintainer Audit` check (via
`audit_check_status`) instead of leaving it ambiguously pending forever.

The **only** escape hatch is an explicit, head-bound human break-glass
override, posted as a PR comment by a genuine maintainer:

```markdown
## Maintainer override — KEEP

Audited head: `<exact sha>`
Reason: engine_unavailable (quota_exceeded)
```

Constraints enforced by `governance/merge_governor.py`:

- An override can only ever assert `KEEP`. There is no "override BLOCK" —
  a maintainer can always simply decline to merge through ordinary
  repository permissions, so no machine-readable override contract is
  needed for that direction.
- An override only becomes non-blocking when `audit is None` **and**
  `engine_unavailable` is true. It can never substitute for, or override,
  an actual completed `ITERATE`/`BLOCK` decision (see
  `test_override_never_substitutes_for_a_real_block_decision`).
- An override is bound to the exact current head SHA the same way an
  audit is: a stale override (bound to a superseded head) does not
  authorize a newer commit.
- The override only relaxes the *aggregate* `tessera-merge-governor`
  check. The dedicated `TESSERA Maintainer Audit` check is never faked to
  `success` by an override — it honestly reports `ENGINE_UNAVAILABLE`
  (`failure`) because the audit genuinely did not run. Branch protection
  still requires CI and Benchmark green in every case; the override only
  ever removes the semantic-audit blocker, never the deterministic ones.
- The caller (`tessera-merge-governor.yml`) must only pass override
  comments authored by a trusted human role (`OWNER`/`MEMBER`/
  `COLLABORATOR`, non-bot) into `find_latest_override` — a bot-authored or
  outside-contributor comment must never count, even if it matches the
  override heading verbatim.

### Per-workflow failure-mode policy

| Workflow | Failure mode | Behavior when the engine is unavailable |
| --- | --- | --- |
| `tessera-issue-triage.md` | best-effort | Issue stays untriaged; re-run manually or on reopen. No merge-authorization impact. |
| `tessera-pr-maintainer-audit.md` | **fail-closed** | No audit comment → no authorization. `ENGINE_UNAVAILABLE` on the dedicated check; only escape is a bound human override. |
| `tessera-pr-fixer.md` | fails, manual fix | PR is unchanged; a maintainer fixes it by hand or re-applies `ai-fix-approved`. |
| `tessera-post-merge-lifecycle.md` | retry/fallback (future) | Lifecycle PR is simply not opened yet; `workflow_dispatch` re-run recovers it. Cross-engine fallback is explicitly deferred to a future stage. |
| `tessera-documentation-drift.md` | best-effort | Next scheduled run recovers it; this is a periodic safety net, not a gate. |
| `tessera-merge-governor.yml` | deterministic, no AI engine | Not subject to engine failure; this is the workflow that *interprets* engine-unavailable state for the other agents. |

## Engine assignment (initial hypothesis, not a benchmark claim)

```text
Copilot → all five workflows: issue triage, independent semantic PR audit,
          opt-in code fixing (branch mutation authorized), post-merge
          lifecycle reconciliation, and weekly documentation-drift
          reconnaissance
GitHub Actions (deterministic) → merge authorization only
```

Every AI-driven TESSERA workflow now runs on `engine: {id: copilot}`. This
was not the original design — `tessera-pr-maintainer-audit.md` and
`tessera-post-merge-lifecycle.md` started on `engine: {id: codex}`, and
`tessera-issue-triage.md`/`tessera-documentation-drift.md` started on
`engine: {id: gemini}` — but every non-Copilot engine hit a live,
external, unfixable failure during this delivery:

- **Codex** (`tessera-pr-maintainer-audit.md`,
  `tessera-post-merge-lifecycle.md`): a live OpenAI account/billing
  failure on `CODEX_API_KEY`/`OPENAI_API_KEY` blocked the required
  Maintainer Audit check on PR #182 (`stream disconnected before
  completion: Your account is not active`). A prior attempt to route
  Codex inference through Copilot billing (`engine.model: copilot/auto`)
  also failed live with `model_not_supported`, despite being gh-aw's own
  documented pattern. Both switched to Copilot.
- **Gemini** (`tessera-issue-triage.md`, `tessera-documentation-drift.md`):
  the first live Issue Triage run (#195, triggered by issue #192) failed
  with `Invalid auth method selected` (exit code 41), even though
  `GEMINI_API_KEY` was correctly configured as a repository secret. Root
  cause is a confirmed upstream infrastructure bug in gh-aw's Agentic
  Workflow Firewall (AWF) sandbox: the firewall sets `GEMINI_API_BASE_URL`
  to its local API proxy, but at the pinned firewall version that proxy
  reported no Gemini protocol support at all (`API proxy enabled:
  OpenAI=false, Anthropic=false, Copilot=false` — no `Gemini=true`),
  so the Gemini CLI could never authenticate regardless of the secret's
  validity (tracked upstream as `github/gh-aw#25294` /
  `github/gh-aw-firewall#1806`/`#1931`/`#2009`; even the firewall's own
  partial fix left a follow-on `API_KEY_INVALID` failure from a key
  the proxy fails to substitute). This is external infrastructure, not a
  TESSERA workflow-configuration defect, and not something a workflow
  frontmatter change alone can fully work around. Both switched to
  Copilot for consistency and because Copilot has no external API-key
  dependency at all (`copilot-requests: write`, org-billed).

Standard Copilot engine (`copilot-requests: write`, no external API-key
dependency) avoids every failure mode above and is now the sole engine
assignment across all five roles.

This assignment is an initial engineering hypothesis based on Copilot's
documented feature set, native agent selection, and freedom from
external-provider billing/proxy dependencies. It is **not** evidence that
one model is objectively superior at each role. A future Test Card should
measure this directly by running, for a sample of PRs, independent
reviewers on multiple engines side by side once at least one non-Copilot
engine is confirmed stable in this environment, and comparing: valid
blocking findings, false-positive rate, unique valid findings per model,
defects caught before merge, human override rate, latency, and cost. Dual
mandatory reviewers are explicitly **not** enabled in this initial
delivery.

## Safe outputs and least privilege

Every AI workflow runs with read-only `permissions:` (`contents: read`,
`issues: read`, `pull-requests: read`). All repository mutation happens
through gh-aw `safe-outputs:`, executed by a separate, narrowly-permissioned
job — never by the agent directly:

| Workflow | Safe outputs allowed | Explicitly forbidden |
|---|---|---|
| `tessera-issue-triage.md` | `add-comment` (max 1), `add-labels` (max 4) | issue close/delete, code changes, PR creation/merge |
| `tessera-pr-maintainer-audit.md` | `add-comment`, `add-labels`, `create-pull-request-review-comment` | `push-to-pull-request-branch`, `create-pull-request`, `merge-pull-request`, `submit-pull-request-review`, direct file edits |
| `tessera-pr-fixer.md` | `push-to-pull-request-branch` (to the existing PR branch only), `add-comment` | merge, approve/submit-review, push to `main`, create new PRs |
| `tessera-post-merge-lifecycle.md` | `create-pull-request` (**draft: true**), `add-comment` | push to `main`, `push-to-pull-request-branch` |
| `tessera-documentation-drift.md` | `create-issue` (max 1, `close-older-issues`) | PR creation, file edits |
| `tessera-merge-governor.yml` | (not a safe-output workflow; plain `checks: write`) | any merge/auto-merge API call in Stage A |

`tessera-pr-maintainer-audit.md` deliberately never uses
`submit-pull-request-review`: GitHub's default `GITHUB_TOKEN` cannot submit
an "approve" review (a hard, non-configurable platform restriction that
prevents a workflow from self-approving its own pull request), so this
would permanently fail for every `KEEP` decision. The `## Maintainer audit
— KEEP | ITERATE | BLOCK` PR comment (parsed by `find_latest_audit`) is the
sole authoritative decision record; no formal GitHub review object is ever
required or relied upon by the merge governor.

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

No secrets are committed by this change. All five TESSERA workflows now run
on the standard Copilot engine:

- **Copilot** (`tessera-issue-triage.md`, `tessera-pr-maintainer-audit.md`,
  `tessera-pr-fixer.md`, `tessera-post-merge-lifecycle.md`,
  `tessera-documentation-drift.md`): prefer organization-billed Copilot
  requests (`copilot-requests: write`, granted to all five workflows) if
  your GitHub plan/organization supports it; otherwise configure a
  `COPILOT_GITHUB_TOKEN` secret (fine-grained PAT with Copilot Requests
  access) per gh-aw's documented Copilot CLI authentication.
- **Codex**: previously used by `tessera-pr-maintainer-audit.md` and
  `tessera-post-merge-lifecycle.md` (`CODEX_API_KEY`/`OPENAI_API_KEY`).
  Both were switched to the Copilot engine after two consecutive live
  failures on PR #182: routing Codex inference through Copilot billing
  (`engine.model: copilot/auto`) failed with `model_not_supported` at the
  pinned engine version (`0.150.1`), and reverting to direct OpenAI
  billing then failed with an inactive/unbilled OpenAI account error
  (`stream disconnected before completion: Your account is not active`).
  Neither is a code defect in this repository; both were external
  provider/billing failures. Codex is no longer used by any TESSERA
  workflow.
- **Gemini**: previously used by `tessera-issue-triage.md` and
  `tessera-documentation-drift.md` (`GEMINI_API_KEY`). Switched to Copilot
  after the first live Issue Triage run failed with `Invalid auth method
  selected` (exit code 41) due to a confirmed upstream gh-aw
  Agentic Workflow Firewall bug unrelated to the `GEMINI_API_KEY` secret's
  validity (see "Engine assignment" and `github/gh-aw#25294`). Gemini is
  no longer used by any TESSERA workflow.

Standard Copilot engine has no external API-key dependency at all, which is
now the primary reason it is the sole engine across every role — this is a
design decision, not merely a temporary workaround. See "Known limitations"
for the full failure history of both abandoned engines.

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
  `tessera-pr-maintainer-audit.md`. With branch protection enforcing
  `TESSERA Maintainer Audit` and `tessera-merge-governor` as required
  checks, the merge button is genuinely blocked until a fresh KEEP lands —
  a maintainer can no longer just disregard the audit comment. If the
  audit engine itself is unavailable (not merely a bad decision), see
  "Engine-failure resilience" above for the human break-glass override.
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
- Branch protection on `main` now requires `tessera-merge-governor` and
  `TESSERA Maintainer Audit` as individual status checks (in addition to
  CI/benchmark), with `strict: true` (anti-stale-head) and 1 required
  approval. The earlier self-referential `mergeStateStatus` loop (the
  governor's own aggregate merge state depended on its own required check)
  was fixed by gating on `mergeable` (raw git-conflict-only) instead — see
  "Engine-failure resilience" and the `mergeable_state` docstring in
  `governance/merge_governor.py`.
- `tessera-pr-maintainer-audit.md` and `tessera-post-merge-lifecycle.md`
  moved from `engine: {id: codex}` to `engine: {id: copilot}` after two
  consecutive live failures on PR #182, both external to this repository's
  code: (1) `engine.model: copilot/auto` (routing Codex inference through
  Copilot billing) failed with `model_not_supported` for the literal model
  name `auto` at the pinned Codex engine version (`0.150.1`), even though
  `copilot/auto` is gh-aw's own documented and unit-tested pattern for this
  exact use case (verified against `github/gh-aw`'s
  `pkg/workflow/codex_engine_test.go` and `pkg/workflow/data/model_aliases.json`
  upstream); (2) reverting to direct `CODEX_API_KEY`/`OPENAI_API_KEY` billing
  then failed with `stream disconnected before completion: Your account is
  not active, please check your billing details on our website` — an
  inactive/unbilled OpenAI account, unrelated to any workflow configuration.
  Standard Copilot engine (`copilot-requests: write`) has no external
  API-key dependency and avoids both failure modes; this fail-closed
  Maintainer Audit engine failure is exactly what the `ENGINE_UNAVAILABLE`
  break-glass override contract above exists to handle when it recurs.
- `tessera-issue-triage.md` and `tessera-documentation-drift.md` moved from
  `engine: {id: gemini}` to `engine: {id: copilot}` after the first live
  Issue Triage run (workflow run `33671226992`, triggered by issue #192,
  recorded in the automatically-filed `[aw]` noise issue #195) failed with
  `Invalid auth method selected` (exit code 41), immediately after
  `YOLO mode is enabled` and before any model call was attempted. The
  `GEMINI_API_KEY` repository secret was confirmed present and valid; the
  failure is a confirmed upstream gh-aw Agentic Workflow Firewall (AWF)
  bug (`github/gh-aw#25294`, tracked upstream as
  `github/gh-aw-firewall#1806`/`#1931`/`#2009`): the firewall sandbox sets
  `GEMINI_API_BASE_URL` to its own local API proxy, but at the firewall
  version pinned by this gh-aw release (`0.28.10`) that proxy reports no
  Gemini protocol support (`API proxy enabled: OpenAI=false,
  Anthropic=false, Copilot=false`, no `Gemini=true`), so the Gemini CLI
  cannot select a valid auth method regardless of the secret. Even the
  firewall's later partial fix (`gh-aw-firewall#1944`/`#1995`) reportedly
  left a follow-on `API_KEY_INVALID` failure from key-substitution not
  reaching the sandboxed process. Since this is unfixable from workflow
  frontmatter alone and matches the same "external, non-code, non-billing
  root cause" pattern as the Codex failures above, both Gemini-engine
  workflows were switched to Copilot for consistency rather than pinning
  to a newer/older firewall version and re-testing indefinitely.
- Two `[aw]` automation-noise issues remain open as evidence of the above:
  #194 (`Detection Runs`) and #195 (`TESSERA Issue Triage failed`). They
  are intentionally left as-is (not closed) as the audit trail for this
  entry; future genuine Gemini/Codex engine failures would no longer be
  possible since neither engine is referenced by any workflow anymore.
- This PR itself exercised `tessera-pr-maintainer-audit` and
  `tessera-merge-governor` live (real GitHub Actions runs, first on Codex,
  then on Copilot) and both worked as designed, including correctly
  BLOCKing/ITERATEing on several earlier heads (an OR-logic CI gate bug, a
  blank benchmark-issue placeholder, non-reproducible engine-version
  pinning, a lock-file compiler-version mismatch, an
  `agentics-maintenance.yml` scope leak, and the
  `mergeStateStatus`/`workflow_dispatch` bugs above), and correctly staying
  fail-closed (not silently authorizing merge) through two consecutive
  live engine failures.
  `tessera-issue-triage`, `tessera-pr-fixer`, and
  `tessera-post-merge-lifecycle` have not yet executed against a live event
  in this delivery; compilation and static governance tests are the
  available pre-merge evidence for those three.
- **Canonical merge record (post-merge lifecycle reconciliation of #181/#182):**
  final candidate head `30bfdfa02735c9d68ce546182e00a68c205a1b6b` was merged
  to `main` as canonical merge commit `c349bac48c5fb1427f15615fc26e4fbc748ed320`.
  Tracker issue #181 is closed as `IMPLEMENTED` (Stage A only); it is not
  `VALIDATED`, since that label is reserved for capabilities with required
  CI/benchmark evidence against the canonical merge SHA and this delivery is
  process/governance tooling with `NOT_APPLICABLE` benchmark applicability.
  See `docs/ROADMAP.md`'s reconciliation matrix for the authoritative row.
