# 179 — Compare memory lifecycle designs before choosing architecture

| Field | Value |
|---|---|
| Issue | [#179](https://github.com/LuigiFerronatto/TESSERA/issues/179) |
| Record status | `IN_PROGRESS` research candidate |
| Capability type | documentation / comparative research |
| Pull request | [#311](https://github.com/LuigiFerronatto/TESSERA/pull/311), draft |
| Head commit | Latest [PR #311 head](https://github.com/LuigiFerronatto/TESSERA/pull/311); source-audit anchor [`9923678`](https://github.com/LuigiFerronatto/TESSERA/commit/9923678b74724a714c8aec3b17e1cdda9e40c1f9), followed only by publication-metadata sync |
| Merge commit | Not merged |
| Decision | `PENDING`; proposal: KEEP research baseline, ITERATE bounded unknowns |
| Benchmark applicability | `NOT_APPLICABLE` — no retrieval/runtime change or external quality experiment |
| Last audited | 2026-10-02 |

## In one sentence

Compare five systems using pinned source evidence so TESSERA can test useful patterns without mistaking them for new or already-adopted capabilities.

## What problem existed?

Issue #179 listed hypotheses without a versioned ten-dimension code audit. Older research notes used an outdated MemPalace account reference and broad Mem0/Letta shorthand that could mix product generations or overlook existing source retention.

## How did TESSERA behave before?

At canonical baseline `20814a47ec0f72d7bea0639e0b057df1ecf5cded`, the competitive landscape and bibliography offered August product-document comparisons. No #179 5 × 10 matrix tied each claim to a pinned implementation and existing owner.

## What changed or is being tested?

The candidate adds a dated report, machine-readable matrix, required wide CSV, 46-source manifest and existing-owner snapshot. It labels code, docs, inference and unknown claims; corrects only affected older research boundaries; and routes every lesson into existing #179 owners.

## How does it work now?

**TARGET — NOT YET ON MAIN.** Readers can inspect the [audit](../research/MEMORY_LIFECYCLE_2026-10-02.md), follow immutable source links, and distinguish implemented external patterns from proposed TESSERA experiments. Runtime behavior is unchanged. #120 remains a closed contract reference; no owner is reopened or declared delivered.

## Concrete example

Before: “pre-compaction capture” could imply the transcript was already safe when compaction proceeded.

After: the pinned MemPalace handler starts asynchronous transcript ingest and separately waits for project mining. The lesson is to test capture-request and durable-completion receipts under #177/#168, without declaring that runtime behavior implemented by this research.

The Mem0 plugin similarly retains local redacted evidence, and Graphiti's MCP queue returns acceptance before durable processing. Neither should be reduced to an unqualified saved or extraction-only claim.

## How was it validated?

Local validation on 2026-10-02: **571 passed, 5 skipped, 14 warnings** in
160.31 seconds, with the MCP extra installed. The five skips require the absent
`gh-aw` CLI extension; no other checks were silently treated as passed. A final
focused research/stage rerun passed **14 tests** after the last wording change.
The [validation record](../evidence/179-memory-lifecycle/validation.json) captures
commands, counts and scope. Hosted CI is checked against the exact PR head separately and is not claimed
green by this local record. Commands use an isolated Python 3.12 environment outside the checkout:

```bash
python -m pytest -q tests/test_memory_lifecycle_research.py tests/test_plain_language_test_card_docs.py
python -m pytest -ra
```

The six research tests check dimensional coverage, labels, source fingerprints/immutable links, CSV contract and existing-owner routing. They are structural gates, not automated verification that every research claim is true. No competitor code, installer, service or benchmark was executed.

## What improved?

- 50 auditable dimension cells replace unversioned lifecycle hypotheses
- Core/plugin/managed and develop/release/historical boundaries are explicit
- Concrete failure and concurrency boundaries become proposed tests for current owners
- No benchmark ranking or unsupported novelty claim is introduced

## What remains unimplemented?

All runtime adoption decisions remain with #177 and the mapped cards. Managed-service internals, installation behavior, complete supporting-turn fidelity, crash durability and context-quality hypotheses remain bounded unknowns. Static source inspection does not validate live service behavior or guarantee no security leaks.

## What is unlocked next?

No dependency completion or WIP-selection state changes. Existing owners receive reference controls and proposed acceptance evidence, not automatic permission to implement. Review may KEEP this baseline and ITERATE a named gap when an owner needs it.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#179](https://github.com/LuigiFerronatto/TESSERA/issues/179) |
| Pull request | [#311](https://github.com/LuigiFerronatto/TESSERA/pull/311), draft |
| Canonical baseline | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | [Dated audit](../research/MEMORY_LIFECYCLE_2026-10-02.md), [matrix](../evidence/179-memory-lifecycle/matrix.json), [source manifest](../evidence/179-memory-lifecycle/sources.json) |
| Benchmark record | NOT_APPLICABLE; no external performance claims tested |
| PR Evolution Audit | Canonical baseline contained broad research notes; this isolated candidate adds documentation and structural tests only. PR #277 was the baseline Corpus Doctor merge, not a #179 delivery |

## Evolution

August documented emphasis → October pinned code/docs matrix candidate → maintainer research decision pending → owner-specific experiments only if selected.

Post-merge reconciliation must record the actual canonical merge, issue decision and stage status. No merge, issue closure, roadmap promotion or release is performed by this candidate. Roll back by reverting this documentation/test PR; no user data or index migration is involved. Changelog N/A: repository research and source-reference corrections do not change product behavior or promote a capability.
