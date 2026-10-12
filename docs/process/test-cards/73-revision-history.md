# #73 — Keep the previous source when a memory changes

| Field | Value |
|---|---|
| Issue | [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) |
| Record status | `IMPLEMENTED` |
| Capability type | `opt-in runtime experiment` |
| Pull request | [PR #291](https://github.com/LuigiFerronatto/TESSERA/pull/291) (merged) |
| Head commit | Final candidate `121ff0a2ce8b67647a91dc5e8b47e1e53a63cd70` |
| Merge commit | `3a9e9b892604a69a30de44efe8980ef6682b8042` |
| Decision | `PENDING` lifecycle adoption; proposed `KEEP opt-in R2`, full R3 belongs to #15 |
| Benchmark applicability | `SMOKE_ONLY` plus dedicated lifecycle experiment |
| Last audited | 2026-10-12 |

## In one sentence

The merged opt-in implementation preserves full observed source revisions and
their evidence IDs outside the disposable index, while retrieval continues to
use current sources.

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

IMPLEMENTED ON `main`: select the Python constructor option, capture current
sources during indexing, preserve old text before a generated overwrite, and
resolve issued evidence separately from live retrieval. Failures remain visible.

## Concrete example

“Use Playwright” changes to “Use native browser recording.” The current source
and retrieval show the latter. An evidence ID issued for the former still
resolves to the complete old text, even after deleting and rebuilding the index.
Only one live memory participates in retrieval.

## How was it validated?

The [reproducible R0–R3 comparison](../../../benchmarks/revisions/README.md) preserves
24/24 old bodies and canonical evidence IDs in R2, compared with 0/24 for R0.
Contract tests cover issued paragraph evidence, source deletion, index deletion,
restart, metadata-only revisions, rename, revert, failure and corrupt history.
The original local full-suite and sanity results remain historical candidate
evidence in PR #291. Exact candidate and canonical checks are recorded below.

## Canonical delivery and check evidence

[PR #291](https://github.com/LuigiFerronatto/TESSERA/pull/291) merged on 2026-10-12. Final candidate
`121ff0a2ce8b67647a91dc5e8b47e1e53a63cd70` and canonical merge
`3a9e9b892604a69a30de44efe8980ef6682b8042` are distinct identities for one delivery.

- Final-candidate [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203793938)
  and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203793949)
  completed successfully on `121ff0a2ce8b67647a91dc5e8b47e1e53a63cd70`.
- Exact canonical CI was cancelled:
  [run 38203925811](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203925811)
  on `3a9e9b892604a69a30de44efe8980ef6682b8042`. This is not a successful canonical CI run.
- The canonical [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203925791)
  completed successfully on that same merge SHA.

These are historical engineering checks, not newly run benchmarks. The reviewed
PR discussion has no final-head formal reviews or accepted final-head KEEP
record. Earlier automatic BLOCK comments concern older candidates and are not
current-head defects. Current governance does not require a positive human or
automatic AI review. This correction records delivery and available validation;
it does not invent a retrospective approval or a new capability-adoption decision.

## What improved?

Old evidence is reconstructable without duplicate live memories. Full-source
copies and SQLite pages consume 12.66x current-only storage in the small fixture.
Capturing sources and issued evidence adds local I/O. This is an opt-in choice.

## What remains unimplemented?

Unobserved external versions cannot be recovered. There is no implicit restore,
retention deletion, concurrent-editor transaction, CLI/MCP/config opt-in,
temporal validity, authority, default activation or full R3 temporal model.
See the [contract and failure boundaries](../../reference/revision-history.md).

## What is unlocked next?

The merged substrate is available for bounded inspection. #15/#16/#19 are not
promoted by this correction: full temporal and admission semantics are absent,
canonical CI was cancelled, and the lifecycle adoption decision remains pending.

## Technical provenance

Canonical #12 indexing (`971801c`, PR #246) and #94 Markdown persistence
(`467ba64`, PR #101) are the prerequisites. The original candidate was based on
`20814a47ec0f72d7bea0639e0b057df1ecf5cded` and did not require then-unmerged
PR #282 or write-receipt work #263. The final integrated candidate and canonical merge
are recorded above. No issue is closed and no downstream capability is declared
complete by this factual lifecycle correction.

## Evolution

Current-only source text and disposable fingerprints
→ opt-in observed full-source/evidence history
→ merged opt-in durability with measured overhead
→ cancelled canonical CI and pending adoption remain explicit
