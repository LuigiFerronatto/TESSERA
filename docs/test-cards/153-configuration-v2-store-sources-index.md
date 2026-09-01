# #153 — Separate memory writes, readable sources, and derived index state

| Field | Value |
|---|---|
| Issue | [#153](https://github.com/LuigiFerronatto/TESSERA/issues/153) |
| Record status | `IN_PROGRESS` |
| Capability type | `CONFIGURATION_V2` |
| Pull request | pending publication from `test-card/153-config-v2` |
| Merge commit | Not merged; candidate branch only |
| Audited main | `0880ef3ec417735c105898039cc202450407af2b` |
| Decision | candidate `KEEP`, subject to final CI |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-01 |

## In one sentence

TESSERA now has separate, explicit boundaries for where generated memories are
written, which existing Markdown files may be read, and where disposable index
state is rebuilt.

## What problem existed?

The v1 runtime used `storage_dir` for three jobs at once: write destination,
read corpus, and parent directory for `.tessera_index/`. That protected the
corpus after #93, but it could not safely index a root README or selected
`docs/` and `research/` files while keeping generated memories under
`memories/`.

## How did TESSERA behave before?

Project configuration persisted only a UUID and store path. The resolved
`StorageSelection` passed one directory to Engine. Engine recursively read
Markdown below that directory, wrote generated notes there, and stored its
derived cache below the same directory. MCP retained the legacy environment or
`./memories` bootstrap.

## What changed or is being tested?

The candidate introduces one resolved runtime configuration carrying all three
boundaries:

```text
store.path   -> ordinary generated-memory writes only
sources      -> explicit read/index roots and include patterns
index.path   -> disposable graph, identity manifest, and Evidence Ledger cache
```

Project schema v2 is closed and explicit:

```yaml
schema_version: 2
store:
  id: <stable UUID>
  path: memories
sources:
  roots:
    - path: .
      include:
        - README.md
        - docs/**/*.md
        - research/**/*.md
        - memories/**/*.md
index:
  path: .tessera/index
```

## How does it work now?

**CANDIDATE — not yet merged or validated on `main`.**

`ResolvedConfiguration` is the runtime source of truth. Configuration-aware
Engine, CLI, and MCP construction consume it. Engine writes remain contained
by `storage_dir`, which is the compatibility name for `store.path`; source
iteration uses only configured roots and allow-list patterns; index persistence
uses only `index.path` and excludes that tree from discovery.

Project source roots must resolve inside the physical project. A source-file
symlink that escapes its configured root fails the build. The one compatibility
exception is a v1 store explicitly located outside the project: it remains its
own sole source root and does not authorize any additional external source.

## Concrete example

The v2 file above indexes four visible groups without copying them. A call such
as `tessera write --id project/fact ...` still writes only
`memories/project/fact.md`. Deleting `.tessera/index/` deletes no source and the
next build reconstructs equivalent graph and Evidence Ledger state.

New `tessera init` writes schema v2 conservatively with only `store.path` as a
source. It does not discover the repository. Broader source proposal, ignore
rules, and interactive source selection remain #154/#155.

## How was it validated?

The focused matrix (`209 passed`) covers a root README, separate `docs/` and `research/`
sources, read-only sources, a writable generated store, index deletion and
rebuild, lexical traversal, symlink escape, named-global isolation, v1
migration, held-constant retrieval, and Python/CLI/MCP result equality.

Both Python 3.9 and 3.12 full suites pass (`317 passed` each). Deterministic
sanity remains Hit@1 `0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence hit `1.00`,
with missing evidence passed. Candidate/CI identifiers are recorded in
`docs/PR_EVOLUTION_153.md` and PR evidence after publication. This record must
remain `IN_PROGRESS` until canonical merge and a separate post-merge lifecycle
sync.

## What improved?

- Existing source documents remain authoritative and untouched.
- Generated writes cannot target arbitrary read roots.
- Cache, identity manifest, graph snapshot, and Evidence Ledger summary have
  an explicit disposable location.
- Project and named-global stores remain isolated.
- MCP can consume the same v2 project boundary while keeping its legacy
  `./memories` fallback when no product config exists.

## What remains unimplemented?

This card does not implement `.tessera-ignore`, automatic scanning, source
picker UX, document segmentation, incremental indexing, hosted storage, or any
work owned by #154, #155, #157, #12, #69, or #70.

## What is unlocked next?

#154 and #155 remain blocked while this candidate is open. They may be
reconciled to `READY` only after #153 is canonically merged and its lifecycle
record is synchronized. The expanded #118 onboarding proof remains downstream.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #153](https://github.com/LuigiFerronatto/TESSERA/issues/153) |
| Branch | `test-card/153-config-v2` |
| Audited main | `0880ef3ec417735c105898039cc202450407af2b` |
| PR Evolution Audit | [PR_EVOLUTION_153.md](../PR_EVOLUTION_153.md) |
| Executable matrix | `tests/test_issue_153_configuration_v2.py` |
| Benchmark record | `SMOKE_ONLY`; held-constant deterministic sanity required |

## Evolution

```text
#93 one selected directory is the complete implicit corpus
-> #117 persisted project/global store selection
-> #153 explicit store / sources / index boundaries
-> #154/#155 remain unstarted until canonical reconciliation
```
