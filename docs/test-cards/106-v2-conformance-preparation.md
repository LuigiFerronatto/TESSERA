# 106 — Prepare V2 protocol and synthetic adapter checks

| Field | Value |
|---|---|
| Issue | [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) |
| Record status | `IN_PROGRESS` preparation / `BLOCKED` full card |
| Capability type | benchmark |
| Pull request | [Draft PR #323](https://github.com/LuigiFerronatto/TESSERA/pull/323) |
| Head commit | Exact candidate identified by the PR and local manifest |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

Check how invented trajectory evidence crosses the V2 memory boundary without
pretending that a real multimodal benchmark was run.

## What problem existed?

V2 has a distinct multimodal query, context-budget and lifecycle contract;
copying V1's adapter or whitespace token counts would create false compliance.

## How did TESSERA behave before?

Canonical main has V1 retrieval-only evaluation. No V2 adapter or official
V2 result is established. The full #106 card depends on #74/#100/#103/#104/#105.

## What changed or is being tested?

An exact upstream/schema audit and repository-only synthetic adapter prepare
insertion, query isolation, text/source-image context, provenance and budgets.
Production behavior, source ownership, dependencies and quality claims are fixed.

## How does it work now?

TARGET — NOT YET ON MAIN. A fresh temporary TESSERA corpus holds every state of
an invented haystack. Query receives only text/optional synthetic image path.
The image is validated, not interpreted. Whole-item prefix checks use explicitly
synthetic units. Official tokenizer, save/load and real evaluation fail closed.

## Concrete example

Invented source: “The blue toolkit is beside the north door.” A text query can
return that text and its exact original synthetic PNG, linked in an audit to
trajectory `workshop`, original step and stable state/image hashes. A missing
image raises an error. An evaluator's gold answer is never an adapter argument.

## How was it validated?

`tests/test_v2_conformance_preparation.py` exercises positive and negative
boundaries, real unchanged Engine retrieval and byte-repeatable synthetic runs.
Full suite, package build, sanity and exact-head CI/Benchmark Ledger are separate
preservation checks recorded in the PR. Source pins live in
`benchmarks/longmemeval_v2/protocol.json`; local reports never claim an official
pass. See [protocol audit](../../benchmarks/longmemeval_v2/protocol-audit.md).

## What improved?

The proposed boundary is inspectable and independently testable without models,
providers or official content. Unsupported contracts are explicit and cannot
silently degrade to guessed tokenizer/image semantics.

## What remains unimplemented?

Canonical acceptance, official runtime registration, immutable real processor,
general screenshot validation, visual query retrieval, persisted-state contract,
reader/judge selection, cost authorization, small-tier runs/comparisons and all
quality/latency/frontier acceptance remain open. No full conformance is claimed.

## What is unlocked next?

Protocol review only. No dependency state changes. Full #106 remains BLOCKED;
medium additionally needs a separate readiness and approved resource decision.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) |
| Pull request | [Draft PR #323](https://github.com/LuigiFerronatto/TESSERA/pull/323), not merged |
| Merge commit | None |
| Evidence/Learnings/Decision | Protocol audit and synthetic tests; ITERATE |
| Benchmark record | Separate synthetic preparation profile; V1 ledger unchanged |
| PR Evolution Audit | Canonical base `20814a47ec0f72d7bea0639e0b057df1ecf5cded`; unmerged #315/#321 inspected, not imported |

## Evolution

V1 retrieval-only main → isolated V2 preparation candidate → review and canonical
dependency acceptance → separately authorized official V2 conformance/evaluation.
