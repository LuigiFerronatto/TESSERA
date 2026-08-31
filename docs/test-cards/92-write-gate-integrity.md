# #92 — Make the memory gate prove what it did

| Field | Value |
|---|---|
| Issue | [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| Record status | `PLANNED` |
| Capability type | `runtime safety contract` |
| Pull request | Not started |
| Head commit | Not applicable |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA must not say “I removed the dangerous instruction” unless the text it will save is demonstrably different and safe under its deterministic rules.

## What problem existed?

The current write gate can report that safe text was sanitized without changing it. It can also detect a hostile English instruction without neutralizing it, while persistence metadata still sounds stronger than the real protection.

Colloquially, the gate can claim that it removed a dangerous item from a bag even though the item is still inside.

## How did TESSERA behave before?

```text
detect suspicious text
→ sanitization flag may become true
→ persistence candidate may remain identical
→ audit metadata overclaims protection
```

## What changed or is being tested?

**TARGET — NOT YET ON MAIN.**

Issue #92 will separate detection, transformation, admission and persistence. It will use hashes as fingerprints of the exact original and persistence-candidate text.

## How does it work now?

**CURRENT MAIN:** the known inconsistency still exists. This page documents the planned correction; it does not claim that the fix is implemented.

**TARGET:**

```text
detect
→ transform when deterministic and safe
→ choose accept | accept_sanitized | reject | review
→ persist only after an accepting decision
```

`accept_sanitized` will require different original and persisted hashes. Reject/review paths must not mutate the canonical corpus, registry, graph, Evidence Ledger or index.

## Concrete example

| Input | Target result |
|---|---|
| Safe fact | Accept unchanged; never call it sanitized |
| Transformable hostile instruction | Persist only the demonstrably changed candidate |
| Non-transformable hostile instruction | Reject or review; do not persist canonically |
| Quoted security example | Preserve under an explicit policy or review it; do not silently destroy it |

## How was it validated?

Not yet validated. The issue contains the reproduced baseline and required multilingual, hash-consistency, side-effect and cross-surface tests. Evidence belongs here only after an implementation PR runs them.

## What improved?

Nothing on `main` yet. The Test Card makes the inconsistency explicit and decisionable.

## What remains unimplemented?

The truthful result contract, deterministic transformation/reject/review behavior, mutation-boundary proof and Python/CLI/MCP parity still need implementation. General semantic prompt-injection defense and State Contamination evaluation remain out of scope.

## What is unlocked next?

No capability is unlocked until the implementation is merged and validated. After that, #92 will satisfy one dependency of #67 and #19; their other dependencies remain.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| Pull request | Not started |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Pending |
| Benchmark record | LongMemEval not applicable; smoke/sanity required |
| PR Evolution Audit | Required in the future implementation PR |

## Evolution

```text
truthful Markdown format gate (#94)
→ known sanitizer-status inconsistency (#92)
→ planned detect/transform/admit/persist contract
→ later State Contamination experiment
```
