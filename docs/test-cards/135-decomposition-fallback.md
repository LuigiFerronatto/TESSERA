# 135 — Deterministic decomposition fallback integrity

| Field | Value |
|---|---|
| Issue | [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | [#216](https://github.com/LuigiFerronatto/TESSERA/pull/216) |
| Head commit | `555a8354343bb8458c6f9650dd349eb28374d2f6` |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-04 |

## In one sentence

When assisted decomposition cannot produce a valid structured result, TESSERA
now proposes memories with its existing repeatable offline heuristic instead
of silently returning nothing, while a valid empty result remains empty.

## What problem existed?

The documented deterministic heuristic existed in `tessera/decomposer.py`, but
the public assisted path never called it after a provider or parsing failure.
Both failure and an intentional `[]` collapsed to the same empty list, so the
runtime could not preserve the documented fallback without also corrupting the
meaning of a valid empty response.

## How did TESSERA behave before?

At audited canonical `main`
`f57727b11977e9ba9619bd2202f5897fb20c334b`:

```text
valid assisted memories -> assisted memories
valid []                 -> []
provider failure         -> []
parse failure            -> []
```

Directly calling `_decompose_via_heuristic()` for the same non-empty episode
returned deterministic candidates, proving the implementation existed but was
unreachable from `decompose_episode()`.

## What changed or is being tested?

The candidate introduces the smallest internal outcome distinction needed to
represent assisted success separately from expected provider, parse and schema
failure. It preserves the existing list-returning Python APIs and supported
JSON wrappers, and adds an opt-in diagnostic result for Engine, CLI and MCP.

## How does it work now? — TARGET, NOT YET ON MAIN

```text
valid non-empty list -> assisted candidates; no fallback
valid []             -> intentional empty result; no fallback
provider exception   -> deterministic fallback
malformed/prose      -> deterministic fallback
wrong root/schema    -> deterministic fallback
programming error    -> propagates
candidate write      -> canonical write gate
```

The fallback performs no provider lookup, retry, model download, embedding,
graph retrieval or direct durable write.

## Concrete example

Given the same episode, a provider timeout previously returned `[]`. The
candidate classifies each non-empty episode line with the local keyword rules
and returns the same ordered candidates on repeated runs. In contrast, a
provider response of exactly `[]` still returns `[]` and records assisted
success.

## How was it validated?

Candidate validation is recorded on [PR #216](https://github.com/LuigiFerronatto/TESSERA/pull/216) and in
[`PR_EVOLUTION_135.md`](../PR_EVOLUTION_135.md). Focused tests separately cover
assisted non-empty output, valid empty output with zero fallback calls,
expected provider exceptions, malformed JSON, unsupported prose, invalid root
and item schemas, programming-error propagation, repeatability, canonical
write-gate rejection, and Engine/CLI/MCP delegation. Exact final Python 3.9,
Python 3.12, smoke, sanity and CI evidence. At candidate
`555a8354343bb8458c6f9650dd349eb28374d2f6`, the focused decomposition/gate
set passed `113` tests and the clean full suite passed on both Python 3.9 and
3.12 (`523 passed, 5 skipped`, with the same 14 expected warnings). Exact final
head smoke, sanity, CI and Maintainer Audit evidence remains pending.

## What improved?

- Expected assisted failures no longer silently discard a usable local result.
- `[]` has one unambiguous meaning: successful extraction with no candidates.
- Diagnostics never label heuristic output as assisted success.
- Fallback candidates retain the same admission and persistence boundary.

## What remains unimplemented?

This card does not change F/P/I meaning or decomposition passes (#136), source
episode lineage/supporting turns/temporal position (#137), dynamic role-aware
episode boundaries (#138), or the QUMem tracker (#145). CLI/MCP backend
selection and broader optional-capability envelopes remain separate work.

## What is unlocked next?

Nothing is declared unlocked until this candidate is canonically merged and
its lifecycle is reconciled. At that point only actual declared blockers for
#136 and #137 should be reassessed; no other QUMem card becomes Ready
automatically.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #135](https://github.com/LuigiFerronatto/TESSERA/issues/135) |
| Pull request | [PR #216](https://github.com/LuigiFerronatto/TESSERA/pull/216) |
| Starting canonical main | `f57727b11977e9ba9619bd2202f5897fb20c334b` |
| Evidence/Learnings/Decision | This record and the implementation PR; `PENDING` |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity required, LongMemEval not required |
| PR Evolution Audit | [`docs/PR_EVOLUTION_135.md`](../PR_EVOLUTION_135.md) |

## Evolution

```text
documented but unreachable heuristic
-> #135 candidate restores the failure edge
-> canonical merge/lifecycle still required
-> reassess only declared #136/#137 blockers
```
