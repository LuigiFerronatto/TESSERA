# LongMemEval V1 — canonical dev-50 baseline

> Retrieval-only development record. It does not measure final-answer correctness,
> run a reader, call an LLM judge, or represent the official full-500 result.

## Record

- Record ID: `longmemeval-v1-dev-50/96-b09ceacc`
- Decision: `KEEP`
- Issue / PR: #96 / #99
- Measured commit: `b09ceacc24d9dfb67f9cd63f5219cd2ce8bc9f5a`
- Merge commit: `812c3aa37b59a3e99135a9d8b39245aeb71356d0`
- Retrieval contract: `fb23012ba4b2fddc3912d7cb593391a04fe45ae7`

## Experimental profile

- Profile: `longmemeval-v1-dev-50`
- Dataset: `longmemeval_s_cleaned.json` (`cleaned-2025-09`)
- Dataset SHA-256: `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
- Queries: 50 (46 positive, 4 abstention)
- Subset / Top-K / granularity: `deterministic-small` / 10 / `session`
- Reader / LLM judge: none / none

## Retrieval metrics

| Metric | Value |
| --- | ---: |
| Recall@1 | 0.4710144928 |
| Recall@3 | 0.7028985507 |
| Recall@5 | 0.7753623188 |
| Recall@10 | 0.9166666667 |
| MRR | 0.7785024155 |
| nDCG@10 | 0.7874548354 |
| Evidence hit rate | 0.9565217391 |
| First evidence position | 1.9318181818 |
| Provenance coverage | 1 |
| Abstention retrieval empty rate | 0 |
| Average context characters | 12574.122 |
| Average whitespace tokens | 2049.184 |

## Determinism and provenance

- Same-commit runs: 2
- Equivalent: `true`
- Normalized SHA-256: `e284a8229436e59e116ee066226fdb89bbad656fcc8828fffa2e81cfc9069944`
- Retrieval-result SHA-256: `759f5f01ec5898b44a30bf3cc28549df21d36eb7405f7e063d9c98c3b1b463dc`
- Selected-query-order SHA-256: `a5549148e1405715c970e640b7146a42670e9d2735270419d0a0a5d872e6480a`

## Cost and latency

- API calls: 0
- LLM calls: 0
- Estimated cost: USD 0
- Latency is informational and unavailable as a comparable canonical value.

## Plain-language interpretation

- Recall@K is the proportion of expected evidence sessions recovered in the first K results; it is not answer accuracy.
- Evidence hit rate is the percentage of positive questions with at least one expected evidence session in Top-K.
- MRR measures how early the first relevant result appears; nDCG measures evidence presence and ordering.
- Provenance coverage measures whether retrieved results remain traceable.
- Abstention retrieval empty rate only reports whether retrieval returned no candidates; it does not measure correct answer-stage abstention.
- This 50-query profile measures retrieval only and is a development gate, not an official full-500 score.

## Limitations

- 50-question subset is not an official full LongMemEval score
- retrieval only; no reader, generation, or LLM-as-judge
- canonical comparable latency was not recorded

## Decision: `KEEP`
