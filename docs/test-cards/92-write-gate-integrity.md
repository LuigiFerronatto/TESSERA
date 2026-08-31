# #92 — Make the memory gate prove what it did

| Field | Value |
|---|---|
| Issue | [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| Record status | `VALIDATED` |
| Capability type | `runtime safety contract` |
| Pull request | [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) |
| Head commit | [`4679965`](https://github.com/LuigiFerronatto/TESSERA/commit/4679965050498a4d9dcc67de67c15e5407b5201c) (audited candidate) |
| Merge commit | [`9ab03f7`](https://github.com/LuigiFerronatto/TESSERA/commit/9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05) (canonical squash merge) |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA must not say “I removed the dangerous instruction” unless the text it will save is demonstrably different and safe under its deterministic rules.

## What problem existed?

Before #92, the write gate could report that safe text was sanitized without
changing it. It could also detect a hostile instruction without neutralizing
the complete payload, while persistence metadata sounded stronger than the
real protection.

Colloquially, the gate can claim that it removed a dangerous item from a bag even though the item is still inside.

## How did TESSERA behave before?

```text
detect suspicious text
→ sanitization flag may become true
→ persistence candidate may remain identical
→ audit metadata overclaims protection
```

## What changed or is being tested?

**CURRENT — MERGED ON MAIN THROUGH `9ab03f7`.**

PR #108 separated path validation, detection, transformation, admission and
persistence. It uses hashes as fingerprints of the exact original and
persistence-candidate text.

## How does it work now?

**CURRENT MAIN (`9ab03f7` and later):**

```text
validate portable ID and contained destination
→ detect
→ transform only under a complete versioned rule
→ choose accept | accept_sanitized | reject | review
→ persist only after an accepting decision
```

The merged evaluator rejects direct known hostile instruction blocks and sends
quoted/documentary or suspicious-tag-only ambiguity to review. It emits no
`accept_sanitized`; the schema permits that state only for a complete bounded
whole-content rule. Reject/review/invalid-path outcomes do not mutate the
canonical corpus, registry, graph, Evidence Ledger or index.

## Concrete example

| Input | Current result |
|---|---|
| Safe fact | Accept unchanged; never call it sanitized |
| Direct known hostile instruction, including multiline payload | Reject; do not persist canonically |
| Quoted security example | Preserve under an explicit policy or review it; do not silently destroy it |
| Absolute/traversal/UNC/symlink-escaping memory ID | Reject before warnings, timestamps or filesystem mutation |

## How was it validated?

The merged implementation passed 67 focused write-gate tests and 241 tests in
the complete local suite, including multilingual/adversarial, path-containment,
hash-invariant, atomic-failure, zero-side-effect and Python/CLI/MCP parity
coverage. Python 3.9, Python 3.12, smoke, sanity and benchmark-reporting CI were
green; LongMemEval was correctly skipped under `SMOKE_ONLY`.

## What improved?

The merged contract turns path escape and partial-redaction overclaim into
deterministic non-persisting rejection, while preserving safe writes,
same-directory atomic replacement and truthful public metadata.

## What remains unimplemented?

General semantic prompt-injection defense, quarantine/review storage, a broadly
safe sanitizer, directory-fsync crash durability, State Contamination
evaluation, #95 project-agnostic runtime cleanup and #67 Quality Gate
integration remain unimplemented.

## What is unlocked next?

#92 now satisfies only its own dependency edge for #67 and #19. #67 remains
blocked on #93, #95 and regression-gate integration. #19 remains blocked on
#13, #16 and #73. No unrelated Test Card became ready.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) |
| Pull request | [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) |
| Merge commit | [`9ab03f7`](https://github.com/LuigiFerronatto/TESSERA/commit/9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05) |
| Evidence/Learnings/Decision | [Superseding KEEP record](https://github.com/LuigiFerronatto/TESSERA/issues/92#issuecomment-5479001151), [post-merge audit](https://github.com/LuigiFerronatto/TESSERA/issues/92#issuecomment-5479489764) |
| Implementation CI | [Python 3.9/3.12, smoke and sanity](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33396222206), [benchmark reporting](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33396222211) |
| Benchmark record | Implementation applicability `SMOKE_ONLY`; LongMemEval not rerun |
| PR Evolution Audit | [Current deduplicated audit](../PR_EVOLUTION_92.md) |

## Evolution

```text
truthful Markdown format gate (#94)
→ known sanitizer-status and path-containment defects (#92)
→ path-contained conservative detect/transform/admit/persist contract (PR #108 / merge `9ab03f7`)
→ later State Contamination experiment
```
