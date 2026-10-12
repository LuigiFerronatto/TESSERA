# 358 — Quickstart should connect agents to the configured memory

| Field | Value |
|---|---|
| Issue | [#358](https://github.com/LuigiFerronatto/TESSERA/issues/358) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | See the linked issue's implementation pull request |
| Head commit | See the implementation pull request |
| Merge commit | Not merged |
| Decision | Proposed `KEEP`, pending exact-head CI |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-12 |

## In one sentence

Quickstart should connect an agent to the memory already selected by the project.

## What problem existed?

Copying the quickstart MCP block could point an agent at an empty or unrelated
`memories` directory even when the project selected `kb/store` and separate notes.

## How did TESSERA behave before?

On canonical `6228ecb`, a project configured with `store.path: kb/store` still
produced `Store: <root>/memories` and a `TESSERA_STORAGE_DIR` override. Applying
the plan indexed that store instead of the configured source roots.

## What changed or is being tested?

Project discovery feeds `ConfigurationResolver`. The plan carries the resolved
configuration into apply, displays source/include and index boundaries, and emits
`--project <root>` with no environment override when project config is selected.
Explicit and canonical environment selections retain resolver precedence. The
no-config path retains its existing storage-only behavior and output shape.

## How does it work now?

TARGET — NOT YET ON MAIN. The candidate uses the same project selection as runtime
configuration, including nested-directory discovery and version-1 compatibility.
Invalid configuration fails visibly. Planning does not create directories, scan
notes, index files, modify config or install harness configuration.

## Concrete example

```text
store.path: kb/store
sources.roots: notes/**/*.md
index.path: .tessera/custom-index
→ Store: <root>/kb/store
→ Source: <root>/notes (include: **/*.md)
→ Index: <root>/.tessera/custom-index
→ MCP args: ["--project", "<root>"]
```

## How was it validated?

`tests/test_issue_358_quickstart_config.py` covers 13 cases: custom/default/v1
stores from project and nested directories, plain/JSON output, no-config shape,
explicit/canonical/obsolete environment precedence, malformed configuration, and
an applied source/index selection with byte-preserved source/config files.
Before the fix 10 cases failed and 3 passed; after the fix all 13 pass.

The combined #358/#93/#95/#117 focused suite passed 75 tests. A 30-run local
read-only quickstart probe measured p50/p95 of 0.914/1.041 ms with zero notes and
0.902/1.008 ms with 2,500 synthetic notes; all source/config bytes were unchanged.
These are local smoke observations, not a retrieval-performance claim.
The deterministic sanity evaluation passed 4 queries with hit@3 1.0, MRR 0.875,
and evidence hit rate 1.0. Exact-head CI remains the publication gate.

## What improved?

All six configured layout fixtures select the same corpus and boundaries as
`ConfigurationResolver`; apply indexes the configured source instead of an empty
suggested store. No-config JSON remains unchanged.

## What remains unimplemented?

No harness-file installation, project-type heuristic changes, runtime retrieval
changes or new source-selection policy. Inherited canonical storage environment
variables continue to have the resolver's documented precedence at MCP startup.

## What is unlocked next?

After merge, quickstart copy-paste setup can target existing projects correctly.
This provides evidence for integration UX (#190), without claiming its other
acceptance gates are complete.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card; Evidence/Learnings/Decision | [#358](https://github.com/LuigiFerronatto/TESSERA/issues/358) |
| Pull request / exact head / evolution audit | Linked implementation PR in #358 |
| Previous config delivery | #153 / merged PR #173 (`2508676`) |
| Merge commit | Not merged |
| Benchmark record | Smoke-only; deterministic sanity and 2,500-note planning probe above |

## Evolution

```text
Project config v2 selects separate store, sources and index (#153)
→ quickstart still proposes a storage-only directory
→ #358 candidate shares project selection for display, MCP block and apply
→ merge and canonical lifecycle reconciliation remain pending
```
