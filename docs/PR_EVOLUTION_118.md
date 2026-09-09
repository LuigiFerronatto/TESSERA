# PR Evolution Audit — #118 clean-room onboarding

## Candidate lifecycle

- Issue: #118; status `IN_PROGRESS`; Queue 4.
- Branch: `test-card/118-clean-room-onboarding`.
- Audited starting main: `112ae63c9ba1d8ffbe6ed3f2edf439d7dbe5b3a0`.
- Canonical merge: none. Final candidate SHA is bound by the PR's head and its
  exact-head CI/Maintainer Audit, not a claim of merged delivery.
- Benchmark applicability: `SMOKE_ONLY`.
- Decision: `PENDING` until installed experiments and independent audit finish.

## Relevant delivery history

| Delivery | Canonical merge | Contribution consumed here |
|---|---|---|
| #116 / #131 | `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4` | Wheel/sdist, base/optional dependency and package-data boundary |
| #117 / #150 | `61cf76fbd6ed61972f0f5abae515ba9bffca4b55` | Project/global config discovery and stable store identity |
| #153 / #173 | `2508676d472088733702b6ed920fc829df9a7681` | Independent store, source corpus and derived index |
| #154 / #175 | `05ce0dd234a7756d4a5ba315b77e4a6ec33c9429` | Canonical source discovery and ignore policy |
| #155 / #210 | `4c112195f1572bf352d1cc6a1042c69711381da8` | Selection, planning, confirmation and indexing |
| #16 / #219 | `708c973e23d5c4eb8a52d359a2cadc153e161a90` | Non-destructive conflict containment |
| #221 / #222 | `21b726acb9bce519960de389ebb75181b1b9df6a` | Canonical lifecycle reconciliation; prerequisite to starting #118 |
| #223 / #224 | `112ae63c9ba1d8ffbe6ed3f2edf439d7dbe5b3a0` | Six research/documentation files; no additional runtime delivery |

The fetched main matched the supplied starting SHA. #222 was merged and #221
closed before the dedicated branch was created. #155's canonical Test Card and
merge ancestry proved validation despite stale issue-body routing. #118's body
was corrected to READY, then IN_PROGRESS after branch creation. Project #9 was
updated with `scripts/sync_project_board.py --apply`, retaining queues and the
#87/#134 blockers. A post-apply dry run verified zero changes.

Candidate and merge commits in the history are one delivery each. This PR
does not count historical lifecycle or documentation commits as runtime features.

## Before and after

The shipped wheel could initialize the frozen source corpus, but its diagnostic
and repeat-init composition had two defects. The candidate changes only accepted
global-plan resolution and forbidden-entry diagnostic matching. The scanner,
configuration schema, source ordering, semantic drawers and retrieval algorithms
retain their established ownership.

## Evidence

Baseline on clean audited main: **535 passed, 1 failed, 5 skipped**. The failure
was `test_named_global_existing_store_is_idempotent_and_material_change_is_guarded`.
Running in the developer checkout also produced an inventory failure from local
verification/cache files; the clean checkout removed that environmental result.
Baseline focused packaging/config/discovery/init/storage suite: **105 passed,
1 failed**. Baseline deterministic sanity: Hit@1 **0.75**, Hit@3/5 **1.00**,
MRR **0.875**, evidence hit **1.00**, missing-evidence check passed.

The canonical build method is `python -m build`: it creates the sdist, then
builds the wheel from that sdist in an isolated build environment. The installed
experiments use the wheel directly and prove imports originate in the temporary
venv's `site-packages`. Neither editable installs nor checkout imports count as
installed-artifact evidence.

See the PR's final evidence record for final source SHA, distribution inventory,
hashes/sizes, Python/build/installer versions, source fixture hashes, durations,
query/rebuild comparisons, test counts, sanity after and exact-head CI links.
`environment.json` and `installed.json` are uploaded by each distribution job.

## Findings and classification

| Finding | Classification | Resolution |
|---|---|---|
| Repeating named-global init inside a configured project selected the local corpus | `IN_SCOPE_FIX` | Apply the already accepted global plan directly on a no-change rerun; do not use general project discovery |
| Unselected alias to selected README poisoned config doctor/repeat init | `IN_SCOPE_FIX` | Match the discovered forbidden entry's path; keep symlink exclusion and explicitly configured alias diagnostics |
| Local checkout inventory included verification/cache artifacts | `ENVIRONMENTAL` | Run full validation from a clean worktree; do not alter unrelated user files or weaken the inventory test |
| Ambient build dependency index failed; temporary venv installation exhausted local disk | `ENVIRONMENTAL` | Explicit public dependency index, credential-free child environment, and cleanup restricted to this task's temporary environments |
| Initial harness compared casefold source order with filesystem order | `FALSE_POSITIVE` | Preserve exact semantic source order and compare independently sorted index membership |
| Initial audit-hook namespace failed its own active-guard probe | `FALSE_POSITIVE` | Use an explicit execution namespace; no product change |

## Learnings

- CLI configuration precedence is appropriate for ordinary command discovery,
  but re-running an accepted global initialization plan must preserve its scope.
- Physical containment and lexical selection answer different questions:
  a forbidden alias does not become selected because its target is selected.
- Real installed TTY and filesystem failures expose composition problems that
  prompt mocks and unit tests alone do not prove away.
- Source hashes, exact membership and evidence identity/order are stronger
  reconstruction proof than a successful index command or equivalent path string.
- Partial failure does not imply rollback. The user needs the observed config,
  store/index state and a recoverable rerun; source truth remains intact.

## Decision

Pending final installed experiments and independent exact-head audit. KEEP is
permitted only when the complete clean-room contract passes. An open green PR
still remains IN_PROGRESS and requires independent maintainer review.

## Scope and downstream routing

#120 remains READY / Queue 5. #87 remains the owner decision / Queue 6. #134 is
BLOCKED until both #118 canonical validation and #87 are satisfied. No automatic
merge, publication, release, tag, #119/#120/#121/#134 implementation, intelligence,
enrichment, hooks, integration setup or import work is authorized by this PR.
