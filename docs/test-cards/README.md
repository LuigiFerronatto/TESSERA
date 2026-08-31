# TESSERA Plain-Language Test Card Records

These pages explain project evolution for readers who should not need to reverse-engineer issues, diffs or benchmark artifacts.

They do not replace the technical record. Every page links back to the Issue/Test Card, pull request, merge commit, Evidence/Learnings/Decision and applicable benchmark record.

## How to read status

| Record status | Meaning |
|---|---|
| `PLANNED` | The problem and experiment are defined, but implementation has not started. |
| `IN_PROGRESS` | An implementation pull request is open. |
| `IMPLEMENTED` | The relevant change is merged on `main`. |
| `VALIDATED` | The merged change also passed its required tests or benchmark. |
| `BLOCKED` | A declared dependency or decision is unresolved. |
| `SUPERSEDED` | A newer card or delivery replaced the record. |

An open PR is never described as an implemented or validated capability.

## The explanation contract

Every record answers the same questions:

1. What problem existed?
2. How did TESSERA behave before?
3. What changed or is being tested?
4. How does it work now?
5. What is a concrete example?
6. How was it validated?
7. What improved?
8. What remains unimplemented?
9. What work is unlocked next?
10. Where are the technical evidence and decisions?

Start new pages from [TEMPLATE.md](TEMPLATE.md).

## Current records

| Stage | Status | Plain-language record | Technical evidence |
|---|---|---|---|
| #68 Engine/CLI/MCP retrieval parity | `VALIDATED` | [68-retrieval-contract-parity.md](68-retrieval-contract-parity.md) | [Issue #68](https://github.com/LuigiFerronatto/TESSERA/issues/68), [PR #98](https://github.com/LuigiFerronatto/TESSERA/pull/98) |
| #74 Core vs optional LLM boundary | `VALIDATED` architecture decision | [74-core-vs-optional-llm-boundary.md](74-core-vs-optional-llm-boundary.md) | [Issue #74](https://github.com/LuigiFerronatto/TESSERA/issues/74), [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107), [ADR 0001](../adr/0001-core-vs-optional-llm-boundary.md) |
| #94 Markdown-only persistence | `VALIDATED` | [94-markdown-only-persistence.md](94-markdown-only-persistence.md) | [Issue #94](https://github.com/LuigiFerronatto/TESSERA/issues/94), [PR #101](https://github.com/LuigiFerronatto/TESSERA/pull/101) |
| #96 LongMemEval V1 dev-50 baseline | `VALIDATED` | [96-longmemeval-v1-dev-50.md](96-longmemeval-v1-dev-50.md) | [Issue #96](https://github.com/LuigiFerronatto/TESSERA/issues/96), [PR #99](https://github.com/LuigiFerronatto/TESSERA/pull/99) |
| #100 Benchmark ledger and CI | `VALIDATED` | [100-benchmark-ledger-and-ci.md](100-benchmark-ledger-and-ci.md) | [Issue #100](https://github.com/LuigiFerronatto/TESSERA/issues/100), [PR #102](https://github.com/LuigiFerronatto/TESSERA/pull/102) |
| #92 Truthful write gate | `PLANNED` | [92-write-gate-integrity.md](92-write-gate-integrity.md) | [Issue #92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| #109 Plain-language stage-record system | `IMPLEMENTED` | This index and [TEMPLATE.md](TEMPLATE.md) | [Issue #109](https://github.com/LuigiFerronatto/TESSERA/issues/109), [PR #110](https://github.com/LuigiFerronatto/TESSERA/pull/110) |
| #112 TESSERA ASCII banner | `VALIDATED` | [112-tessera-ascii-banner.md](112-tessera-ascii-banner.md) | [Issue #112](https://github.com/LuigiFerronatto/TESSERA/issues/112), [PR #113](https://github.com/LuigiFerronatto/TESSERA/pull/113) |
| #114 Evolution-auditable templates | `IN_PROGRESS` | [114-evolution-auditable-templates.md](114-evolution-auditable-templates.md) | [Issue #114](https://github.com/LuigiFerronatto/TESSERA/issues/114) |

## Stage map

The [roadmap](../ROADMAP.md) remains the sequencing source of truth. This directory is the explanation layer.

| Roadmap phase | Purpose in plain language | Next records |
|---|---|---|
| M0 — Contract & Safety | Make TESSERA honest, consistent and safe before adding intelligence. | #92, #93, #95, #16 containment, #67 |
| M1 — Measurement Spine | Prove what retrieval, rendering, readers and judges each contribute. | #28, #103, #104, #105, #106 |
| M2 — Corpus Lifecycle | Update and inspect the memory corpus without rebuilding blindly. | #12, #69, #70, #13, #73 |
| M3 — Graph Quality | Expand relations only when evidence shows value. | #25, #26 |
| M4 — State & Arbitration | Represent time, authority, conflict and sufficiency explicitly. | #15, #71, #32, #72, #16, #27, #20 |
| M5 — Admission & Learning | Decide what becomes memory and learn from measured utility. | #19, #17, #21 |

## Lifecycle

- When a Test Card is opened, create a `PLANNED` record.
- When its PR opens, update it to `IN_PROGRESS` and link the head commit.
- Before merge, include before/after evidence and limitations.
- After merge, record the canonical merge commit and only then use `IMPLEMENTED`.
- Use `VALIDATED` only after required CI or benchmark evidence exists.
- If a later card replaces it, preserve the page and mark it `SUPERSEDED`.
