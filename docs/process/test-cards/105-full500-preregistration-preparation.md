# 105 — Prepare full-500 membership and preregistration

| Field | Value |
|---|---|
| Issue | [#105](https://github.com/LuigiFerronatto/TESSERA/issues/105) |
| Record status | `IN_PROGRESS` preparation; empirical execution `BLOCKED` |
| Capability type | `benchmark infrastructure` |
| Pull request | [#321](https://github.com/LuigiFerronatto/TESSERA/pull/321); exact head recorded by GitHub checks |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `SMOKE_ONLY` for this offline preparation |
| Last audited | 2026-10-02 |

## In one sentence

Freeze the public question IDs and expose missing execution gates without running full-500.

## What problem existed?

Main defines dev-50 retrieval but has no separate full-500 preregistration readiness gate.

## How did TESSERA behave before?

The canonical #96/#100 benchmark was retrieval-only. Reader quality, human judge
calibration and full-500 quality acceptance remained separate future work.

## What changed or is being tested?

A 500-ID manifest projected from checksum-verified official bytes plus a draft preregistration and strict structural/readiness checks.

## How does it work now?

**CANDIDATE — NOT YET ON MAIN.** The validator verifies exact source-file order/hash and rejects unknown fields, substituted IDs, missing dependency evidence and unselected model/budget/review fields. Execution remains deliberately unavailable even after structural completion.

## Concrete example

```text
python -m benchmarks.answer_protocols.cli validate --selection benchmarks/answer_protocols/full500-ids.json --preregistration benchmarks/answer_protocols/full500-preregistration.json
# structurally_valid: true; execution_available: false; remaining gates listed
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

Accepted #96/#100/#103/#104 and compatible #28; canonical dependencies and frozen configs/artifacts; reviewed thresholds, budget, attempts, exclusions, statistics, environment, retention and execution authorization; future checkpointed F0–F4 implementation and complete results. Full-500 includes dev-50 and is not a wholly independent holdout.

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
