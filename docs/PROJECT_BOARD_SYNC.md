# TESSERA Project Board Sync

`scripts/sync_project_board.py` deterministically syncs each open TESSERA
issue's own declared portfolio routing to
[GitHub Project #9](https://github.com/users/LuigiFerronatto/projects/9).

## Why five separate fields

It is easy to blur these questions together. They are answered by different
fields on purpose:

| Field       | Question                                     |
| ----------- | --------------------------------------------- |
| `Status`    | Em que estado operacional está?                |
| `HORIZON`   | Quando pretendemos puxar? (Execution)          |
| `Queue`     | Em qual ordem?                                 |
| `Priority`  | Quão importante/crítico é?                     |
| `Milestone` | Em qual fase arquitetural pertence?             |

Critically:

```text
Ready       != NOW
P0          != NOW
Milestone M1 != NEXT
```

A perfectly valid classification looks like:

```text
#176
Status:    Ready
Execution: NEXT
Priority:  P0
Milestone: M2
```

`Ready` means the card can technically start; it says nothing about whether
it has been *selected* for the current WIP window. `HORIZON=NOW` is that
selection, and it is capped (see "WIP policy" below).

## Status semantics

The Project's `Status` single-select only has six options today (`Backlog`,
`Blocked`, `Ready`, `In progress`, `In review`, `Done`) -- there is no native
`Deferred`, `Dropped`, `Validation` or `Inbox` option. Rather than silently
inventing new option IDs, the script maps those concepts onto the nearest
existing option and records that mapping in `reasons`:

- `Deferred` -> `Backlog` (`STATUS_DEFERRED_MAPPED_TO_BACKLOG_NO_NATIVE_OPTION`)
- `Dropped` (closed, `state_reason=NOT_PLANNED`) -> `Backlog`
  (`STATUS_DROPPED_MAPPED_TO_BACKLOG_NO_NATIVE_OPTION`)

Live GitHub evidence always overrides stale issue-body text:

- an open **draft** PR closing the issue -> `In progress`
- an open **non-draft** PR closing the issue -> `In review`
- a closed issue -> `Done` (or `Backlog` if `state_reason=NOT_PLANNED`)
- a declared blocker (`Depends on` / `Active blocker`) that references an
  issue which is no longer open -> the text is stale; the script overrides
  to `Ready` and flags `STATUS_BLOCKED_TEXT_STALE_ALL_BLOCKERS_CLOSED`
- a declared conditional readiness ("READY FOR DESIGN **after** #176 is
  accepted") whose referenced issue is still open -> `Blocked`, not `Ready`
  (`STATUS_READY_CONDITIONAL_UNSATISFIED_DEPENDENCY_OPEN`). If the
  conditional clause names no issue at all ("ready after baseline fixture
  is frozen"), the script cannot verify it and conservatively returns
  `Blocked` (`STATUS_READY_CONDITIONAL_UNVERIFIABLE_CONSERVATIVE_BLOCKED`)
  rather than inventing readiness.

Split cards such as `#16` ("P0 containment ready; full experiment blocked")
surface as `Ready` -- the executable slice can start now -- while the split
nuance is preserved in `reasons`, not silently discarded.

## Sources of truth (architecture decision)

Two independent sources feed the classifier, deliberately kept separate to
avoid `GitHub Project != issue body != ROADMAP != script` drift:

- **`Status` / `Priority` / `Milestone`** come from each issue's own
  `## Portfolio routing` / `## Authoritative portfolio routing` block
  (see `docs/ROADMAP.md`'s reference to this contract), overlaid with live
  GitHub state as described above. The issue body is authoritative.
- **`HORIZON` / `Queue`** (Execution ordering) come from
  `governance/portfolio_execution.yaml`, *not* from issue bodies and *not*
  from regex-scraping `docs/ROADMAP.md` prose. Issue bodies do not declare
  an execution horizon today, and `ROADMAP.md`'s "Canonical execution
  board" is written for humans, not as a parser contract. The YAML file is
  the single ordering source of truth; `ROADMAP.md` is the human-readable
  narrative of that same ordering and must be kept consistent with it by
  hand, but the script never parses `ROADMAP.md`.

This is "Variant B" from the original design options (a small, versioned,
repository-owned portfolio manifest), chosen over regex-parsing
`ROADMAP.md` prose (fragile) or requiring every issue body to declare its
own Execution/Queue (would mean editing ~70 issue bodies for no product
reason).

`governance/portfolio_execution.yaml` also owns two override lists:

- `deferred_status_override`: issues whose own body declares `READY` but
  which this portfolio intentionally keeps at `Status=Backlog` to protect
  the `NOW` WIP limit (their `HORIZON`/`Queue` still records where they
  resume).
- `trackers`: `Type: epic/tracker` issues, which never consume `Queue` or
  count toward the `NOW` WIP limit.

## WIP policy

`HORIZON=NOW` is capped at `--now-wip-limit` (default `3`; trackers never
count). Exceeding it fails the sync with an actionable error rather than
silently letting `NOW` balloon; pass `--allow-wip-overflow` to bypass this
explicitly (never happens implicitly).

`Queue` is a single global ordinal: no duplicates, always positive, and
every `NOW` queue position must precede every `NEXT` position, which must
precede every `LATER` position.

## Usage

```bash
# Default: read-only. Never mutates anything.
python scripts/sync_project_board.py
python scripts/sync_project_board.py --dry-run

# Machine-readable plan.
python scripts/sync_project_board.py --dry-run --json

# Apply the computed plan. Requires `gh auth status` with the `project` scope.
python scripts/sync_project_board.py --apply
```

Every planned change carries `reasons` (reason codes) explaining exactly
why, e.g. `STATUS_READY_DECLARED`, `EXECUTION_NOW_CANONICAL_QUEUE_MANIFEST`,
`STATUS_BLOCKED_TEXT_STALE_ALL_BLOCKERS_CLOSED`.

## Safety contract

- Default invocation never mutates anything; `--apply` is required.
- Every ProjectV2/field/option/item ID is discovered live via
  `gh api graphql` -- nothing is hard-coded.
- The script never invents a missing Status/Priority/HORIZON option; if a
  required field/option is absent it fails with an actionable diagnostic
  rather than guessing an ID (`--bootstrap-fields` is reserved for future
  use; TESSERA's Project #9 already has `Status`, `HORIZON`, `Queue` and
  `Priority`, so it is a no-op today).
- `Milestone` is native GitHub issue metadata (not a duplicate Project
  field); the script updates the issue's real milestone via
  `gh issue edit --milestone`.
- Scope: only currently OPEN issues are read/classified/synced. Closed
  issues already on the board (`Done`/`Dropped`) are left untouched.
- Apply computes the full plan before mutating anything, reports
  successes/failures per issue, and exits non-zero if any mutation failed.
  Re-running `--dry-run` after `--apply` must show zero changes (verified
  in CI-independent manual runs; see the PR that introduced this tool).

## Testing

All classification/parsing/WIP/idempotency logic is covered offline in
`tests/test_sync_project_board.py` using frozen fixtures under
`tests/fixtures/project_board_sync/` -- no network access or `gh`
authentication is required to run the suite:

```bash
python -m pytest tests/test_sync_project_board.py -q
```
