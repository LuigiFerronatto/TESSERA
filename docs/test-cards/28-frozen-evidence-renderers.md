# #28 — Separate evidence presentation from retrieval quality

| Field | Value |
|---|---|
| Issue | [#28](https://github.com/LuigiFerronatto/TESSERA/issues/28) |
| Record status | `IN_PROGRESS` |
| Capability type | `benchmark infrastructure` |
| Pull request | Draft candidate; see issue-linked PR |
| Head commit | Exact source revision recorded by each replay manifest and PR head |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

## In one sentence

This candidate lets researchers hold retrieved evidence fixed while measuring
what raw, evidence-first, and structured presentation retain under one budget.

## What problem existed?

A different-looking response could be credited to better retrieval even when
only its presentation changed. The canonical retrieval benchmark did not store
complete renderable evidence or isolate downstream reader inputs.

## How did TESSERA behave before?

The current Engine already returns full memory, selected evidence and provenance.
The #96/#100 dev-50 ledger measures retrieval independently, and remains
retrieval-only. There was no dedicated frozen renderer replay contract.

## What changed or is being tested?

The isolated `benchmarks/rendering/` candidate captures label-free raw Engine hits
once. It freezes query text/IDs, result order/scores, evidence/provenance and full
body hashes, then constructs R0/R1/R2 with one fixed reader-input and truncation
policy. No runtime files, defaults, existing benchmarks or ranking change.

## How does it work now?

**TARGET — NOT YET ON MAIN.** R0 shows complete raw bodies; R1 shows selected
spans and provenance; R2 adds existing direct relations and full-memory
references. Missing spans fall back to explicitly marked raw bodies. Source
identity aliases retain a local audit mapping without leaking benchmark IDs
or abstention suffixes into reader messages. The budget counts whitespace units,
not actual provider tokens. No reader or judge is called.

## Concrete example

An invented toolkit location appears after 480 filler words. At a 180-unit
per-query budget, R0 retains none of its selected evidence; R1/R2 retain all
19 selected-span words across two memories. R1/R2 also lose two of five complete
provenance records at that tight budget. At 512 units, both retain all five;
R2 consumes 29 more context units than R1 over the three-query fixture.
These are deliberate fixture mechanics, not measured answer-quality gains.

## How was it validated?

- `tests/test_renderer_ablation.py`: 67 passing focused synthetic and real-Engine capture
  controls, deterministic replay, fixed budgets, provenance/retention metrics,
  identity masking, malformed/duplicate/label rejection, and zero-network replay
- `tests/test_benchmark_reporting.py`: 51 passing unchanged closed ledger/CI contracts
- Full repository suite: 629 passed, 8 skipped (5 unavailable governance CLI,
  3 optional MCP transport), 14 existing warnings; offline sanity Hit@1 0.75,
  Hit@3/5 1.0, MRR 0.875, evidence hit rate 1.0, missing-evidence check passed
- Wheel/sdist build and installed-wheel import/CLI smoke passed; the repository-
  only rendering package is absent from both distribution artifacts
- Two clean same-head runs must produce byte-identical manifest/input/summary
  artifacts; exact renderer commit and environment are recorded in the manifest

The [reproduction guide](../../benchmarks/rendering/README.md) describes exact
commands, policies and denominators. Large/source-bearing artifacts remain
outside Git. The PR records the actual checks, counts, hashes and any failures.

## What improved?

The candidate makes presentation-only experiments repeatable and auditable,
including overhead and lost provenance. It does not establish a preferred
renderer, QA/abstention improvement, or a new product capability.

## What remains unimplemented?

Pinned provider/model/tokenizer/decoding settings; authorized cost/attempt caps;
DEV and disjoint held-out reader runs; model repeatability, latency and quality
metrics; independently scored or calibrated verdicts; fair external-system
controls. Null QA metrics mean `NOT_RUN`, never zero accuracy or a passing gate.
No credentials were tested and no provider availability claim is made.

## What is unlocked next?

The offline candidate can be reviewed now. No dependency status changes merely
because the PR exists: #103 still requires accepted #28/#74/#96/#100, #104 still
requires #103, and #105 still requires #103/#104. #28's empirical criterion and
the staged reader dependency need maintainer reconciliation before final KEEP.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Canonical base | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Retrieval parity | [#68 / PR #98](68-retrieval-contract-parity.md) |
| Historical dev-50 | [#96 / PR #99](96-longmemeval-v1-dev-50.md) |
| Ledger contract | [#100 / PR #102](100-benchmark-ledger-and-ci.md), [Benchmark CI](../BENCHMARK_CI.md) |
| Offline contract | [Renderer guide](../../benchmarks/rendering/README.md) |
| Draft future experiment | [Preregistration](../../benchmarks/rendering/preregistration.json) |
| Evidence/Learnings/Decision | This candidate PR, linked from #28; `ITERATE` |

## Evolution

```text
current structured retrieval and retrieval-only ledger
→ isolated offline capture/replay candidate
→ accepted frozen interface and pinned reader experiment
→ measured DEV/held-out renderer decision, still pending
```
