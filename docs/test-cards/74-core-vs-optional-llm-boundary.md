# #74 — Where TESSERA ends and agent reasoning begins

| Field | Value |
|---|---|
| Issue | [#74](https://github.com/LuigiFerronatto/TESSERA/issues/74) |
| Record status | `VALIDATED` architecture decision |
| Capability type | `architecture decision` |
| Pull request | [#107](https://github.com/LuigiFerronatto/TESSERA/pull/107) |
| Merge commit | [`0c0b638`](https://github.com/LuigiFerronatto/TESSERA/commit/0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2) |
| Decision | `KEEP` |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA's deterministic core finds and explains evidence; optional adapters may transform it, but the consuming agent owns the final answer and decision.

## What problem existed?

The repository had both deterministic retrieval and a legacy LLM orchestrator. Without a boundary, users could mistake LLM-generated synthesis for source evidence or assume a provider was mandatory.

## How did TESSERA behave before?

The direct path already returned deterministic structured evidence. The assisted path performed LLM need analysis, planning and synthesis, with implicit provider probing and incomplete generated-output metadata.

## What changed or is being tested?

ADR 0001 assigned responsibilities to the deterministic core, optional adapters, consuming agents and benchmark infrastructure. PR #107 corrected documentation and recorded legacy deviations; it changed no runtime.

## How does it work now?

Current direct retrieval is O0-style deterministic evidence. O1–O4 are explicit target modes, not completed features. Generated text must remain derived and original evidence must remain inspectable.

## Concrete example

TESSERA may return three sourced memories. A reader may use them to draft an answer, but that answer is not reclassified as source evidence and TESSERA does not silently own the final abstention policy.

## How was it validated?

The documentation-contract suite, Python 3.9/3.12, smoke, sanity and benchmark-applicability checks passed. The runtime diff under `tessera/` was empty.

## What improved?

The product boundary, dependency direction, failure semantics, provenance invariants and judge boundary are now binding and auditable.

## What remains unimplemented?

Deterministic MCP startup, explicit adapter interfaces, derived-output envelopes and contract-compliant O1–O4 modes remain follow-up work.

## What is unlocked next?

The architecture decision prerequisite for optional adapter, planner, reader, judge and abstention experiments is closed. Their other routed dependencies still apply.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#74](https://github.com/LuigiFerronatto/TESSERA/issues/74) |
| Pull request | [#107](https://github.com/LuigiFerronatto/TESSERA/pull/107) |
| Merge commit | [`0c0b638`](https://github.com/LuigiFerronatto/TESSERA/commit/0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2) |
| Evidence/Learnings/Decision | [Issue evidence](https://github.com/LuigiFerronatto/TESSERA/issues/74#issuecomment-5472168701) |
| Benchmark record | Not applicable; documentation/contract only |
| PR Evolution Audit | PR #107 description |
| ADR | [ADR 0001](../adr/0001-core-vs-optional-llm-boundary.md) |

## Evolution

```text
deterministic retrieval plus ambiguous assisted path
→ accepted responsibility boundary
→ runtime remains unchanged but constrained
→ explicit adapters and O1–O4 ablations
```
