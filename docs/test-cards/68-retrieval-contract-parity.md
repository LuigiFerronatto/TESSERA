# #68 — The same retrieval result everywhere

| Field | Value |
|---|---|
| Issue | [#68](https://github.com/LuigiFerronatto/TESSERA/issues/68) |
| Record status | `VALIDATED` |
| Capability type | `runtime contract` |
| Pull request | [#98](https://github.com/LuigiFerronatto/TESSERA/pull/98) |
| Merge commit | [`fb23012`](https://github.com/LuigiFerronatto/TESSERA/commit/fb23012ba4b2fddc3912d7cb593391a04fe45ae7) |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

A query now returns the same complete evidence contract whether it enters through Python, CLI JSON or direct MCP retrieval.

## What problem existed?

Different entry points could expose different subsets of the same retrieval result. An agent using MCP or CLI could lose fields that Python received, weakening auditability and making cross-surface tests unfair.

## How did TESSERA behave before?

```text
same query
→ Python: full evidence
→ CLI/MCP: smaller or independently projected result
```

## What changed or is being tested?

PR #98 introduced a shared evidence projection and deterministic parity tests. The CLI gained JSON output and direct MCP retrieval adopted the Engine contract without changing ranking.

## How does it work now?

The Engine remains the semantic source. Python, `tessera query --json` and `mcp_server.query_memories()` expose the same ordered result fields and values.

## Concrete example

If the Engine ranks memories A, B and C with provenance and score explanations, CLI JSON and direct MCP return A, B and C in that order with the same contract fields.

## How was it validated?

Deterministic parity tests compare the integral Engine and MCP results, result ordering and field ordering. Python 3.9/3.12, smoke and sanity CI passed for the delivery.

## What improved?

Transport choice no longer changes the canonical direct-query evidence contract.

## What remains unimplemented?

The typed-store helper `query_store()` still has a smaller hand-projected shape. This card did not change retrieval quality or ranking.

## What is unlocked next?

It provided the frozen cross-surface evidence contract needed by benchmark and renderer cards, including #96 and #28.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#68](https://github.com/LuigiFerronatto/TESSERA/issues/68) |
| Pull request | [#98](https://github.com/LuigiFerronatto/TESSERA/pull/98) |
| Merge commit | [`fb23012`](https://github.com/LuigiFerronatto/TESSERA/commit/fb23012ba4b2fddc3912d7cb593391a04fe45ae7) |
| Evidence/Learnings/Decision | [Issue evidence](https://github.com/LuigiFerronatto/TESSERA/issues/68#issuecomment-5471122707) |
| Benchmark record | Parity fixture and ordinary CI |
| PR Evolution Audit | PR #98 description and issue evidence |

## Evolution

```text
surface-specific projections
→ shared evidence projection
→ lossless Python/CLI/MCP direct-query parity
→ frozen rendering and reader experiments
```
