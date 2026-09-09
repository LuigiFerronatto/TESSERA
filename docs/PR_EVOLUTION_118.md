# PR Evolution Audit — #118 clean-room onboarding

## Canonical lifecycle

- Issue: #118; closed; status `VALIDATED`; decision `KEEP`; historical Queue 4.
- Branch: `test-card/118-clean-room-onboarding`.
- Audited starting main: `112ae63c9ba1d8ffbe6ed3f2edf439d7dbe5b3a0`.
- Final candidate: `b83c18494f9a2bc5687010ee27f077ac81688b6f`.
- Canonical squash merge: `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d`,
  merged by the maintainer on 2026-09-09; #118 closed automatically.
- Candidate and canonical merge have identical Git trees and count as **one
  runtime delivery**. This post-merge reconciliation is `DOCUMENTATION_CORRECTION`.
- Benchmark applicability: `SMOKE_ONLY`.
- Final exact-head [Maintainer Audit: KEEP](https://github.com/LuigiFerronatto/TESSERA/pull/225#issuecomment-5603811873)
  and [Merge Governor: success](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34365927883)
  preceded the human merge of [PR #225](https://github.com/LuigiFerronatto/TESSERA/pull/225).

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
| #118 / #225 | `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d` | Installed onboarding gate and two narrow init/discovery fixes; candidate `b83c18494f9a2bc5687010ee27f077ac81688b6f` is the same delivery |

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

Predecessor candidate validation: **538 passed, 5 skipped** in the clean full suite; **62**
focused init/discovery regressions, **96** routing/documentation checks, and **54
passed, 5 skipped** packaging/governance checks. Both local installed environments
passed 67 console commands plus probes and uninstall. TESSERA CI
[34362352380](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34362352380)
passed its Python 3.9/3.12 distributions, full suites, CLI smoke and sanity for
candidate `3f0088a45c991ba6a39c36b2d90c599d351b44d3`. This is predecessor evidence:
the final artifact checkout now explicitly uses the PR head rather than the
synthetic merge ref.

[Versioned evidence](evidence/118-clean-room/validation.json) includes artifact
inventories/hashes, local Python/installer versions, all fixture source hashes,
config, counts, timings, TTY/cancel transcripts, partial-state and uninstall
results. Baseline and after sanity quality metrics are identical.

See the PR's final evidence record for final source SHA, distribution inventory,
hashes/sizes, Python/build/installer versions, source fixture hashes, durations,
query/rebuild comparisons, test counts, sanity after and exact-head CI links.
`environment.json` and `installed.json` are uploaded by each distribution job.

Final candidate `b83c18494f9a2bc5687010ee27f077ac81688b6f` passed **68 installed
CLI commands and 69 source-integrity checkpoints per environment**, with zero
source mutations. [CI 34363459711](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34363459711)
and [Benchmark Ledger 34363459996](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34363459996)
passed at that exact head. The first independent ITERATE requested prior-gitlink
provenance and completed-check evidence; the final audit accepted the evidence
and returned KEEP with no supported P0/P1 findings, without a new candidate.

Post-merge [CI 34367274210](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34367274210)
and [Benchmark Ledger 34367274180](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34367274180)
both passed on canonical `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d`. The downloaded
Python 3.9.25/3.12.14 distribution reports explicitly bind that SHA, report
`passed: true`, and prove installed `site-packages` imports, the complete fixture
contract and successful uninstall. [Canonical merge evidence](evidence/118-clean-room/canonical-merge.json)
records their artifact hashes, report hashes and unchanged sanity metrics.

## Findings and classification

| Finding | Classification | Resolution |
|---|---|---|
| Repeating named-global init inside a configured project selected the local corpus | `IN_SCOPE_FIX` | Apply the already accepted global plan directly on a no-change rerun; do not use general project discovery |
| Unselected alias to selected README poisoned config doctor/repeat init | `IN_SCOPE_FIX` | Match the discovered forbidden entry's path; keep symlink exclusion and explicitly configured alias diagnostics |
| Local checkout inventory included verification/cache artifacts | `ENVIRONMENTAL` | Run full validation from a clean worktree; do not alter unrelated user files or weaken the inventory test |
| Ambient build dependency index failed; temporary venv installation exhausted local disk | `ENVIRONMENTAL` | Explicit public dependency index, credential-free child environment, and cleanup restricted to this task's temporary environments |
| Initial harness compared casefold source order with filesystem order | `FALSE_POSITIVE` | Preserve exact semantic source order and compare independently sorted index membership |
| Initial audit-hook namespace failed its own active-guard probe | `FALSE_POSITIVE` | Use an explicit execution namespace; no product change |
| Existing hosted-site gitlink had no `.gitmodules` mapping, making the required Maintainer Audit checkout fail before review | `IN_SCOPE_FIX` (CI bootstrap) | Record its verified existing remote and path with `update = none`; preserve the exact gitlink commit and site files, with no site fetch or deployment |
| Board status parsing maps a branch-only IN_PROGRESS declaration to Backlog | `OUT_OF_SCOPE_FOLLOW_UP` | The canonical linked-PR overlay correctly routes this card after its draft PR exists; no board-classifier redesign included |

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

**VALIDATED / KEEP**: the installed-artifact contract passed on Python 3.9 and
3.12, both reproduced runtime defects have focused regressions, and the held-
constant sanity corpus is unchanged. The inherited checkout defect is repaired
without moving/deleting site files or changing its gitlink commit. Independent
audit and governor passed for the final candidate; the maintainer merged it;
canonical-merge CI and Benchmark Ledger then passed. These are distinct gates,
now satisfied. The lifecycle correction adds no runtime delivery or release.

## Scope and downstream routing

#120 remains READY / Queue 5 and is the next implementation after this lifecycle
correction merges. Start it from fresh canonical main, not this lifecycle branch.
#87 remains the owner decision / Queue 6. #134's #118 prerequisite is satisfied;
it remains BLOCKED solely by #87. No automatic
merge, publication, release, tag, #119/#120/#121/#134 implementation, intelligence,
enrichment, hooks, integration setup or import work is authorized by this PR.

Residual repository hygiene: the existing external site's ownership and host
longevity were not independently certified. Its gitlink was introduced by
`4fdb4b79dab06cdce638eb78eea024b188c1272a`, before #225, and remains at
`ae439b0e1c4ffbeabc39f19f0579e8f0f0dedc50` with `update = none`. Any ownership or
hosting review is a separate follow-up; it does not reopen #118 or expand #120.
