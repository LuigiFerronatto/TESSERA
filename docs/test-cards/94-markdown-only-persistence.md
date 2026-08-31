# #94 — Only persist memory in a format TESSERA can read

| Field | Value |
|---|---|
| Issue | [#94](https://github.com/LuigiFerronatto/TESSERA/issues/94) |
| Record status | `VALIDATED` |
| Capability type | `runtime contract` |
| Pull request | [#101](https://github.com/LuigiFerronatto/TESSERA/pull/101) |
| Merge commit | [`467ba64`](https://github.com/LuigiFerronatto/TESSERA/commit/467ba649f53312cedcecf40caf548af5f766c67b) |
| Decision | `KEEP — Markdown-only persistence` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA now rejects unsupported write formats before touching storage instead of claiming success for memory it cannot index.

## What problem existed?

A caller could request JSON persistence, receive an acknowledged write, and create content invisible to the Markdown index.

## How did TESSERA behave before?

```text
write as JSON
→ file acknowledged
→ index ignores it
→ user thinks memory exists
```

## What changed or is being tested?

PR #101 made Markdown the only canonical persistence format and moved validation before every durable mutation.

## How does it work now?

Omitted format and `md` use Markdown. Unsupported or unknown formats fail deterministically before files, registry, graph, Evidence Ledger or MCP index rebuild are touched.

## Concrete example

A request with `persist_format="json"` raises a deterministic `ValueError` and leaves the storage tree unchanged. A Markdown write survives a clean rebuild with the same logical identity.

## How was it validated?

Contract tests proved identical before/after storage hashes on rejection and Markdown visibility after a clean rebuild. Python 3.9/3.12, smoke and sanity CI passed.

## What improved?

Acknowledged writes and indexable memory can no longer diverge because of an unsupported requested format.

## What remains unimplemented?

Pre-existing JSON files are not migrated or removed, arbitrary JSON ingestion is unsupported, and orphan discovery belongs elsewhere.

## What is unlocked next?

The canonical persistence prerequisite for incremental indexing, text ingestion and write-gate integrity is stable.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#94](https://github.com/LuigiFerronatto/TESSERA/issues/94) |
| Pull request | [#101](https://github.com/LuigiFerronatto/TESSERA/pull/101) |
| Merge commit | [`467ba64`](https://github.com/LuigiFerronatto/TESSERA/commit/467ba649f53312cedcecf40caf548af5f766c67b) |
| Evidence/Learnings/Decision | [Issue evidence](https://github.com/LuigiFerronatto/TESSERA/issues/94#issuecomment-5471509112) |
| Benchmark record | Smoke/persistence contract only |
| PR Evolution Audit | PR #101 description |

## Evolution

```text
acknowledged but unindexable writes
→ pre-mutation format validation
→ truthful Markdown-only persistence
→ incremental corpus lifecycle work
```
