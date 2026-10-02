# 12 follow-up — Preserve the selected corpus when rebuilding memory

| Field | Value |
|---|---|
| Issue | [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12), reliability follow-up to the delivered index contract |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | Draft repair candidate; link recorded in the PR evidence |
| Head commit | See the linked repair PR's exact head and CI |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

This repair candidate makes fresh, cached and incremental builds respect the
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

**TARGET — NOT YET ON MAIN.** Project documents and generated memories have
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
The draft PR records exact final full-suite, installed-wheel, CLI/MCP, sanity
and CI evidence. Required benchmark results must be recorded before a merge
decision; an unrun or blocked benchmark is never treated as a pass.

## What improved?

The original four state-transition discrepancies are removed in local probes.
The candidate additionally checks source identity separation and source
freshness rather than testing only whether a query returned some text.

## What remains unimplemented?

Semantic retrieval, temporal truth arbitration, source revision history,
crash-durability guarantees and multi-process writer coordination remain
outside this repair. No merge or release is implied by a passing local test.

## What is unlocked next?

No roadmap dependency is promoted by this unmerged candidate. After review and
required exact-head CI, a maintainer may decide whether to merge the repair.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) |
| Previous index delivery | [PR #246](https://github.com/LuigiFerronatto/TESSERA/pull/246), merge `971801cd89b6ce7b890df9ceb43b6afff9fa0964` |
| Configuration boundary | [PR #173](https://github.com/LuigiFerronatto/TESSERA/pull/173), merge `2508676d472088733702b6ed920fc829df9a7681` |
| Source segmentation/cache context | [PR #270](https://github.com/LuigiFerronatto/TESSERA/pull/270), merge `8ca854f14f8f57443784e6cf3524419a953c2ce6` |
| Baseline | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Regression tests | `tests/test_index_corpus_equivalence.py` |
| Benchmark record | Exact-head PR CI; pending until completed |
| Evidence/Learnings/Decision | Repair PR; `PENDING`, with baseline and candidate distinguished |
| Merge commit | Not merged |

## Evolution

```text
#153 selected-source boundary + #12 incremental index + #70 exact-hash cache
→ four reproduced transition defects
→ this repair candidate and targeted coverage
→ exact-head review/CI/benchmark decision, then post-merge reconciliation
```

The historical #12 validation record remains intact. This page records its
unmerged repair follow-up and does not reopen or close the original issue.
