# 12 follow-up — Preserve the selected corpus when rebuilding memory

| Field | Value |
|---|---|
| Issue | [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12), reliability follow-up to the delivered index contract |
| Record status | `IMPLEMENTED` (merged; canonical-merge CI/benchmark cancelled, so not `VALIDATED`) |
| Capability type | `runtime` |
| Pull request | [PR #282](https://github.com/LuigiFerronatto/TESSERA/pull/282) |
| Head commit | Runtime candidate `51a8c3c281470bd290829beb94202405a61befc4`; final candidate head `879ad1f54ecd08f0895c3040743ac8c8b13291ae` |
| Merge commit | `89dec1e444e15bfa8b1361683a9b88a89402888e` |
| Decision | `KEEP` ([exact-head independent audit](https://github.com/LuigiFerronatto/TESSERA/pull/282#issuecomment-5957192591)) |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-09 |

## In one sentence

This repair makes fresh, cached and incremental builds respect the
same selected sources and retain valid source versions and relations.

## What problem existed?

Four independently reproduced gaps remained after the original #12 delivery:
project/store relative paths could collide and hide edits, updating a relation
target could discard incoming links from unchanged sources, nonrecursive API
indexing could broaden a source allow list, and it could reuse a recursive cache.

## How did TESSERA behave before?

On main `20814a47ec0f72d7bea0639e0b057df1ecf5cded`, changing
`docs/guide.md` while `memories/docs/guide.md` existed could report a cache hit
and keep returning the old document. Editing B could remove A's declared A→B
link even though A's source did not change. The existing full suite passed
565 tests (five environment-dependent skips); four additional probes failed.

## What changed or is being tested?

- Use one physical source namespace while preserving logical-ID conventions
- Rebuild old graph snapshots and preserve only provable manifest identities
- Replay retained source relations after changed targets are reconstructed
- Narrow configured source patterns by traversal depth without replacing them
- Include recursion mode in cache freshness validation
- Align Corpus Doctor and evidence freshness with the physical source root

Ranking weights, write admission, source contents and the three drawers remain
unchanged.

## How does it work now?

**IMPLEMENTED ON MAIN (merge `89dec1e444e15bfa8b1361683a9b88a89402888e`).** Project documents and generated memories have
distinct physical paths and document identities; edits appear after indexing.
Source-backed relations survive target updates. Both recursion settings retain
the configured source selection, and cache reuse respects the requested mode.

## Concrete example

```text
docs/guide.md + memories/docs/guide.md
edit only docs/guide.md from "amber" to "magenta"
before: cache_hit; query("magenta") -> []
candidate: one source reparsed; query("magenta") -> documentation/guide
```

## How was it validated?

The four independent baseline reproductions fail before the patch and pass
with the repair. `tests/test_index_corpus_equivalence.py` adds lifecycle,
configuration, migration, rename, provenance and relation regression controls.
Local final validation: 586 passed and five gh-aw-dependent skips on Python
3.12.14/Linux, including 21 added cases. The installed wheel passed the four
original probes, 37 API/CLI checks and 18 real stdio MCP groups. Another 125
mutation/reload cycles matched cleanly reparsed graphs and identities.
Four-query sanity remained Hit@1=0.75, Hit@3=1.0, MRR=0.875.
[PR #282 checks](https://github.com/LuigiFerronatto/TESSERA/pull/282/checks)
record the final candidate CI and required benchmark. The
[independent KEEP audit](https://github.com/LuigiFerronatto/TESSERA/pull/282#issuecomment-5957192591)
covers final candidate `879ad1f54ecd08f0895c3040743ac8c8b13291ae`.

After merge, [canonical CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/37849491343)
and the [canonical Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/37849491372)
were cancelled on `89dec1e444e15bfa8b1361683a9b88a89402888e`.
Subsequent-main [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/37849579311)
and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/37849579474)
passed on `0a4a22c3b356c191a6f30c555eb01677ac2b85a4`, which includes this repair.
Those later results are integration evidence, not a pass on the earlier merge
SHA. The repair remains `IMPLEMENTED`, not `VALIDATED`; a cancelled or unrun
gate is never treated as a pass.

## What improved?

The original four state-transition discrepancies are removed in local probes.
The candidate additionally checks source identity separation and source
freshness rather than testing only whether a query returned some text.

## What remains unimplemented?

Semantic retrieval, temporal truth arbitration, source revision history,
crash-durability guarantees and multi-process writer coordination remain
outside this repair. The recorded merge does not imply a release or validation
of these out-of-scope capabilities.

## What is unlocked next?

No roadmap dependency is promoted by this repair. Lifecycle `VALIDATED` status
awaits CI/benchmark evidence for the canonical merge commit.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) |
| Previous index delivery | [PR #246](https://github.com/LuigiFerronatto/TESSERA/pull/246), merge `971801cd89b6ce7b890df9ceb43b6afff9fa0964` |
| Configuration boundary | [PR #173](https://github.com/LuigiFerronatto/TESSERA/pull/173), merge `2508676d472088733702b6ed920fc829df9a7681` |
| Source segmentation/cache context | [PR #270](https://github.com/LuigiFerronatto/TESSERA/pull/270), merge `8ca854f14f8f57443784e6cf3524419a953c2ce6` |
| Baseline | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Regression tests | `tests/test_index_corpus_equivalence.py` |
| Benchmark record | Final candidate passed per exact-head audit; canonical merge runs cancelled; subsequent-main integration passed (links above) |
| Evidence/Learnings/Decision | Repair PR; recorded exact-head `KEEP`, with candidate, canonical merge and subsequent-main evidence distinguished |
| Merge commit | `89dec1e444e15bfa8b1361683a9b88a89402888e` |

## Evolution

```text
#153 selected-source boundary + #12 incremental index + #70 exact-hash cache
→ four reproduced transition defects
→ repair candidate and targeted coverage
→ exact-head KEEP and canonical merge
→ post-merge reconciliation; canonical validation remains incomplete
```

The historical #12 validation record remains intact. This page records its
merged repair follow-up and does not reopen or close the original issue.
