# 350 — One duplicated note should not take the whole memory offline

| Field | Value |
|---|---|
| Issue | [#350](https://github.com/LuigiFerronatto/TESSERA/issues/350) |
| Record status | `IMPLEMENTED` (architecture decision only) |
| Capability type | `architecture decision` |
| Pull request | [#368](https://github.com/LuigiFerronatto/TESSERA/pull/368) (ADR 0006, Accepted) |
| Head commit | `b8ce5f72244c731700ca224da998704c65a4a876` (final candidate) |
| Merge commit | `16152d78b20c1ee37a4b808f5c4d6b55b2bd4e68` |
| Decision | `KEEP` (ADR accepted; runtime not implemented) |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-10-12 |

## In one sentence

When two notes claim the same explicit ID, TESSERA should keep the rest of the
memory available, report every such clash at once, and never guess which
conflicting note is the real one.

## What problem existed?

If any two files declare the same frontmatter `id`, the index build stops at
the first clash. No note can be searched from the CLI, Python or MCP, only one
clash is reported per run, and exact copies of one note are treated as badly as
two different notes fighting over one name. A file without an `id` whose
path-derived ID happens to equal another file's explicit ID also stops the
build.

## How did TESSERA behave before?

```text
notes/c.md  id: team/conflict  "Version one."
notes/d.md  id: team/conflict  "Version two, different."
tessera index -> Error [internal_error]; 0 notes queryable
```

## What changed or is being tested?

This stage records an architecture decision only. ADR 0006 adopts collecting
all identity claims before admitting notes, letting explicit IDs win over
path-derived ones, keeping one canonical copy of byte-identical duplicates,
quarantining genuinely conflicting copies (owner-confirmed), listing
every clash in one structured report, and offering `--strict` to keep today's
fail-fast behaviour for CI. No runtime code changes in this stage.

## How does it work now?

The ADR is accepted and merged on `main`; its runtime target is not implemented. Until #355 merges, the first explicit-ID collision
still aborts the build.

## Concrete example

```text
target: Index rebuilt: N notes. 2 explicit-id collisions:
  team/dup       duplicate_identical  kept notes/a.md (notes/sub/a-copy.md skipped)
  team/conflict  explicit_id_conflict quarantined notes/c.md, notes/d.md
tessera index --strict -> fails with index.explicit_id_collision listing both
```

## How was it validated?

The baseline observations above were recorded in issue #350 on `main`
`7e7b20e`; they are historical evidence, not a new runtime measurement.
The [owner decision](https://github.com/LuigiFerronatto/TESSERA/issues/350#issuecomment-6118666771)
records `KEEP`. PR #368's merge and final candidate were verified against
GitHub and the merge's second parent; the candidate and merge trees match.

[Final-candidate CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38217337767)
passed.
[Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38217337695)
passed with documentation-only `NOT_APPLICABLE` applicability. This record
uses `IMPLEMENTED`, not a claim that the proposed runtime or its performance
has been validated. No new human approval is inferred from merge or CI.

## What improved?

Nothing at runtime yet. The repository gains a binding admission and reporting
contract for #355.

## What remains unimplemented?

All runtime behaviour remains unimplemented and is owned by #355.

## What is unlocked next?

The ADR prerequisite for #355 is satisfied. The collision contract that
#356 must render is decided, but the runtime error code is not implemented.
Coordinate source-selection integration with #352/#353 before delivery.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#350](https://github.com/LuigiFerronatto/TESSERA/issues/350) |
| Pull request | [#368](https://github.com/LuigiFerronatto/TESSERA/pull/368) |
| Merge commit | `16152d78b20c1ee37a4b808f5c4d6b55b2bd4e68` |
| Evidence/Learnings/Decision | Issue #350 Evidence section |
| Benchmark record | Not applicable (architecture decision) |
| PR Evolution Audit | [Verified delivery](../../history/pr-evolution/350.md) |

## Evolution

```text
F3 explicit identity enforced by aborting the build
→ ADR 0006 proposed: complete diagnostics, canonical copies, quarantined conflicts, --strict
→ current state: Accepted and merged on main, runtime unchanged
→ next implementation: #355 implementation
```
