# #96 — A reproducible first LongMemEval retrieval baseline

| Field | Value |
|---|---|
| Issue | [#96](https://github.com/LuigiFerronatto/TESSERA/issues/96) |
| Record status | `VALIDATED` |
| Capability type | `benchmark infrastructure` |
| Pull request | [#99](https://github.com/LuigiFerronatto/TESSERA/pull/99) |
| Merge commit | [`812c3aa`](https://github.com/LuigiFerronatto/TESSERA/commit/812c3aa37b59a3e99135a9d8b39245aeb71356d0) |
| Decision | `KEEP` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA can now measure how well its current retriever finds evidence in a fixed 50-question LongMemEval V1 development slice.

## What problem existed?

Retrieval changes could sound sophisticated without a repeatable external baseline proving whether they found more evidence, ranked it earlier or increased cost.

## How did TESSERA behave before?

The repository had deterministic synthetic sanity tests but no reproducible LongMemEval adapter, artifact contract or external retrieval scorecard.

## What changed or is being tested?

PR #99 added a deterministic adapter, pinned dataset preparation, stable question ordering, evaluator and JSON/Markdown artifacts without changing retrieval.

## How does it work now?

For each question, the runner indexes the historical sessions, asks TESSERA for the top ten candidates, then joins evaluator-owned evidence labels only after retrieval. Reader generation is not part of this stage.

## Concrete example

On the canonical 50-question profile, at least one correct evidence session appeared in the top ten for 95.65% of positive-evidence questions. The first correct evidence appeared near position 1.93 on average.

## How was it validated?

Two equivalent runs produced the same normalized SHA-256. The accepted baseline reports Recall@10 0.9167, MRR 0.7785, nDCG@10 0.7875 and provenance coverage 1.0. CI passed without runtime retrieval changes.

## What improved?

TESSERA gained an auditable external retrieval baseline and leakage guards.

## What remains unimplemented?

This is 50 of 500 questions, not an official full-set result. It does not measure answer correctness, a reader, an LLM judge, semantic abstention or LongMemEval V2.

## What is unlocked next?

It enables controlled renderer, reader and full-evaluation cards when their remaining dependencies close.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#96](https://github.com/LuigiFerronatto/TESSERA/issues/96) |
| Pull request | [#99](https://github.com/LuigiFerronatto/TESSERA/pull/99) |
| Merge commit | [`812c3aa`](https://github.com/LuigiFerronatto/TESSERA/commit/812c3aa37b59a3e99135a9d8b39245aeb71356d0) |
| Evidence/Learnings/Decision | [Issue evidence](https://github.com/LuigiFerronatto/TESSERA/issues/96#issuecomment-5471323841) |
| Benchmark record | [Historical dev-50 baseline](../../benchmarks/results/longmemeval-v1-dev-50/baseline.md) |
| PR Evolution Audit | PR #99 description |

## Evolution

```text
synthetic sanity only
→ deterministic LongMemEval V1 dev-50 adapter
→ frozen retrieval baseline
→ renderer, reader, judge and full-500 stages
```
