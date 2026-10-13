# ADR 0005: One source-selection authority for every corpus reader

- Status: Accepted (owner decision recorded in PR #366 on 2026-10-12)
- Date: 2026-10-12
- Issue: [#349](https://github.com/LuigiFerronatto/TESSERA/issues/349)
- Amends: [ADR 0004](0004-safe-project-source-discovery.md) (consumption only;
  its discovery, ignore and symlink rules are unchanged)

## Context

ADR 0004 defines a safe, root-bounded discovery policy: mandatory exclusions,
`.tessera-ignore`, a 2 MiB size limit, and "all symlinks are skipped, including
aliases whose target remains inside the root". It deliberately scopes itself to
discovery and leaves "display/select/confirm/persist/index" to #155.

On canonical `main` (7e7b20e) the indexer does not consume that policy.
`TesseraEngine._iter_source_files()` walks `Path.glob()` for every configured
`include` pattern and applies only `.git`, `.tessera_index`, the derived index
and a built-in excluded-directory set. Two independent file-selection paths
therefore exist, and they disagree:

| Rule | `discover_sources()` / `config doctor` | `_iter_source_files()` / index, query, MCP |
|---|---|---|
| `.tessera-ignore` | applied | **not read** |
| Mandatory exclusions (`secrets/`, `.env*`, keys) | applied | **not applied** (only `.git`, index and history paths) |
| 2 MiB size limit | applied | **not applied** |
| Symlink inside root | skipped (forbidden diagnostic) | **followed** via `resolve()` |
| Dangling symlink | forbidden diagnostic, doctor `PROBLEM` | silently skipped |

With the #349 fixture, `.tessera-ignore` lists `notes/sub/a-copy.md` and
`notes/d.md`; the indexer still yields both, and the ignored `notes/d.md` then
aborts the build with an explicit-ID collision. A file a user excluded for
privacy is equally parsed and becomes queryable through CLI and MCP.

The mandatory exclusions are bypassed the same way. Adding `secrets/token.md`,
`.env.md` and a 2.2 MB `notes/big.md` to the same fixture with include
`**/*.md`:

```text
indexer:              ['.env.md', 'notes/a.md', 'notes/b.md', 'notes/big.md', 'notes/c.md', 'secrets/token.md']
discovery selectable: ['notes/a.md', 'notes/b.md', 'notes/c.md']
```

The engine's built-in excluded-directory set also hard-codes
project-specific names (`.venv-browser-agent`, `.browser-harness`, `Tessera`),
which the single authority makes unnecessary.

Configured selections compound the problem. `init` persists the plan's
selected files as literal `include` entries (#354), so on large trees the
configuration enumerates thousands of paths and freezes the corpus at init
time.

## Decision

### 1. One authority

Exactly one function produces the **selected source set** for a resolved
configuration. It is derived from the ADR 0004 discovery plan and is the only
input every corpus reader may use:

- `TesseraEngine` index builds (CLI `index`, `query`, `list`, `stats`, and the
  Python API);
- the MCP runtime;
- `config doctor` and corpus diagnostics (#13);
- `init` plan simulation and persistence.

No reader walks the filesystem independently. The legacy schema-v1 store-only
corpus keeps its current behaviour until it is migrated through `init`.

### 2. Selection rule

A regular file is selected if and only if:

1. it matches at least one configured `include` pattern of a configured source
   root; and
2. ADR 0004 classifies it as selectable (`RECOMMENDED` or `SUPPORTED`), which
   already accounts for mandatory exclusions, ignore rules, format and size.

`.tessera-ignore` is the single exclusion authority. An `include` entry never
overrides it; re-inclusion uses `!` in `.tessera-ignore` exactly as ADR 0004
already allows, and never overrides mandatory exclusions. A literal (wildcard
free) `include` entry that resolves to an ignored path yields a
`configured_source_ignored` diagnostic so the conflict stays visible.

### 3. Symlinks

ADR 0004's symlink rule applies on every surface: no reader opens a symlink or
its target. Severity depends on how the path was reached:

- a symlink matched only by a wildcard pattern produces a non-blocking
  `symlink_skipped` diagnostic, counted in doctor and JSON output, and can be
  silenced by a `.tessera-ignore` entry;
- a symlink named literally in `include` keeps the blocking
  `configured_source_forbidden` diagnostic, because the user asked for
  something the policy will not deliver.

Resolving internal symlinks as aliases remains rejected; reopening it requires
a separate ADR.

### 4. Persisted selections are patterns

`init` persists selections at the granularity users choose: a fully selected
discovery cluster becomes one directory glob (for example `docs/architecture/adr/**/*.md`,
plus the matching `*.txt` pattern while #69 formats are supported); a partially
selected cluster becomes its directory glob plus `.tessera-ignore` entries for
the deselected children; individually chosen root files remain literal entries.
The plan shows each pattern with its matched-file count. Existing enumerated
configurations remain valid and are never rewritten automatically.

### 5. `.gitignore` participation

Decision: a root `.gitignore` participates as a convenience-ignore layer
evaluated **before** `.tessera-ignore`, parsed with the same documented ADR
0004 subset (no `git` subprocess, no full gitignore grammar). Unsupported
gitignore lines are reported as diagnostics and skipped. Any path it ignores
can be re-included with `!` in `.tessera-ignore`; mandatory exclusions remain
non-overridable. Nested `.gitignore` files, `.git/info/exclude` and global
excludes are out of scope.

The owner chose option (a) of the `.gitignore` alternatives below.

### 6. Parity invariant

For any resolved configuration:

```text
set(paths read by any corpus reader) == selected_source_set(configuration)
```

Implementation cards must test this invariant on fixtures covering ignore
rules, re-inclusion, mandatory exclusions, the size limit, internal and
dangling symlinks, and literal versus wildcard includes.

### 7. Cost

Discovery runs at most once per build and its result is reused for selection.
An index build must not regress by more than 10% at p95 on a 2,500-note corpus
compared with `main`. Removing the second filesystem walk is expected to
reduce cost: on a real 18 MB corpus `_iter_source_files` accounted for 11.2 s
of an 18.8 s build.

## Alternatives considered

1. **Shared helpers, two paths.** Keep the glob walk and call the ignore and
   symlink helpers from it. Rejected: every future discovery rule would have
   to be added twice, which is how the current divergence happened.
2. **Indexer re-reads `.tessera-ignore` only.** Smallest change. Rejected: it
   fixes one row of the table and leaves mandatory exclusions, size and
   symlink parity broken.
3. **`include` overrides `.tessera-ignore`.** Rejected: two exclusion
   authorities with opposite precedence are hard to explain, and ADR 0004
   already provides `!` for intentional re-inclusion.
4. **`.gitignore` options.** (a) adopt as decided in §5 (chosen); (b) adopt behind an
   opt-in config key, which needs a schema version bump; (c) defer and keep
   ADR 0004 as is; (d) shell out to `git check-ignore`, rejected because it
   adds a runtime dependency on a `git` binary and on repository state.

## Consequences

- Files that are ignored, mandatorily excluded, oversized or reached through a
  symlink stop being indexed after upgrade. This is the intended fix and must
  be called out under `Fixed` in the changelog of each implementation PR.
- `config doctor` stops reporting wildcard-matched symlinks as a blocking
  problem.
- Configurations created by `init` become short and keep newly added notes in
  selected folders indexable without re-running `init`.
- Implementation is owned by #352 (single authority and ignore enforcement),
  #353 (symlink parity and severity) and #354 (pattern persistence); the
  interactive picker (#351/#357) persists through section 4.

## Boundaries

This ADR does not change discovery classification, the ignore grammar, the
size limit, schema versions, incremental indexing (#12), corpus diagnostics
UI (#13), collision handling (#350) or MCP startup (#361).
