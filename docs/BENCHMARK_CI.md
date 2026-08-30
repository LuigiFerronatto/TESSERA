# Benchmark ledger and CI

TESSERA separates deterministic retrieval measurement from future reader and
judge evaluation. The versioned ledger contains only compact aggregate evidence;
licensed dataset content and full query-level artifacts remain local or in
short-lived GitHub Actions artifacts.

## Applicability contract

Every pull request contains exactly one line:

```text
Benchmark applicability: REQUIRED
Benchmark issue: #123
```

The allowed values are `REQUIRED`, `SMOKE_ONLY`, and `NOT_APPLICABLE`.
`REQUIRED` covers changes that may alter retrieval quality or its benchmark.
`SMOKE_ONLY` covers integration contracts that should preserve retrieval.
`NOT_APPLICABLE` covers non-executable documentation/governance/metadata work.
A `Benchmark rationale:` is mandatory for the latter two. Missing, duplicate,
malformed, or unsupported declarations fail with an actionable error. A
`REQUIRED` declaration must include exactly one numeric `Benchmark issue`; this
validated Test Card number and the actual PR number are written into the run
record rather than inferred from prose.

## CI tiers

Tier 1 runs offline for every pull request. It validates the strict record
schema, canonical JSON/Markdown consistency, deterministic comparison behavior,
synthetic compatibility failures, applicability parsing, and the existing
Python 3.9/3.12, smoke, and sanity gates. It needs no dataset, LLM, secret, or
provider API.

Tier 2 runs the frozen LongMemEval V1 dev-50 profile for `REQUIRED` pull
requests and manual dispatch. It verifies the checksum, executes the candidate
twice from a clean worktree, and reconstructs both the exact PR base SHA and the
historical #96 commit in isolated Git worktrees. Candidate-versus-immediate-
parent is the primary merge gate. Candidate-versus-#96 is a distinct
longitudinal report. The two comparisons have separate JSON and Markdown files.
Experimental incompatibility, nondeterminism, parent regression, provenance
regression, schema/threshold failure, environment drift, or data-infrastructure
failure fails the relevant gate.

Tier 3 runs the same frozen dev-50 drift check on pushes to `main`, weekly at
04:17 UTC on Monday, and manual dispatch. It never mutates the repository and
requires no LLM or API key. A push uses `github.event.before` as its immediate
parent. Scheduled/manual runs use the measured commit in the versioned forward
reference. Non-PR records use issue/PR zero plus an explicit event, run,
attempt, and measured-commit identity; they never pretend to belong to a Test
Card.

## Frozen data and artifacts

The dataset cache key embeds SHA-256
`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
Both cache restores and official-URL downloads pass through the same verifier.
Network, cache, upstream, and checksum failures are infrastructure failures—not
zero retrieval scores, successful skips, or benchmark passes.

Each candidate run produces the five LongMemEval artifacts plus candidate and
parent ledger records, repeatability evidence, environment evidence, and
separate parent/canonical comparison JSON and Markdown. Query-level detail is
never committed.

## Reproducibility and interpretation

The dev-50 job uses Python 3.12.14 and the versioned
`benchmarks/longmemeval_v1/constraints-ci.txt`. Every new record captures the
Python implementation/full version, OS/platform/architecture, NumPy, SciPy,
scikit-learn, NetworkX and PyYAML versions, measured commit, constraints hash,
and normalized environment fingerprint. The fingerprint is checked against the
versioned forward CI reference, so dependency or runner drift cannot disappear
merely because candidate and comparison worktrees share one runner.

Same-commit runs compare normalized payload hashes after removing only creation
timestamps, latency fields, and absolute temporary paths. Cross-commit runs may
have different provenance hashes, so they compare compatible configuration,
selected-query order, aggregate metrics, and provenance-aware retrieval-result
signatures. For query-level isolation, CI reruns the frozen baseline commit in
the candidate environment. Drift between that reconstruction and the historical
record is reported separately because #96 did not record a fully pinned package
and platform environment; it is not silently attributed to candidate code. The
original #96 record and metrics remain unchanged and explicitly
environment-incomplete.

Recall measures expected evidence sessions recovered; it is not answer
accuracy. Abstention retrieval emptiness is diagnostic only. The 50-query slice
is a development gate, not an official full LongMemEval result. A future
full-500 profile must be separately named and stored and may run only manually
or on a schedule. Reader/answer generation, LLM judging, and LongMemEval V2 are
outside this contract.
