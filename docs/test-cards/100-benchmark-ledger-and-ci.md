# #100 — Keep benchmark results comparable over time

| Field | Value |
|---|---|
| Issue | [#100](https://github.com/LuigiFerronatto/TESSERA/issues/100) |
| Record status | `VALIDATED` |
| Capability type | `benchmark infrastructure` |
| Pull request | [#102](https://github.com/LuigiFerronatto/TESSERA/pull/102) |
| Merge commit | [`39febe3`](https://github.com/LuigiFerronatto/TESSERA/commit/39febe36f016997f0c54ede9824f15dec04cc1ee) |
| Decision | `KEEP` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-08-31 |

## In one sentence

Benchmark results now have a versioned ledger and CI rules that compare a candidate with its immediate parent instead of relying on copied numbers.

## What problem existed?

A single baseline snapshot could not reliably explain whether a later PR improved, regressed or merely ran in a different environment.

## How did TESSERA behave before?

LongMemEval dev-50 was reproducible locally, but historical and forward comparisons, applicability decisions and environment drift were not one enforced contract.

## What changed or is being tested?

PR #102 added a closed result schema, canonical records, environment fingerprints, parent comparison, PR applicability declarations and conditional benchmark CI.

## How does it work now?

Every PR declares `REQUIRED`, `SMOKE_ONLY` or `NOT_APPLICABLE`. Required candidates run the frozen dev-50 profile twice, compare with the immediate parent and retain historical #96 comparison separately.

## Concrete example

A retrieval-changing PR can no longer say “Recall looks good.” It must show the same-profile baseline, candidate, delta, determinism, environment and regression decision.

## How was it validated?

The delivery produced identical normalized run hashes, zero query-level semantic changes, green reporting/dev-50 CI and green Python/smoke/sanity jobs.

## What improved?

Benchmark evidence became longitudinal, attributable and reviewable.

## What remains unimplemented?

Dev-50 remains retrieval-only. Reader accuracy, judge calibration, full-500 and V2 remain separate cards. Machine-dependent latency remains informative rather than a hard universal guarantee.

## What is unlocked next?

Future Test Cards can prove candidate value against both immediate-parent and historical reference states.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#100](https://github.com/LuigiFerronatto/TESSERA/issues/100) |
| Pull request | [#102](https://github.com/LuigiFerronatto/TESSERA/pull/102) |
| Merge commit | [`39febe3`](https://github.com/LuigiFerronatto/TESSERA/commit/39febe36f016997f0c54ede9824f15dec04cc1ee) |
| Evidence/Learnings/Decision | [Issue evidence](https://github.com/LuigiFerronatto/TESSERA/issues/100#issuecomment-5471939801) |
| Benchmark record | [Forward dev-50 record](../../benchmarks/results/longmemeval-v1-dev-50/forward.md) |
| PR Evolution Audit | PR #102 description |

## Evolution

```text
one reproducible baseline
→ versioned result ledger and parent comparison
→ conditional longitudinal benchmark CI
→ controlled reader/judge/full-set evaluation
```
