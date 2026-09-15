# 70 — Structural segmentation without destroying source fidelity

| Field | Value |
|---|---|
| Issue | [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [PR #270](https://github.com/LuigiFerronatto/TESSERA/pull/270) |
| Head commit | `e14ef92e2891d8429539ec4a47174c76ab241839` (exact-head evidence `6f493ad239504999242128a3b02fba6775f4bc73`) |
| Merge commit | [`8ca854f14f8f57443784e6cf3524419a953c2ce6`](https://github.com/LuigiFerronatto/TESSERA/commit/8ca854f14f8f57443784e6cf3524419a953c2ce6) |
| Decision | `KEEP` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-09-15 |

## In one sentence

Long or heading-structured Markdown/plain-text sources now expose
deterministic, addressable sub-spans for evidence, while every retrieval
result still returns the complete original document.

## What problem existed?

Before this change, every source — a two-line note or a multi-thousand-word
reference — was indexed as exactly one atomic memory. A query targeting one
section of a long document could only retrieve the whole document (diluting
evidence precision) or fail to surface it at all.

## How did TESSERA behave before?

A 3,000+ character structured reference indexed as one memory with one
evidence span covering the whole body. There was no way to point the Evidence
Ledger at just the relevant paragraph or heading section.

## What changed or is being tested?

- Short, already-atomic memory cards remain untouched (no fragmentation).
- Long structured Markdown is segmented by heading; long unstructured
  Markdown/plain text is segmented by bounded paragraph/line windows.
- Each derived `source_segment` records parent memory ID, stable document ID,
  exact document hash, source path/format, heading, ordinal, and exact line
  span.
- Segments live outside the three semantic drawers and outside the parent
  document candidate/PageRank pool — they refine evidence selection on an
  already-ranked parent, they do not compete for ranking weight or appear as
  standalone pseudo-memory results.

## How does it work now?

A query matches segment facets to select a precise `evidence_info` span on
the complete, unchanged parent document result. Editing, moving, or deleting
a source retracts its stale derived segments; identity is preserved across
pure moves.

## Concrete example

For a 3,075-character structured reference, TESSERA derives three addressable
segments. A query targeting the middle section returns the parent document ID
with a 1,047-character exact evidence segment (`0.3405` of the full body) and
full source-version/span provenance — the parent memory itself is unchanged
and complete.

## How was it validated?

```text
exact-head CI full suite: PASS (Python 3.9 and Python 3.12)
focused #70/retrieval/conflict/LongMemEval unit suite: 44 passed
exact-head LongMemEval V1 dev-50: KEEP against immediate parent `c50b32d`,
  identical aggregate and all 50 per-query rankings; repeatability=true under
  different Python hash seeds
wheel + sdist build: PASS; twine check: PASS
clean-room installed-artifact harness (TTY included): PASS
```

Maintainer Audit recorded `KEEP` with zero P0/P1 findings.

## What improved?

- Long documents can expose precise, addressable evidence spans.
- Provenance coverage remains `1.0`; retrieval ranking hashes are stable
  across Python hash seeds.
- Established document candidate/PageRank ranking behavior is unchanged.

## What remains unimplemented?

- Segmentation thresholds are deterministic Foundation policy, not learned
  corpus-specific tuning.
- Conversational episode segmentation, durable revision history (#73), and
  semantic embeddings remain out of scope.
- Adapter precedence / instruction resolution (#71/#72) is not addressed by
  this card.

## What is unlocked next?

[#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) had its only
remaining hard blocker (#70) satisfied and moves to `READY`.
[#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) still depends on
further harness-adapter-registry work not delivered by this PR and remains
`BLOCKED`.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) |
| Pull request | [PR #270](https://github.com/LuigiFerronatto/TESSERA/pull/270) |
| Merge commit | [`8ca854f14f8f57443784e6cf3524419a953c2ce6`](https://github.com/LuigiFerronatto/TESSERA/commit/8ca854f14f8f57443784e6cf3524419a953c2ce6) |
| Evidence/Learnings/Decision | Maintainer Audit `KEEP` on exact-head `6f493ad2`; PR #270 evaluation card |
| Benchmark record | `REQUIRED`; LongMemEval V1 dev-50 passed (`KEEP`) on `6f493ad2` |
| PR Evolution Audit | [PR_EVOLUTION_70.md](../PR_EVOLUTION_70.md) |

## Evolution

```text
Markdown/plain-text sources as single atomic memories (#12, #69)
-> #70 document + addressable derived segment (D3) modeling
-> current state: complete parent documents plus deterministic, addressable
   heading/paragraph-window segments with exact provenance on main
-> next validated dependency: #13 corpus/metadata doctor
```
