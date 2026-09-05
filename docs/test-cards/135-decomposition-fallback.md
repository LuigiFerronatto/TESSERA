# 135 — Deterministic decomposition fallback integrity

| Field | Value |
|---|---|
| Issue | [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [#216](https://github.com/LuigiFerronatto/TESSERA/pull/216) |
| Head commit | `2bc281760dedbe71cfeca5b8a16296de29260980` |
| Merge commit | `c324ac2f46d48f7b49769b2fea9df0a2a93b42de` |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-05 |

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

## How does it work now? — ON MAIN

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

Validation is recorded on merged [PR #216](https://github.com/LuigiFerronatto/TESSERA/pull/216) and in
[`PR_EVOLUTION_135.md`](../PR_EVOLUTION_135.md). Focused tests separately cover
assisted non-empty output, valid empty output with zero fallback calls,
expected provider exceptions, malformed JSON, unsupported prose, invalid root
and item schemas, programming-error propagation, repeatability, canonical
write-gate rejection, and Engine/CLI/MCP delegation. At final head
`2bc281760dedbe71cfeca5b8a16296de29260980`, the focused decomposition/gate
set passed `113` tests and the clean full suite passed on both Python 3.9 and
3.12 (`523 passed, 5 skipped`, with the same 14 expected warnings). Exact-head
CI run `33905362165` and Benchmark Ledger run `33905362230` both succeeded;
the change merged to `main` as `c324ac2f46d48f7b49769b2fea9df0a2a93b42de` with
decision `KEEP`.

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

Now that this change is canonically merged and reconciled, #136 and #137 have
their declared #135 blocker satisfied. #136's other declared dependency, #74,
is already `VALIDATED`, so #136 is `READY`; #137 declares no other hard
blocker, so it is also `READY`. They retain their existing queue positions and
do not move ahead of #16. No other QUMem card becomes Ready automatically.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #135](https://github.com/LuigiFerronatto/TESSERA/issues/135) |
| Pull request | [PR #216](https://github.com/LuigiFerronatto/TESSERA/pull/216) |
| Starting canonical main | `f57727b11977e9ba9619bd2202f5897fb20c334b` |
| Evidence/Learnings/Decision | This record and the implementation PR; `KEEP` |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity required, LongMemEval not required |
| PR Evolution Audit | [`docs/PR_EVOLUTION_135.md`](../PR_EVOLUTION_135.md) |

## Evolution

```text
documented but unreachable heuristic
-> #135 candidate restores the failure edge
-> canonically merged `c324ac2f46d48f7b49769b2fea9df0a2a93b42de`, decision KEEP
-> reassess only declared #136/#137 blockers
```
