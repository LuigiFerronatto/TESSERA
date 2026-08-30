# Benchmark ledger and CI

TESSERA separates deterministic retrieval measurement from future reader and
judge evaluation. The versioned ledger contains only compact aggregate evidence;
licensed dataset content and full query-level artifacts remain local or in
short-lived GitHub Actions artifacts.

## Applicability contract

Every pull request contains exactly one line:

```text
Benchmark applicability: REQUIRED
```

The allowed values are `REQUIRED`, `SMOKE_ONLY`, and `NOT_APPLICABLE`.
`REQUIRED` covers changes that may alter retrieval quality or its benchmark.
`SMOKE_ONLY` covers integration contracts that should preserve retrieval.
`NOT_APPLICABLE` covers non-executable documentation/governance/metadata work.
A `Benchmark rationale:` is mandatory for the latter two. Missing, duplicate,
malformed, or unsupported declarations fail with an actionable error.

## CI tiers

Tier 1 runs offline for every pull request. It validates the strict record
schema, canonical JSON/Markdown consistency, deterministic comparison behavior,
synthetic compatibility failures, applicability parsing, and the existing
Python 3.9/3.12, smoke, and sanity gates. It needs no dataset, LLM, secret, or
provider API.

Tier 2 runs the frozen LongMemEval V1 dev-50 profile for `REQUIRED` pull
requests and manual dispatch. It verifies the checksum, executes the candidate
twice from a clean worktree, proves repeatability, reconstructs the canonical
commit in an isolated Git worktree, performs aggregate and query-level
comparison, publishes a concise step summary, and uploads artifacts for 14
days. Experimental incompatibility, nondeterminism, provenance regression,
schema/threshold failure, or data-infrastructure failure fails the job.

Tier 3 runs the same frozen dev-50 drift check on pushes to `main`, weekly at
04:17 UTC on Monday, and manual dispatch. It never mutates the repository and
requires no LLM or API key.

## Frozen data and artifacts

The dataset cache key embeds SHA-256
`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
Both cache restores and official-URL downloads pass through the same verifier.
Network, cache, upstream, and checksum failures are infrastructure failures—not
zero retrieval scores, successful skips, or benchmark passes.

Each candidate run produces the five LongMemEval artifacts plus a compact
candidate ledger record, repeatability evidence, comparison JSON, and comparison
Markdown. Query-level detail is never committed.

## Reproducibility and interpretation

Same-commit runs compare normalized payload hashes after removing only creation
timestamps, latency fields, and absolute temporary paths. Cross-commit runs may
have different provenance hashes, so they compare compatible configuration,
selected-query order, aggregate metrics, and provenance-aware retrieval-result
signatures.

Recall measures expected evidence sessions recovered; it is not answer
accuracy. Abstention retrieval emptiness is diagnostic only. The 50-query slice
is a development gate, not an official full LongMemEval result. A future
full-500 profile must be separately named and stored and may run only manually
or on a schedule. Reader/answer generation, LLM judging, and LongMemEval V2 are
outside this contract.
