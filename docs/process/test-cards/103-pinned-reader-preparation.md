# 103 — Prepare a pinned reader without running one

| Field | Value |
|---|---|
| Issue | [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103) |
| Record status | `IN_PROGRESS` preparation; empirical execution `BLOCKED` |
| Capability type | `benchmark infrastructure` |
| Pull request | [#321](https://github.com/LuigiFerronatto/TESSERA/pull/321); exact head recorded by GitHub checks |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `SMOKE_ONLY` for this offline preparation |
| Last audited | 2026-10-02 |

## In one sentence

Prepare an auditable reader transport while keeping real inference blocked.

## What problem existed?

Main has retrieval evaluation but no pinned reader capture boundary.

## How did TESSERA behave before?

The canonical #96/#100 benchmark was retrieval-only. Reader quality, human judge
calibration and full-500 quality acceptance remained separate future work.

## What changed or is being tested?

Closed request/output/capture schemas, unchanged opaque #28 message transport, structural label guards and persistence-before-evaluation are exercised with invented responses.

## How does it work now?

**CANDIDATE — NOT YET ON MAIN.** A synthetic script writes the request first, retains each failed attempt and writes a completion receipt last. J0 joins references only after verifying persisted capture hashes.

## Concrete example

```text
python -m benchmarks.answer_protocols.cli synthetic --output artifacts/answer-protocols/run-a
# 4 invented cases; 3 successful mock captures; 1 preserved mock provider failure; zero provider calls
```

## How was it validated?

Focused offline tests in `tests/test_answer_protocol_preparation.py` cover closed
schemas, hash/ID tampering, label boundaries, persistence, attempt retention,
reviewer independence and fail-closed execution. Full regression, sanity and
packaging evidence are recorded for the exact candidate in the PR conversation.
Synthetic fixtures do not count as real model performance or human calibration.

## What improved?

The preparation is reviewable and reproducible, with explicit missing gates and
no silent conversion of draft metadata into empirical acceptance. No runtime,
ranking/default, source, workflow or #100 retrieval ledger change is introduced.

## What remains unimplemented?

Accepted #28/#74/#96/#100 compatibility; immutable reader/prompt/model/tokenizer/config; approved bounded execution and retention; frozen dev-50 input, two real repeated passes and complete answer/citation/abstention/usage reports. The four dev-50 abstention cases remain unevaluated.

## What is unlocked next?

Protocol review can proceed now. No empirical dependent work or issue closure is
unlocked until canonical dependencies, required real evidence and human review
are accepted. Models, budget decisions, thresholds and human labels remain null.

## Technical provenance

- Base main: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- [Protocol and commands](../../benchmarks/answer_protocols/README.md)
- [Independent-human instructions](../../benchmarks/answer_protocols/HUMAN_REVIEW.md)
- Proposed #28 interface: unmerged [PR #315](https://github.com/LuigiFerronatto/TESSERA/pull/315), head `85638e1320ca68bfdd15efbfaed14a1791218120`
- Exact candidate/head and CI URLs: [PR #321](https://github.com/LuigiFerronatto/TESSERA/pull/321); no canonical merge claimed

## Evolution

Canonical retrieval-only benchmark → linked offline preparation candidate →
future separately authorized/calibrated execution after dependency acceptance.
No earlier delivery is superseded, and this issue remains open.
