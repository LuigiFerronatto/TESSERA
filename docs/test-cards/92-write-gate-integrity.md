# #92 — Make the memory gate prove what it did

| Field | Value |
|---|---|
| Issue | [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime safety contract` |
| Pull request | [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) |
| Head commit | [`b38ec89`](https://github.com/LuigiFerronatto/TESSERA/commit/b38ec89e66eb5130d45bca8f8146e01181754639) (audited implementation snapshot; live PR head includes evidence-only follow-up) |
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

**CANDIDATE — IN PR #108, NOT YET ON MAIN.**

PR #108 separates path validation, detection, transformation, admission and
persistence. It uses hashes as fingerprints of the exact original and
persistence-candidate text.

## How does it work now?

**CURRENT MAIN (`a0a482c`):** the known inconsistency and unconstrained memory-ID
join still exist.

**PR CANDIDATE:**

```text
validate portable ID and contained destination
→ detect
→ transform only under a complete versioned rule
→ choose accept | accept_sanitized | reject | review
→ persist only after an accepting decision
```

The current evaluator rejects direct known hostile instruction blocks and sends
quoted/documentary or suspicious-tag-only ambiguity to review. It emits no
`accept_sanitized`; the schema permits that state only for a complete bounded
whole-content rule. Reject/review/invalid-path outcomes do not mutate the
canonical corpus, registry, graph, Evidence Ledger or index.

## Concrete example

| Input | Target result |
|---|---|
| Safe fact | Accept unchanged; never call it sanitized |
| Direct known hostile instruction, including multiline payload | Reject; do not persist canonically |
| Quoted security example | Preserve under an explicit policy or review it; do not silently destroy it |
| Absolute/traversal/UNC/symlink-escaping memory ID | Reject before warnings, timestamps or filesystem mutation |

## How was it validated?

The candidate passes focused multilingual/adversarial, path-containment,
hash-invariant, atomic-failure, zero-side-effect and Python/CLI/MCP parity tests.
Final CI evidence remains attached to the open PR and issue; the stage remains
`IN_PROGRESS` until merge.

## What improved?

The open candidate turns path escape and partial-redaction overclaim into
deterministic non-persisting rejection, while preserving safe writes and
same-directory atomic replacement. Nothing is promoted on `main` before merge.

## What remains unimplemented?

General semantic prompt-injection defense, quarantine/review storage, a broadly
safe sanitizer, directory-fsync crash durability, State Contamination
evaluation, #95 project-agnostic runtime cleanup and #67 Quality Gate
integration remain unimplemented.

## What is unlocked next?

No capability is unlocked until the implementation is merged and validated. After that, #92 will satisfy one dependency of #67 and #19; their other dependencies remain.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| Pull request | [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Candidate evidence in PR #108 and issue #92; final merge lifecycle pending |
| Benchmark record | LongMemEval not applicable; smoke/sanity required |
| PR Evolution Audit | [Current deduplicated audit](../PR_EVOLUTION_92.md) |

## Evolution

```text
truthful Markdown format gate (#94)
→ known sanitizer-status and path-containment defects (#92)
→ path-contained conservative detect/transform/admit/persist candidate (PR #108)
→ later State Contamination experiment
```
