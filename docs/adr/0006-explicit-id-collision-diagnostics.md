# ADR 0006: Explicit-ID collisions are complete, deterministic index diagnostics

- Status: Proposed
- Date: 2026-10-12
- Issue: [#350](https://github.com/LuigiFerronatto/TESSERA/issues/350)

## Context

An explicit frontmatter `id` is an authority claim: the author says "this note
is `team/conflict`". Foundation F3 protects that claim, and on canonical `main`
(7e7b20e) `build_index()` enforces it by raising `ValueError` the first time a
second file declares an already-seen explicit ID.

That enforcement has four observable problems:

1. **All-or-nothing availability.** One duplicate aborts the whole build, so
   zero notes are queryable from CLI, Python and MCP. In a field report, five
   duplicated files made a ~2,500-note corpus unusable, and the MCP server
   failed at startup.
2. **One collision per run.** Only the first collision is reported; N
   collisions need N fix-and-rerun cycles.
3. **No distinction between copies and conflicts.** Byte-identical copies of
   one note (common after folder reorganisations) are treated exactly like two
   different notes competing for one identity.
4. **Inferred IDs can block explicit ones.** An explicit ID that equals
   another file's *inferred* (path-derived) ID also aborts the build, in either
   processing order, although the inferred file made no identity claim.
   Verified on `main`: `n/aaa.md` without frontmatter plus `n/zzz.md` declaring
   `id: n/aaa` aborts, and so does the mirrored layout.

The CLI renders the exception as `internal_error` (#356). The engine already
has a per-file warning channel (`processing_warnings`) for other source
failures, so non-fatal handling has precedent. The identity manifest removes
older paths that share an ID on every parse ("move detection"), so a naive
lenient implementation that simply skipped the raise would make the manifest
alternate between the two live paths across rebuilds.

## Decision

### 1. Two-phase admission

Index builds first collect every identity claim from the selected source set
(ADR 0005) and only then admit notes. Admission no longer depends on
filesystem enumeration order.

### 2. Explicit beats inferred

An explicit ID always owns its identifier. A file whose *inferred* ID equals an
explicit ID receives the existing deterministic hash suffix (the mechanism
already used between inferred IDs), regardless of processing order. This is
not a collision; it produces an informational `inferred_id_suffixed`
diagnostic so the rename is visible.

### 3. Byte-identical explicit duplicates

When every file claiming one explicit ID has identical bytes (SHA-256 of the
raw file), exactly one copy is admitted under the ID. The canonical copy is the
lexicographically smallest normalized project-relative POSIX path, which is
deterministic across platforms and runs. The other copies are not admitted and
are reported as `duplicate_identical` with a pointer to the canonical path. The
identity manifest records only the canonical path, so it stays stable across
rebuilds.

### 4. Conflicting explicit duplicates

Proposed (option A): when copies differ, **no copy is admitted under the
contested ID**. All claimants are reported as `explicit_id_conflict`
(quarantined), relations that target the ID resolve to nothing and are
reported, and the rest of the corpus is indexed normally.

Rationale: admitting either copy picks an author's claim arbitrarily, and
admitting both under synthetic path-qualified IDs (option B) invents identities
nobody declared, which breaks links and relations that name the original ID
while looking healthy. Quarantine keeps the F3 guarantee — an explicit ID never
resolves to content its author may not have meant — and keeps the corpus
available.

This is the sub-decision the owner must confirm at review.

### 5. Complete diagnostics

Every collision is reported in one run with a stable shape:

```yaml
code: explicit_id_conflict          # or duplicate_identical
id: team/conflict
paths: [notes/c.md, notes/d.md]     # sorted
sha256: [<hash of c>, <hash of d>]  # same order as paths
resolution: quarantined             # or kept_canonical
canonical_path: null                # set for duplicate_identical
```

Diagnostics surface in `index` and `stats` (human summary plus JSON), in the
Python build result, in MCP `get_server_health`, and are available to the
corpus doctor (#13). Human output names counts and the first entries;
`--json` lists all of them.

### 6. Strict mode

`tessera index --strict`, `TesseraEngine.build_index(strict=True)` and an MCP
startup option restore fail-fast: the build stops before persisting anything
and raises one structured error, code `index.explicit_id_collision`, listing
every collision in the shape above. Duplicates that are byte-identical also
fail in strict mode. CI pipelines should use strict mode.

### 7. Exit codes

Default (lenient) builds exit 0 when the index was written, even with
collision diagnostics; the JSON envelope carries `diagnostics` and a
`collision_count` so automation can gate on it. Strict builds exit with the
configuration/data error code defined by the CLI output contract (#166).

## Alternatives considered

1. **Keep fail-fast.** Rejected: one bad file blocks every reader and
   collisions are found one at a time.
2. **First wins.** Rejected: the winner depends on enumeration order and the
   loss is silent.
3. **Path-qualified IDs for conflicts (option B).** Admit every copy as
   `<id>@<path-hash>`. Rejected as the default for the reasons in §4; it may be
   reconsidered as an explicit opt-in.
4. **Merge conflicting notes.** Rejected: content merging is cognition owned by
   the consuming agent (ADR 0001), not by the deterministic core.

## Consequences

- A corpus with duplicates becomes queryable again; conflicting notes are
  visible as diagnostics instead of crashing the build.
- `tests/test_canonical.py` currently asserts the abort; under this ADR that
  assertion moves to strict mode and a lenient-mode test is added (#355).
- Error naming coordinates with #356 so CLI and MCP render the same code.
- No user file is renamed, rewritten or deleted.

## Boundaries

This ADR changes admission and reporting only. It does not change how IDs are
declared or inferred, does not add content merging, and does not change source
selection (ADR 0005) or MCP startup (#361). Implementation is owned by #355.
