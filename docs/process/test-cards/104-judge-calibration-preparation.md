# 104 — Prepare independent judge calibration review

| Field | Value |
|---|---|
| Issue | [#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) |
| Record status | `IN_PROGRESS` preparation; empirical execution `BLOCKED` |
| Capability type | `benchmark infrastructure` |
| Pull request | [#321](https://github.com/LuigiFerronatto/TESSERA/pull/321); exact head recorded by GitHub checks |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `SMOKE_ONLY` for this offline preparation |
| Last audited | 2026-10-02 |

## In one sentence

Prepare real humans to calibrate an eventual judge without inventing their labels.

## What problem existed?

Main defines a benchmark-only judge boundary but has no independent-human review packet.

## How did TESSERA behave before?

The canonical #96/#100 benchmark was retrieval-only. Reader quality, human judge
calibration and full-500 quality acceptance remained separate future work.

## What changed or is being tested?

Eight unlabeled sampling coverage slots and a blind independent-human review protocol; a validator retains two initial judgments and requires a distinct adjudicator for disagreement.

## How does it work now?

**CANDIDATE — NOT YET ON MAIN.** All model, threshold, sample and human-label fields remain null. Synthetic reviewer identities exercise mechanical validation only. No judge inference or label generation runs.

## Concrete example

```text
python -m benchmarks.answer_protocols.cli judge-packet --output /tmp/new-judge-packet.json
# DRAFT; 8 unlabeled coverage slots; judge selection null
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

Accepted #74/#100/#103; licensed fixed calibration sample, real independent labels/rationales and accepted thresholds; immutable judge/prompt/rubric; reviewed provider/verdict implementation; actual agreement, failure, repeatability, sensitivity and usage reports.

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
