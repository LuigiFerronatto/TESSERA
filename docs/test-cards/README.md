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
| #92 Truthful write gate | `VALIDATED` | [92-write-gate-integrity.md](92-write-gate-integrity.md) | [Issue #92](https://github.com/LuigiFerronatto/TESSERA/issues/92), [PR #108](https://github.com/LuigiFerronatto/TESSERA/pull/108), [merge `9ab03f7`](https://github.com/LuigiFerronatto/TESSERA/commit/9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05), [KEEP evidence](https://github.com/LuigiFerronatto/TESSERA/issues/92#issuecomment-5479001151) |
| #93 Storage configuration parity | `VALIDATED` | [93-storage-configuration-parity.md](93-storage-configuration-parity.md) | [Issue #93](https://github.com/LuigiFerronatto/TESSERA/issues/93), [PR #129](https://github.com/LuigiFerronatto/TESSERA/pull/129), [canonical merge `c612454`](https://github.com/LuigiFerronatto/TESSERA/commit/c6124548f32b6dc5e1b7acf5127632bc6c75fccc), [KEEP evidence](https://github.com/LuigiFerronatto/TESSERA/issues/93#issuecomment-5483152212), [PR Evolution Audit](../PR_EVOLUTION_93.md) |
| #109 Plain-language stage-record system | `IMPLEMENTED` | This index and [TEMPLATE.md](TEMPLATE.md) | [Issue #109](https://github.com/LuigiFerronatto/TESSERA/issues/109), [PR #110](https://github.com/LuigiFerronatto/TESSERA/pull/110) |
| #112 TESSERA ASCII banner | `VALIDATED` | [112-tessera-ascii-banner.md](112-tessera-ascii-banner.md) | [Issue #112](https://github.com/LuigiFerronatto/TESSERA/issues/112), [PR #113](https://github.com/LuigiFerronatto/TESSERA/pull/113) |
| #114 Evolution-auditable templates | `VALIDATED` | [114-evolution-auditable-templates.md](114-evolution-auditable-templates.md) | [Issue #114](https://github.com/LuigiFerronatto/TESSERA/issues/114), [PR #123](https://github.com/LuigiFerronatto/TESSERA/pull/123) |
| #115 Repository layout architecture | `VALIDATED` | [115-repository-layout-architecture.md](115-repository-layout-architecture.md) | [Issue #115](https://github.com/LuigiFerronatto/TESSERA/issues/115), [PR #128](https://github.com/LuigiFerronatto/TESSERA/pull/128), [canonical squash merge `b475f1c`](https://github.com/LuigiFerronatto/TESSERA/commit/b475f1cd805f86cc8ad9526e563e3c6fb8409ff1), `KEEP` |
| #116 Distribution artifact hardening | `VALIDATED` | [116-packaging-hardening.md](116-packaging-hardening.md) | [Issue #116](https://github.com/LuigiFerronatto/TESSERA/issues/116), [PR #131](https://github.com/LuigiFerronatto/TESSERA/pull/131), [canonical squash merge `0dd6e5c`](https://github.com/LuigiFerronatto/TESSERA/commit/0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4), `KEEP` |
| #117 Project/global configuration and init | `VALIDATED` | [117-configuration-init-discovery.md](117-configuration-init-discovery.md) | [Issue #117](https://github.com/LuigiFerronatto/TESSERA/issues/117), [PR #150](https://github.com/LuigiFerronatto/TESSERA/pull/150), [canonical squash merge `61cf76f`](https://github.com/LuigiFerronatto/TESSERA/commit/61cf76fbd6ed61972f0f5abae515ba9bffca4b55), [ADR 0003](../adr/0003-configuration-and-store-discovery.md), [PR Evolution Audit](../PR_EVOLUTION_117.md), `KEEP` |
| #153 Configuration v2 store/source/index boundaries | `VALIDATED` | [153-configuration-v2-store-sources-index.md](153-configuration-v2-store-sources-index.md) | [Issue #153](https://github.com/LuigiFerronatto/TESSERA/issues/153), [PR #173](https://github.com/LuigiFerronatto/TESSERA/pull/173), canonical squash merge `2508676d472088733702b6ed920fc829df9a7681`, [PR Evolution Audit](../PR_EVOLUTION_153.md), `KEEP` |
| #154 Safe project source discovery | `VALIDATED` | [154-safe-source-discovery.md](154-safe-source-discovery.md) | [Issue #154](https://github.com/LuigiFerronatto/TESSERA/issues/154), [PR #175](https://github.com/LuigiFerronatto/TESSERA/pull/175), canonical squash merge `05ce0dd234a7756d4a5ba315b77e4a6ec33c9429`, [ADR 0004](../adr/0004-safe-project-source-discovery.md), [PR Evolution Audit](../PR_EVOLUTION_154.md), `KEEP` |
| #155 Initialization UX and source selection | `VALIDATED` | [155-init-ux.md](155-init-ux.md) | [Issue #155](https://github.com/LuigiFerronatto/TESSERA/issues/155), [PR #210](https://github.com/LuigiFerronatto/TESSERA/pull/210), canonical merge `4c112195f1572bf352d1cc6a1042c69711381da8`, `KEEP` |
| #135 Deterministic decomposition fallback | `VALIDATED` | [135-decomposition-fallback.md](135-decomposition-fallback.md) | [Issue #135](https://github.com/LuigiFerronatto/TESSERA/issues/135), [PR #216](https://github.com/LuigiFerronatto/TESSERA/pull/216), canonical merge `c324ac2f46d48f7b49769b2fea9df0a2a93b42de`, `KEEP`, [PR Evolution Audit](../PR_EVOLUTION_135.md) |
| #16 Non-destructive conflict containment | `IN_PROGRESS` P0 / `BLOCKED` full | [16-conflict-resolver-containment.md](16-conflict-resolver-containment.md) | [Issue #16](https://github.com/LuigiFerronatto/TESSERA/issues/16), implementation PR pending, [PR Evolution Audit](../PR_EVOLUTION_16.md) |
| #95 Generic runtime / explicit legacy compatibility | `VALIDATED` | [95-remove-legacy-runtime-coupling.md](95-remove-legacy-runtime-coupling.md) | [Issue #95](https://github.com/LuigiFerronatto/TESSERA/issues/95), [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126), [canonical merge `6d4a32b`](https://github.com/LuigiFerronatto/TESSERA/commit/6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599), [KEEP evidence](https://github.com/LuigiFerronatto/TESSERA/issues/95#issuecomment-5480777109), [PR Evolution Audit](../PR_EVOLUTION_95.md) |

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
