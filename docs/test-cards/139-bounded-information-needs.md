# #139 — Identify bounded historical evidence needs before searching

| Field | Value |
|---|---|
| Issue | [#139](https://github.com/LuigiFerronatto/TESSERA/issues/139) |
| Record status | `IN_PROGRESS` |
| Capability type | Experimental assisted runtime and evaluation |
| Pull request | Draft candidate on `codex/issue-139-bounded-information-needs` |
| Head commit | Exact candidate recorded in the pull request and CI |
| Merge commit | Not merged |
| Decision | `ITERATE`; keep N0 default; full N2 quality decision blocked |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

An optional assistant can name a few distinct pieces of historical evidence it
needs before searching, or explicitly say that history is unnecessary.

## What problem existed?

Consumers lacked an inspectable, bounded contract for distinct evidence needs.

## How did TESSERA behave before?

The existing orchestrator compressed the task to one free-text sentence. It had
no validated multi-facet contract and no explicit empty no-memory decision.
Consumers had to invent missing search facets or infer intent from the string.

## What changed or is being tested?

An opt-in structured contract is under test.

## How does it work now?

TARGET — NOT YET ON MAIN

N0 remains the default. N1 returns one structured need; N2 allows up to four.
Each need has an ID, evidence description and purpose. Strict validation stops
bad output before retrieval. No-memory and ambiguous tasks can return empty
needs and skip all downstream work. The original structured plan is inspectable.
The existing single-query planner consumes a compatibility projection; there is
no per-need query fanout, state reconstruction or context-packet implementation.

## Concrete example

For “How did the report format preference change, and why?”, the provider can
request earlier preferences, later preferences and explaining feedback as
separate needs. It must not invent what either preference was. For “2 plus 2”,
it can return `no_memory_needed` and `needs: []`, without opening memory stores.
These examples illustrate the contract, not an observed model-quality result.

## How was it validated?

- `tests/test_information_needs.py`: strict schema, IDs, cardinality, input/output
  limits, lexical duplicate rejection, one-call failures, explicit empty early
  exits, N0 serialization/call compatibility and provider-free direct retrieval
- `tests/test_information_needs_experiment.py`: repeatable six-scenario mechanics,
  exact prompt/corpus replay binding, bounded adapter capture, invalid-usage
  rejection, missing review rejection, and null metric denominators
- [Recorded offline mechanics](../../benchmarks/information_needs/mechanics.json):
  six runs per variant, zero schema failures, 18 N0 callable invocations versus
  14 N1 and 14 N2; N1 counts `1/1/1/0/0/1`, N2 counts `1/3/3/0/0/3`
- All those generation replies are **test doubles**. Reduced calls reflect the
  empty-branch contract, not empirical accuracy or real-world cost savings
- Exact-head CI and REQUIRED dev-50 validate deterministic-default compatibility;
  they are recorded in the PR and do not establish assisted quality gains

## What improved?

Deterministic tests establish bounded outputs, explicit empty outcomes, preserved
N0 behavior and replayable measurements. No empirical quality gains are claimed.

## What remains unimplemented?

No provider calls were made and no models were downloaded. The six scenarios'
expected facets are proposed, not independently reviewed. Provider-backed
semantic deduplication, need coverage, unsupported-need rate, evidence recall,
state accuracy and consumer-effort gains remain unestablished. Literal duplicate
rejection is not semantic deduplication. Provider token/time/spend enforcement
remains the application's responsibility. Full adoption stays blocked pending
the [exact capture/review inputs](../../benchmarks/information_needs/README.md).

## What is unlocked next?

Nothing is treated as canonically unlocked before merge and the quality decision.
#140 owns multi-query/store planning; #141 owns structured state. #169 consumes
these future capabilities. #157 model profiles is not a dependency of this PR.

## Technical provenance

- Baseline main: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- #74 architecture boundary: [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107),
  merge `0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2`; documentation decision
- Explicit generic provider isolation: [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126),
  merge `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`; N0 retained
- This candidate adds optional structured needs and an honest blocked empirical
  gate; it does not replace either canonical delivery
- [Runtime contract](../INFORMATION_NEEDS.md) and
  [experiment protocol](../../benchmarks/information_needs/README.md)
- Post-merge: record canonical SHA, independent decision and benchmark evidence,
  then reconcile issue/roadmap/dependencies; do not close #139 on mocks alone

## Evolution

One free-text need → optional bounded structured candidate → provider/reviewer
quality gate → canonical decision, with multi-query planning still owned by #140.
