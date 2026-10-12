# 349 — One rule for which files TESSERA reads

| Field | Value |
|---|---|
| Issue | [#349](https://github.com/LuigiFerronatto/TESSERA/issues/349) |
| Record status | `IMPLEMENTED` (architecture decision only) |
| Capability type | `architecture decision` |
| Pull request | [#366](https://github.com/LuigiFerronatto/TESSERA/pull/366) (ADR 0005, Accepted) |
| Head commit | `cf16d539afca0e903ef611a564d7de53bea3aa58` (final candidate) |
| Merge commit | `b486e6f2c47b367fc686ae84e00b6afdd5a4f9e7` |
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

This stage records an architecture decision only. ADR 0005 adopts that one
selected-source set, derived from the ADR 0004 discovery policy, is the only
input for every corpus reader; that `.tessera-ignore` is the single exclusion
authority; that symlinks are skipped everywhere with severity depending on how
they were selected; that `init` persists patterns instead of file lists; and,
that a root `.gitignore` participates as a convenience-ignore layer
(owner-confirmed). No runtime code changes in this stage.

## How does it work now?

The ADR is accepted and merged on `main`; its runtime target is not implemented. Until the implementation cards merge, the indexer
keeps its independent file walk.

## Concrete example

```text
before: indexer reads ['.env.md', 'notes/a.md', 'notes/b.md', 'notes/big.md', 'notes/c.md', 'secrets/token.md']
target: indexer reads ['notes/a.md', 'notes/b.md', 'notes/c.md']   # same as discovery
```

## How was it validated?

The baseline observations above were recorded in issue #349 on `main`
`7e7b20e`; they are historical evidence, not a new runtime measurement.
The [owner decision](https://github.com/LuigiFerronatto/TESSERA/issues/349#issuecomment-6118666384)
records `KEEP`. PR #366's merge and final candidate were verified against
GitHub and the merge's second parent; the candidate and merge trees match.

[Final-candidate CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38217185375)
failed the unrelated ledger concurrent-initialization test on Python 3.12; no source-selection test failed. Later ADR candidates #368/#369 passed CI on the same runtime. This does not erase the historical failure.
[Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38217185692)
passed with documentation-only `NOT_APPLICABLE` applicability. This record
uses `IMPLEMENTED`, not a claim that the proposed runtime or its performance
has been validated. No new human approval is inferred from merge or CI.

## What improved?

Nothing at runtime yet. The repository gains one binding contract that the
implementation cards can test against.

## What remains unimplemented?

All runtime behaviour remains unimplemented: single-authority selection and
ignore enforcement (#352), symlink parity and severity (#353), and pattern
persistence in `init` (#354), including the `.gitignore` layer.

## What is unlocked next?

The ADR prerequisite for #352, #353 and #354 is satisfied; #357 has its
persistence contract. Implementation selection and shared-code coordination
remain separate from acceptance. No runtime delivery is claimed.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#349](https://github.com/LuigiFerronatto/TESSERA/issues/349) |
| Pull request | [#366](https://github.com/LuigiFerronatto/TESSERA/pull/366) |
| Merge commit | `b486e6f2c47b367fc686ae84e00b6afdd5a4f9e7` |
| Evidence/Learnings/Decision | Issue #349 Evidence section |
| Benchmark record | Not applicable (architecture decision) |
| PR Evolution Audit | [Verified delivery](../../history/pr-evolution/349.md) |

## Evolution

```text
ADR 0004 discovery policy (discovery only)
→ ADR 0005 proposed: one selected-source set for every reader
→ current state: Accepted and merged on main, runtime unchanged
→ next implementation: #352 single-authority implementation
```
