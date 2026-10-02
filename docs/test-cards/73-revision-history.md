# #73 — Keep the previous source when a memory changes

| Field | Value |
|---|---|
| Issue | [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) |
| Record status | `IN_PROGRESS` |
| Capability type | `opt-in runtime experiment` |
| Pull request | Pending draft publication |
| Merge commit | Not merged |
| Decision | `KEEP opt-in R2`; defer full R3 temporal validity to #15 |
| Benchmark applicability | `SMOKE_ONLY` plus dedicated lifecycle experiment |
| Last audited | 2026-10-02 |

## In one sentence

The candidate preserves full observed source revisions and their evidence IDs
outside the disposable index, while retrieval continues to use current sources.

## What problem existed?

Overwriting a memory destroyed its prior body. Stable IDs and hashes could show
that it changed but could not recover the old evidence after an index rebuild.

## How did TESSERA behave before?

An in-place overwrite removed the only full copy of the previous version.
Deleting the derived index also removed its evidence records.

## What changed or is being tested?

A Python `revision_history=True` option archives observed text and evidence in
store-local, append-only history. Before replacing an existing generated memory,
the writer preserves its old body. Indexing also captures selected external
sources without rewriting them. Archive errors are explicit.

## How does it work now?

TARGET — NOT YET ON MAIN: select the Python constructor option, capture current
sources during indexing, preserve old text before a generated overwrite, and
resolve issued evidence separately from live retrieval. Failures remain visible.

## Concrete example

“Use Playwright” changes to “Use native browser recording.” The current source
and retrieval show the latter. An evidence ID issued for the former still
resolves to the complete old text, even after deleting and rebuilding the index.
Only one live memory participates in retrieval.

## How was it validated?

The [reproducible R0–R3 comparison](../../benchmarks/revisions/README.md) preserves
24/24 old bodies and canonical evidence IDs in R2, compared with 0/24 for R0.
Contract tests cover issued paragraph evidence, source deletion, index deletion,
restart, metadata-only revisions, rename, revert, failure and corrupt history.
Existing full-suite and sanity results are recorded in the draft PR; no merge
or canonical validation is claimed by this page.

## What improved?

Old evidence is reconstructable without duplicate live memories. Full-source
copies and SQLite pages consume 12.66x current-only storage in the small fixture.
Capturing sources and issued evidence adds local I/O. This is an opt-in choice.

## What remains unimplemented?

Unobserved external versions cannot be recovered. There is no implicit restore,
retention deletion, concurrent-editor transaction, CLI/MCP/config opt-in,
temporal validity, authority, default activation or full R3 temporal model.
See the [contract and failure boundaries](../REVISION_HISTORY.md).

## What is unlocked next?

A tested revision substrate can support downstream #15 temporal state, #16
supersession and #19 admission without claiming those capabilities now.

## Technical provenance

Canonical #12 indexing (`971801c`, PR #246) and #94 Markdown persistence
(`467ba64`, PR #101) are the prerequisites. This candidate is based on
`20814a47ec0f72d7bea0639e0b057df1ecf5cded` and does not require unmerged PR #282
or write-receipt work #263. After merge, record the canonical commit and reconcile
the card/roadmap; no issue is closed and no downstream work is declared complete
by this unmerged stage record.

## Evolution

Current-only source text and disposable fingerprints
→ opt-in observed full-source/evidence history
→ candidate durability evidence with measured overhead
→ review and merge before downstream temporal decisions
