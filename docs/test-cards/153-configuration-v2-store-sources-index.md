# #153 — Separate memory writes, readable sources, and derived index state

| Field | Value |
|---|---|
| Issue | [#153](https://github.com/LuigiFerronatto/TESSERA/issues/153) |
| Record status | `VALIDATED` |
| Capability type | `CONFIGURATION_V2` |
| Pull request | [#173](https://github.com/LuigiFerronatto/TESSERA/pull/173) |
| Final candidate | `72b2b0c44ecbdc6e5f45ed612f4eb9bb69c57cd4` |
| Runtime implementation commit | `53f772cdd0fae369a2ed3954751667d5e4ea52c4` |
| Merge commit | canonical squash `2508676d472088733702b6ed920fc829df9a7681` |
| Audited main | `0880ef3ec417735c105898039cc202450407af2b` |
| Decision | `KEEP` |
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

The canonical delivery introduces one resolved runtime configuration carrying all three
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

Both Python 3.9 and 3.12 final-candidate suites passed (`317 passed` each). Deterministic
sanity remains Hit@1 `0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence hit `1.00`,
with missing evidence passed. These are historical candidate results, not tests
retroactively generated after merge. Final-head TESSERA CI
[`33545813964`](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33545813964)
and Benchmark Ledger
[`33545813991`](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33545813991)
were green; LongMemEval was skipped under `SMOKE_ONLY`.

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

#154 is now `READY` because #153 was its only hard blocker. #155 remains
`BLOCKED` on #154, and #118 remains `BLOCKED` on #154/#155. #157's #153
foundation is satisfied, but the portfolio deliberately keeps #157 `DEFERRED`
rather than starting a second architecture lane. No downstream implementation
was started.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #153](https://github.com/LuigiFerronatto/TESSERA/issues/153) |
| Pull request | [PR #173](https://github.com/LuigiFerronatto/TESSERA/pull/173) |
| Branch | `test-card/153-config-v2` |
| Audited main | `0880ef3ec417735c105898039cc202450407af2b` |
| Final candidate | `72b2b0c44ecbdc6e5f45ed612f4eb9bb69c57cd4` |
| Runtime implementation | `53f772cdd0fae369a2ed3954751667d5e4ea52c4` |
| Canonical squash merge | `2508676d472088733702b6ed920fc829df9a7681` |
| PR Evolution Audit | [PR_EVOLUTION_153.md](../PR_EVOLUTION_153.md) |
| Executable matrix | `tests/test_issue_153_configuration_v2.py` |
| Benchmark record | `SMOKE_ONLY`; held-constant deterministic sanity required |

## Evolution

```text
#93 one selected directory is the complete implicit corpus
-> #117 persisted project/global store selection
-> #153 VALIDATED explicit store / sources / index boundaries
-> #154 READY
-> #155 BLOCKED
-> #118 BLOCKED
```

The candidate and canonical squash merge identify one `CONFIGURATION_V2`
delivery, not two capabilities.
