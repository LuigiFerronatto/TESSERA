# 349 — One rule for which files TESSERA reads

| Field | Value |
|---|---|
| Issue | [#349](https://github.com/LuigiFerronatto/TESSERA/issues/349) |
| Record status | `IN_PROGRESS` |
| Capability type | `architecture decision` |
| Pull request | [#366](https://github.com/LuigiFerronatto/TESSERA/pull/366) (ADR 0005, Accepted) |
| Head commit | See the pull request |
| Merge commit | Not merged |
| Decision | `KEEP` (ADR accepted; runtime not implemented) |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-10-12 |

## In one sentence

TESSERA should decide once which files belong to the memory corpus, and every
command, the Python API and the MCP server should read exactly those files.

## What problem existed?

Two parts of TESSERA choose files independently. Discovery and
`config doctor` respect `.tessera-ignore`, the mandatory secret exclusions,
the size limit and the symlink policy. The indexer used by `index`, `query`,
`list`, `stats` and the MCP server walks the configured patterns on its own and
applies none of those rules. A file a user excluded, a `secrets/` note, a
`.env.md` file or an oversized file can therefore be indexed and returned to an
agent.

## How did TESSERA behave before?

```text
.tessera-ignore: notes/d.md
tessera config doctor -> notes/d.md is ignored
tessera index         -> notes/d.md is parsed and indexed
```

## What changed or is being tested?

This stage records an architecture decision only. ADR 0005 proposes that one
selected-source set, derived from the ADR 0004 discovery policy, is the only
input for every corpus reader; that `.tessera-ignore` is the single exclusion
authority; that symlinks are skipped everywhere with severity depending on how
they were selected; that `init` persists patterns instead of file lists; and,
that a root `.gitignore` participates as a convenience-ignore layer
(owner-confirmed). No runtime code changes in this stage.

## How does it work now?

TARGET — NOT YET ON MAIN. Until the implementation cards merge, the indexer
keeps its independent file walk.

## Concrete example

```text
before: indexer reads ['.env.md', 'notes/a.md', 'notes/b.md', 'notes/big.md', 'notes/c.md', 'secrets/token.md']
target: indexer reads ['notes/a.md', 'notes/b.md', 'notes/c.md']   # same as discovery
```

## How was it validated?

The current behaviour was reproduced on canonical `main` 7e7b20e with the
fixture recorded in [#349](https://github.com/LuigiFerronatto/TESSERA/issues/349)
and the `_iter_source_files()` versus `discover_sources_for_configuration()`
comparison quoted in ADR 0005. The decision itself is validated by review;
documentation consistency is covered by the existing docs test suite.

## What improved?

Nothing at runtime yet. The repository gains one binding contract that the
implementation cards can test against.

## What remains unimplemented?

All runtime behaviour remains unimplemented: single-authority selection and
ignore enforcement (#352), symlink parity and severity (#353), and pattern
persistence in `init` (#354), including the `.gitignore` layer.

## What is unlocked next?

Once this ADR merges, #352, #353 and #354 are unblocked, and #357 has its
persistence contract.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#349](https://github.com/LuigiFerronatto/TESSERA/issues/349) |
| Pull request | [#366](https://github.com/LuigiFerronatto/TESSERA/pull/366) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Issue #349 Evidence section |
| Benchmark record | Not applicable (architecture decision) |
| PR Evolution Audit | Pull request body |

## Evolution

```text
ADR 0004 discovery policy (discovery only)
→ ADR 0005 proposed: one selected-source set for every reader
→ current state: Accepted in review, runtime unchanged
→ next validated dependency: #352 single-authority implementation
```
