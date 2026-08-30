# LongMemEval V1 — forward dev-50 record

> Retrieval-only development record. It does not measure final-answer correctness,
> run a reader, call an LLM judge, or represent the official full-500 result.

## Record

- Record ID: `longmemeval-v1-dev-50/forward-467ba649f533`
- Decision: `KEEP`
- Issue / PR: #100 / #102
- Measured commit: `467ba649f53312cedcecf40caf548af5f766c67b`
- Merge commit: `None`
- Retrieval contract: `fb23012ba4b2fddc3912d7cb593391a04fe45ae7`

- Parent commit: `None`
- Execution: `pull_request` / `pull_request:33341628084:1:e0bc0412e1ea2e06b00993b9a11533a2b9a9f6a5` / `forward`
- Python: `CPython 3.12.14`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39` / `x86_64`
- Constraints SHA-256: `ccfe8ef09b8d2c744bce01fd34f3ea9c42da97c7b020dc839e2e090be1d8ca7c`
- Environment fingerprint: `53990d7bab034ff10068093248fa0756ed2c53023d539a706eba959acfd996b7`

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
| Average context characters | 12583.98 |
| Average whitespace tokens | 2050.562 |

## Determinism and provenance

- Same-commit runs: 1
- Equivalent: `true`
- Normalized SHA-256: `0978ac074c1afc0c23903f3cc0fb33cb29100aac257c62baf941ae3f2e4d280c`
- Retrieval-result SHA-256: `3154eebce37a04bb5c12dbd4d70e88b9dc185d18bb583fba7b5d757ddb4d8b1d`
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
- latency is environment-dependent

## Decision: `KEEP`
