# 16 — Non-destructive conflict-resolver containment

| Field | Value |
|---|---|
| Issue | [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16) |
| Record status | `VALIDATED` (P0 containment); `BLOCKED` (full supersession) |
| Capability type | `runtime` |
| Pull request | [#219](https://github.com/LuigiFerronatto/TESSERA/pull/219) |
| Head commit | `2420bb5aa70e5d9663b92ae2785eda33f42f1cbe` |
| Merge commit | `708c973e23d5c4eb8a52d359a2cadc153e161a90` |
| Decision | `KEEP` |
| Benchmark applicability | `REQUIRED` (met — LongMemEval V1 dev-50 passed, 0 regressions) |
| Last audited | 2026-09-05 |

## In one sentence

TESSERA now keeps older and newer retrieved evidence visible when it cannot
prove supersession, instead of silently deleting everything except the newest
candidate in a coarse group.

## What problem existed?

The compatibility resolver treated the first entity plus the first tag as a
conflict identity. It kept only the most recently updated factual/preference
candidate for each such key even though that key was not a validated
`state_key` and did not prove contradiction, scope, validity or supersession.

## How did TESSERA behave before?

At canonical main `700b5ada9be059ced1c9f0d3d369b9824f4baaa5`:

```text
input IDs:  P1, P2, P3
input order: 2026-01-01, 2026-02-01, 2026-03-01
coarse key: user_reports
output IDs: P3
lost IDs:   P1, P2
```

Two unrelated preferences with the same `user_reports` key similarly returned
only the newer candidate, proving a false grouping could erase evidence.

## What changed or is being tested?

Containment variant C1 disables destructive filtering in the normal retrieval
path. The public method and list return type remain compatible, but the pass
returns a shallow list copy containing the original candidate objects in the
same order. No legacy newest-only mode is retained.

## How does it work now? — VALIDATED ON MAIN

```text
ranked candidates
→ possible-conflict containment
→ preserve every candidate, ID, score, provenance and order
→ apply the existing top_n result cap
```

This is evidence preservation, not state reconstruction. Ranking algorithms
and scores are unchanged.

## Concrete example

```text
P1 Prefer concise reports.
P2 Prefer more detail than before.
P3 Prefer highly detailed reports for quarterly reviews.

before: P3
after:  P1, P2, P3
```

A contextual preference and a broad preference both survive. Directly
contradictory preferences also both survive because no deterministic rule in
this slice can truthfully select a winner.

## How was it validated?

The pre-fix regression run produced `10 failed, 3 passed` and showed the
trajectory, false-collision and default Engine path losing candidates. After
the containment change, the focused suite passed `14` tests. Dedicated cases
cover three chronological preferences, contextual scope, unresolved
contradiction, false grouping, old-but-valid facts, metadata order, unchanged
object/provenance identity, unchanged source bytes, ranking parity, default
Engine behavior, no duplicates and no provider/network requirement.

## What improved?

- No candidate is removed solely because it is older.
- The compatibility key is no longer treated as canonical state identity.
- Query-conditioned state work can later inspect the full preference history.
- The pass remains deterministic, local, cheap and read-only.

## What remains unimplemented?

This slice does not add #15 temporal fields or state keys, #141 `Fq/Tq/Iq`
reconstruction, #20 evidence status, #27 cross-source arbitration, or the full
#16 temporal supersession model. It adds no annotation/state machine and does
not claim which candidate is current.

## What is unlocked next?

No downstream card becomes `READY` from this merge alone. #16 P0 containment
is now `VALIDATED`, while the full #16 slice remains `BLOCKED` on #15/#73/#96
(none of which changed as a result of this merge). #141, #20 and #27 retain
their other blockers unchanged. Queue #4 remains #118.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #16](https://github.com/LuigiFerronatto/TESSERA/issues/16) |
| Pull request | [PR #219](https://github.com/LuigiFerronatto/TESSERA/pull/219) |
| Starting canonical main | `700b5ada9be059ced1c9f0d3d369b9824f4baaa5` |
| Canonical merge SHA | `708c973e23d5c4eb8a52d359a2cadc153e161a90` |
| Evidence/Learnings/Decision | Focused pre-fix (10 failed) and post-fix (14 passed) regression runs; exact-head Maintainer Audit `KEEP`; decision `KEEP` |
| Benchmark record | `REQUIRED`; met — LongMemEval V1 dev-50 passed at the merged head, 0 gating/query regressions |
| PR Evolution Audit | [`docs/PR_EVOLUTION_16.md`](../PR_EVOLUTION_16.md) |

## Evolution

```text
coarse key + newest-only deletion
→ P0 containment merged and validated (708c973e)
→ #15 + later #16 full supersession experiment (blocked)
```
