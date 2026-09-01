# #117 — Let TESSERA explain where memory lives

| Field | Value |
|---|---|
| Issue | [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117) |
| Record status | `VALIDATED` |
| Capability type | `CONFIGURATION_DISCOVERY` |
| Pull request | [PR #150](https://github.com/LuigiFerronatto/TESSERA/pull/150) |
| Head commit | `f636e39f4d48726a10a3dce15fa42de88b029a23` |
| Merge commit | `61cf76fbd6ed61972f0f5abae515ba9bffca4b55` |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-01 |

## In one sentence

Before, users mostly had to know or pass the memory directory; after, TESSERA
can persist project or global store configuration, resolve one canonical store
deterministically, and explain why that store was selected.

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

The validated implementation adds a closed, versioned project config at
`.tessera/config.yaml`; a closed, versioned OS-appropriate registry of named
absolute paths; persistent UUID store identities; one reusable selection
result; bounded nearest-project discovery; atomic config writes; and:

```yaml
schema_version: 1
store:
  id: <UUID>
  path: <relative-or-explicit-absolute-path>
```

```text
tessera init --project [PATH] [--store PATH]
tessera init --global NAME --store PATH
tessera config show|list|doctor|unregister
```

The init surface preserves `--store`, `--project`, `--global`,
`--non-interactive`, `--dry-run` and `--json`. Stable schema-version-1 JSON
reports fields including `store_id`, `storage_dir`, `source`, `project_root`,
`config_path`, `registry_name` and `registry_path`.

## How does it work now?

**VALIDATED ON `main`.**

Selection precedence is exactly: explicit store/path, `TESSERA_STORAGE_DIR`,
deprecated `LAO_MEM_DIR`, nearest project config, explicitly named global
registry entry, then actionable configuration failure. The result identifies
the absolute store, source, persisted store ID, and applicable project or
registry metadata. The persisted UUID identifies the logical store rather than
its filesystem path, so an explicit path update can preserve identity. TESSERA
selects exactly one store and never merges registered projects.

Interactive TTY init asks only for missing choices, shows every planned create
or update, and confirms inferred mutation. Non-TTY or `--non-interactive` init
fails before any write when its target mode is missing. `--dry-run` exposes the
plan and writes nothing. Existing `tessera init PATH` remains a documented
project-mode compatibility alias.

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

The Issue #117 executable matrix passed 20 tests covering precedence,
canonical/deprecated env,
nested configs, named/missing global entries, TTY and non-TTY init, dry-run,
atomic failure, unregister, moved/missing stores, closed schema, path and
symlink policy, OS registry paths, stable JSON, home-boundary discovery,
independent stores and the #93 write-once/read-through-config regression.

The final local full repository suite passed: 301 passed with 14 expected
warnings. Compilation, artifact build/install smoke and `git diff --check`
passed. Deterministic sanity remained Hit@1 0.75, Hit@3 1.00, Hit@5 1.00,
MRR 0.875, evidence hit rate 1.00, and missing-evidence passed. Final-candidate
TESSERA CI run `33459718574` and Benchmark Ledger run `33459718572` passed;
LongMemEval was correctly skipped under `SMOKE_ONLY` because retrieval,
ranking and evidence semantics did not change.

## What improved?

Configuration is source data, while `.tessera_index/` remains disposable
derived state. Project configuration is `<project>/.tessera/config.yaml`.
The global registry uses the OS configuration directory and contains discovery
metadata only—never copied memory, credentials, merged projects or a home scan.
Its path is `$XDG_CONFIG_HOME/tessera/registry.yaml` (or
`~/.config/tessera/registry.yaml`) on Linux,
`~/Library/Application Support/tessera/registry.yaml` on macOS, and
`%APPDATA%\tessera\registry.yaml` on Windows.
Store moves do not invent a new logical identity when the same project or
registry name is explicitly updated. Missing paths are diagnosed, not silently
deleted or recreated. Config writes are validated and atomic; config-file and
config-directory symlinks are refused, relative traversal is rejected, and
unregister removes metadata only. Source Markdown is never rewritten.

## What remains unimplemented?

This card does not prove clean-machine onboarding (#118), redesign the CLI
appearance (#119), change MCP startup/protocol (#120), define official Skills
(#121), publish a distribution (#134), decide legal ownership (#87), implement
the corpus Metadata Doctor (#13), or change retrieval/conflict behavior.

## What is unlocked next?

After canonical lifecycle synchronization, #118, #119 and #120 are `READY` but
remain unstarted. #121 remains `BLOCKED` on #120. #134 remains `BLOCKED` until
#118 is validated and #87 completes standalone LICENSE, owner-approved legal
ownership and the CONTRIBUTING entrypoint.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #117](https://github.com/LuigiFerronatto/TESSERA/issues/117) |
| Pull request | [PR #150](https://github.com/LuigiFerronatto/TESSERA/pull/150) |
| Final candidate | `f636e39f4d48726a10a3dce15fa42de88b029a23` |
| Merge commit | [canonical squash merge `61cf76f`](https://github.com/LuigiFerronatto/TESSERA/commit/61cf76fbd6ed61972f0f5abae515ba9bffca4b55) |
| Architecture decision | [ADR 0003](../adr/0003-configuration-and-store-discovery.md) |
| PR Evolution Audit | [PR_EVOLUTION_117.md](../PR_EVOLUTION_117.md) |
| Executable matrix | `tests/test_issue_117_config_init_discovery.py` |
| Evidence/Learnings/Decision | [Final candidate evidence](https://github.com/LuigiFerronatto/TESSERA/issues/117#issuecomment-5487457936), [post-merge maintainer audit](https://github.com/LuigiFerronatto/TESSERA/issues/117#issuecomment-5487668483) |
| Benchmark record | Implementation `SMOKE_ONLY`; lifecycle `NOT_APPLICABLE` |

## Evolution

```text
explicit/env/default path with no persisted discovery
→ #117 project config + named global registry + explainable selection
→ final candidate `f636e39` + canonical merge `61cf76f` counted once
→ `VALIDATED` / `KEEP`
→ #118, #119 and #120 `READY`; #121 and #134 remain `BLOCKED`
```

Configuration/discovery validated does not mean clean onboarding validated and
does not mean PyPI release complete. Those outcomes remain downstream work.
