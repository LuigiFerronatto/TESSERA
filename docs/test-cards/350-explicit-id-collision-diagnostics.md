# 350 — One duplicated note should not take the whole memory offline

| Field | Value |
|---|---|
| Issue | [#350](https://github.com/LuigiFerronatto/TESSERA/issues/350) |
| Record status | `IN_PROGRESS` |
| Capability type | `architecture decision` |
| Pull request | Open (ADR 0006, Proposed) |
| Head commit | See the pull request |
| Merge commit | Not merged |
| Decision | `PENDING` |
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

This stage records an architecture decision only. ADR 0006 proposes collecting
all identity claims before admitting notes, letting explicit IDs win over
path-derived ones, keeping one canonical copy of byte-identical duplicates,
quarantining genuinely conflicting copies (pending owner confirmation), listing
every clash in one structured report, and offering `--strict` to keep today's
fail-fast behaviour for CI. No runtime code changes in this stage.

## How does it work now?

TARGET — NOT YET ON MAIN. Until #355 merges, the first explicit-ID collision
still aborts the build.

## Concrete example

```text
target: Index rebuilt: N notes. 2 explicit-id collisions:
  team/dup       duplicate_identical  kept notes/a.md (notes/sub/a-copy.md skipped)
  team/conflict  explicit_id_conflict quarantined notes/c.md, notes/d.md
tessera index --strict -> fails with index.explicit_id_collision listing both
```

## How was it validated?

The current behaviour, including the explicit-versus-inferred abort in both
processing orders, was reproduced on canonical `main` 7e7b20e with the fixture
recorded in [#350](https://github.com/LuigiFerronatto/TESSERA/issues/350). The
decision is validated by review; documentation consistency is covered by the
existing docs test suite.

## What improved?

Nothing at runtime yet. The repository gains a binding admission and reporting
contract for #355.

## What remains unimplemented?

All runtime behaviour remains unimplemented and is owned by #355. The
conflicting-copy policy (quarantine versus path-qualified IDs) remains open
until the owner confirms it at review.

## What is unlocked next?

Nothing is unlocked until this ADR is accepted. Acceptance unblocks #355 and
fixes the collision error code that #356 renders.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#350](https://github.com/LuigiFerronatto/TESSERA/issues/350) |
| Pull request | Open |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Issue #350 Evidence section |
| Benchmark record | Not applicable (architecture decision) |
| PR Evolution Audit | Pull request body |

## Evolution

```text
F3 explicit identity enforced by aborting the build
→ ADR 0006 proposed: complete diagnostics, canonical copies, quarantined conflicts, --strict
→ current state: Proposed, runtime unchanged
→ next validated dependency: #355 implementation
```
