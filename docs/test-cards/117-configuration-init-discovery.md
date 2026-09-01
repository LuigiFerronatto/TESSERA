# #117 — Let TESSERA explain where memory lives

| Field | Value |
|---|---|
| Issue | [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime configuration` |
| Pull request | [PR #150](https://github.com/LuigiFerronatto/TESSERA/pull/150) |
| Head commit | Final candidate recorded after CI |
| Merge commit | Not merged |
| Decision | Candidate `KEEP` after green CI |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

Before, you usually had to know or pass the memory path; after this candidate,
TESSERA can resolve an explicitly configured project or named global store and
explain exactly why that one store was selected.

## What problem existed?

TESSERA already kept Python, CLI and MCP on the same selected path once a path
was known. It did not have a project-owned config, a user registry of named
stores, or a safe initialization flow for creating either. Running `init`
without a path silently used `./memories`, including in non-interactive use.

## How did TESSERA behave before?

The selection chain was explicit path, `TESSERA_STORAGE_DIR`, deprecated
`LAO_MEM_DIR`, then `./memories`. `tessera init` constructed an Engine for that
path and built its index. It wrote no durable explanation of which project or
named store owned the directory.

## What changed or is being tested?

The candidate adds a closed, versioned project config at
`.tessera/config.yaml`; a closed, versioned OS-appropriate registry of named
absolute paths; persistent UUID store identities; one reusable selection
result; bounded nearest-project discovery; atomic config writes; and:

```text
tessera init --project [PATH] [--store PATH]
tessera init --global NAME --store PATH
tessera config show|list|doctor|unregister
```

All inspection and mutation commands can emit stable JSON where applicable.

## How does it work now?

**IN PROGRESS while the implementation PR is open.**

Selection is explicit path, canonical environment, deprecated environment,
nearest project config, explicitly named global entry, then an actionable
failure. The result identifies the absolute store, source, persisted store ID,
and applicable project or registry metadata. It selects exactly one store and
never merges registered projects.

Interactive init asks only for missing choices, shows every planned create or
update, and confirms inferred mutation. Non-interactive init fails before any
write when its target mode is missing. `--dry-run` exposes the plan and writes
nothing. Existing `tessera init PATH` remains a documented project-mode
compatibility alias.

## Concrete example

```bash
tessera init --project . --store memories --non-interactive --json
tessera config show --json
```

The project file can be committed because it contains only schema version,
stable store ID and path—no provider key or secret. From a nested directory,
the nearest exact `.tessera/config.yaml` wins.

A named store is explicit:

```bash
tessera init --global research --store /srv/tessera/research --non-interactive
tessera config show --global research --json
tessera config unregister research
```

Unregistering leaves `/srv/tessera/research`, its Markdown and its index
untouched.

## How was it validated?

The Issue #117 executable matrix covers precedence, canonical/deprecated env,
nested configs, named/missing global entries, TTY and non-TTY init, dry-run,
atomic failure, unregister, moved/missing stores, closed schema, path and
symlink policy, OS registry paths, stable JSON, home-boundary discovery,
independent stores and the #93 write-once/read-through-config regression.

The full repository suite, compilation, artifact build/install smoke,
deterministic sanity, and fresh PR CI are required before the candidate is
merge-ready. LongMemEval is intentionally skipped under `SMOKE_ONLY` because
retrieval, ranking and evidence semantics do not change.

## What improved?

Configuration is source data, while `.tessera_index/` remains disposable
derived state. Store moves do not invent a new logical identity when the same
project or registry name is explicitly updated. Missing paths are diagnosed,
not silently deleted or recreated. Exact marker checks replace guesswork; no
home scan, credential inspection, provider probing or cross-project copy occurs.

## What remains unimplemented?

This card does not prove clean-machine onboarding (#118), redesign the CLI
appearance (#119), change MCP startup/protocol (#120), define official Skills
(#121), publish a distribution (#134), decide legal ownership (#87), implement
the corpus Metadata Doctor (#13), or change retrieval/conflict behavior.

## What is unlocked next?

Only after canonical merge and lifecycle validation may #118, #119 and #120 be
routed forward. #121 still depends on #120. #134 remains blocked until #117
and #118 are validated and #87 is complete.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #117](https://github.com/LuigiFerronatto/TESSERA/issues/117) |
| Pull request | [PR #150](https://github.com/LuigiFerronatto/TESSERA/pull/150) |
| Merge commit | Not merged |
| Architecture decision | [ADR 0003](../adr/0003-configuration-and-store-discovery.md) |
| PR Evolution Audit | [PR_EVOLUTION_117.md](../PR_EVOLUTION_117.md) |
| Executable matrix | `tests/test_issue_117_config_init_discovery.py` |
| Evidence/Learnings/Decision | Attached to Issue #117 after final candidate CI |
| Benchmark record | `SMOKE_ONLY`: deterministic sanity and Benchmark Ledger |

## Evolution

```text
explicit/env/default path with no persisted discovery
→ #117 project config + named global registry + explainable selection
→ IN_PROGRESS candidate (not yet on main)
→ canonical merge/lifecycle validation before #118 can start
```
