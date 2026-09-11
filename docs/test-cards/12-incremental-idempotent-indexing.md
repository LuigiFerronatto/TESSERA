# 12 — Indexing only reparses what actually changed

| Field | Value |
|---|---|
| Issue | [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [#246](https://github.com/LuigiFerronatto/TESSERA/pull/246) |
| Head commit | Final candidate [`def1c43c`](https://github.com/LuigiFerronatto/TESSERA/commit/def1c43c069f616e63fdea7e384e15af4ecfef44) |
| Merge commit | Canonical squash merge [`971801cd`](https://github.com/LuigiFerronatto/TESSERA/commit/971801cd89b6ce7b890df9ceb43b6afff9fa0964) |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-11 |

## In one sentence

`tessera index` now tracks per-source hashes, reuses unchanged source
contributions, and reports exactly which sources were added, updated, moved,
or removed instead of reparsing the whole corpus on any change.

## What problem existed?

The prior `build_index()` decided freshness from a coarse fingerprint —
`(file_count, max_mtime)`. Any change to that pair triggered a full rebuild:
every Markdown source was reparsed and the graph/corpus were rebuilt from
scratch, even when only one file changed. There was no way to see which
sources were actually affected, and deleted sources relied on a full rebuild
to disappear rather than an explicit removal step.

## How did TESSERA behave before?

```text
edit one file
→ (file_count, max_mtime) changes
→ full graph/corpus/registry clear
→ every Markdown source reparsed
→ no scanned/added/updated/moved/removed counts reported
```

## What changed or is being tested?

A rebuildable per-source manifest under `.tessera_index/` now tracks stable
identity and content hashes per source. Indexing classifies each source as
unchanged, added, updated, moved, or removed; only affected sources are
reparsed, and orphaned derived entity/tag nodes are removed for deleted
sources. The global TF-IDF matrix is still refit whenever the corpus changes,
so retrieval/ranking semantics are unchanged — this card reduces reparsing
and reconstruction, not vectorization. If the manifest exists without a
usable graph snapshot (including after a project relocation), indexing falls
back to a full rebuild rather than producing an inconsistent partial state.

## How does it work now?

**VALIDATED ON `main`.** The CLI reports scanned/parsed/unchanged/added/
updated/moved/removed counts for every `tessera index` run. A no-op run on an
unchanged corpus parses zero sources. Add/edit/move/delete lifecycle
preserves stable memory and document IDs where applicable, and deleted
sources leave no stale graph/corpus entries.

## Concrete example

```text
tessera index                      # first run: scanned=N, parsed=N, added=N
# (no source changes)
tessera index                      # scanned=N, parsed=0, unchanged=N
mv docs/a.md docs/moved-a.md
tessera index                      # moved=1, no duplicate node/evidence
rm docs/b.md
tessera index                      # removed=1, node/edges/corpus entries for b.md gone
```

## How was it validated?

- No-op indexing parses zero sources;
- add/edit/move/delete lifecycle preserves stable memory and document IDs;
- deleted sources leave no stale graph/corpus entries;
- a manifest without `graph.pkl` forces a complete rebuild;
- project relocation reparses sources when persisted paths are no longer
  valid;
- existing canonical, persistence, engine and init tests pass;
- focused suite `tests/test_issue_12_incremental_indexing.py` and the updated
  parity/runtime-boundary suites pass on the final candidate head (exact
  pass/skip counts were not independently re-run for this reconciliation;
  see CI run evidence below for the authoritative result);
- CI on the final candidate head `def1c43c` (`test`/`distribution` for Python
  3.9 and 3.12, `smoke`, `sanity-eval`, `benchmark-reporting`) is green;
  Benchmark Ledger declares `SMOKE_ONLY` and correctly skips
  `longmemeval-v1-dev-50`, since ranking semantics are unchanged;
- distribution validation builds and installs both wheel and sdist in an
  external clean room.

## What improved?

- Unchanged corpora no longer trigger any reparsing;
- source lifecycle (add/edit/move/delete) is explicit and deterministic
  instead of an opaque full-rebuild side effect;
- deleted sources no longer leave stale derived graph/tag/entity nodes.

## What remains unimplemented?

- The TF-IDF vectorizer itself is still refit globally on any corpus change;
  this card does not provide incremental vector embeddings;
- no filesystem watcher/daemon — indexing remains an explicit, on-demand
  operation;
- temporal/state semantics and relation confidence are out of scope (see #15,
  #26).

## What is unlocked next?

- [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) (text ingestion
  beyond Markdown) and [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73)
  (versioned source/memory revision history) had their only remaining hard
  blocker (#12) satisfied and move to `READY`.
- [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) and
  [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) remain
  `BLOCKED` — they still depend on #69/#70, which are not yet implemented.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) |
| Pull request | [#246](https://github.com/LuigiFerronatto/TESSERA/pull/246) |
| Merge commit | [`971801cd89b6ce7b890df9ceb43b6afff9fa0964`](https://github.com/LuigiFerronatto/TESSERA/commit/971801cd89b6ce7b890df9ceb43b6afff9fa0964) |
| Evidence/Learnings/Decision | Maintainer audit `KEEP` on final candidate head `def1c43c` (PR #246 review thread) |
| Benchmark record | `SMOKE_ONLY`; `longmemeval-v1-dev-50` skipped |
| PR Evolution Audit | Not a separate file by maintainer decision; scope ratification recorded in [PR #246](https://github.com/LuigiFerronatto/TESSERA/pull/246) body and `CHANGELOG.md`. |

## Evolution

```text
full rebuild on any (file_count, max_mtime) change
→ #12 per-source manifest, hash-based classification, targeted reparse
→ current state: incremental add/edit/move/delete lifecycle on main
→ next validated dependency: #69 (text ingestion), #73 (revision history)
```
