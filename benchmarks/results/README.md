# Versioned benchmark ledger

This directory stores compact, non-sensitive benchmark records. JSON is the
source of truth; Markdown is generated deterministically and validated in CI.
Datasets, questions, expected answers, ground-truth mappings, full result
bundles, indices, and model outputs are never versioned here.

## Canonical profile

`longmemeval-v1-dev-50` is the frozen LongMemEval V1 retrieval-only development
profile: 50 deterministic questions, session granularity, Top-K 10, no reader,
no judge, and zero API/LLM calls. The canonical record is
`longmemeval-v1-dev-50/baseline.json` and validates against schema version
`1.0.0` in `schema.json`.

## Compare locally

```bash
python -m benchmarks.reporting.compare \
  --baseline benchmarks/results/longmemeval-v1-dev-50/baseline.json \
  --candidate artifacts/benchmark-reporting/candidate.json \
  --output-json artifacts/benchmark-reporting/comparison.json \
  --output-md artifacts/benchmark-reporting/comparison.md
```

The candidate may be a ledger JSON record or a complete LongMemEval artifact
directory. Add `--baseline-artifacts` and `--candidate-artifacts` to produce
query-level deltas when both compatible full bundles are available locally.
Query-level reports remain ignored local/CI artifacts.

## Comparison rules

Experimental configuration, dataset checksum/revision, selected-query-order
checksum, Top-K, granularity, reader/judge, retrieval configuration, metric
definitions, token counting, and adapter version must match exactly. Errors name
the incompatible field. Same-commit repeatability compares normalized hashes;
cross-commit evaluation compares compatible metrics and the retrieval-result
signature because Git provenance legitimately changes the normalized payload.

Recall@K measures expected evidence sessions recovered, not answer accuracy.
Evidence hit rate measures positive questions with at least one expected session
in Top-K. Abstention retrieval empty rate is informational and is not correct
answer-stage abstention. Reader and LLM-judge evaluation remain separate future
layers. LongMemEval V2 is out of scope.

## CI and data policy

Tier 1 validates reporting, schema, baseline rendering, applicability, smoke,
and sanity offline on every PR. Tier 2 runs dev-50 twice only for `REQUIRED`
PRs or manual dispatch. Tier 3 runs dev-50 on main and weekly drift detection.
The dataset cache key is checksum-pinned; cache restores and downloads are always
verified. Network/cache/upstream failures are infrastructure failures, never
retrieval scores or successful skips. CI artifacts are retained for 14 days.

Full-500 runs are future manual/scheduled profiles with separate records. They
must never overwrite dev-50 and still must not add a reader or judge implicitly.
