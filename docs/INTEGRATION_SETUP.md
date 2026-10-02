# Experimental integration setup plans (#190)

This candidate adds two read-only setup entrypoints over one plan core. It does
not claim that a client is configured, connected, or compatible with a tested
version. The existing `quickstart` command and the #120 MCP server are unchanged.

```bash
# Direct path: preview a portable logical store binding.
tessera integrate claude --scope project --store-name shared-notes --dry-run --json

# Guided selection, with the same planner and JSON contract.
tessera mcp setup --runtime claude --runtime gemini --scope project \
  --store-name shared-notes --dry-run --json

# A terminal can prompt for runtime selection when --runtime is omitted.
tessera mcp setup --scope project --store-name shared-notes

# User-local path binding is explicit and never presented as portable.
tessera integrate gemini --scope user --store-path /absolute/local/memories --dry-run

# Removal only plans the entry tracked by this installer's ownership receipt.
tessera integrate gemini --scope project --remove --dry-run --json
```

Scope is required. Preview is the default, including when `--dry-run` is omitted.
Noninteractive setup never selects a client on the user's behalf. A blocked
request exits 2 and provides a structured diagnostic. `--apply` is recognized
but refuses CLI mutation until the real-client acceptance gates below pass.

## What the plan contains

- PATH executable evidence and known standard-config existence, separately
- Runtime version `null` and compatibility `unverified`; detection runs no client
- Explicit runtime, project root, project/user scope, and named-store/local-path binding
- Target JSON and ownership paths, current/desired fingerprints, exact entry mutation,
  formatting impact, other-scope guard, and rollback prerequisites
- Evaluated native CLI argument arrays, clearly not executed
- Existing #120 MCP transport, with #171 semantic tools and #177/#196 hooks unavailable

The plan does not print existing runtime settings or credentials. Its internal
byte snapshots must remain in process memory: do not use `dataclasses.asdict`,
pickle, or debug dumps to persist a plan. `plan.to_dict()` is the safe preview.
Ownership metadata contains hashes and creation flags, never credential values.
No credentials are added to TESSERA's memory store or configuration.

## Supported candidate adapters

| Runtime | Current candidate | Config scopes | Deliberate boundary |
|---|---|---|---|
| Claude Code | strict JSON plan | project `.mcp.json`; user `.claude.json` | local-scope collisions detected; no local-scope edits |
| Gemini CLI | strict JSON plan | project/user `.gemini/settings.json` | JSONC/duplicate keys/unknown structure refused |
| Codex | executable/config discovery, blocked plan | documented project/user TOML paths shown as evidence | no TOML rewriter and no invented project flag for `codex mcp add` |
| Copilot CLI | executable discovery, blocked plan | unavailable | no MCP/hook file generation or Bash/PowerShell claims |
| Generic MCP | explicit diagnostic | unavailable | MCP does not specify a universal client config format |

Custom provider home overrides block default-path planning. Symlinked paths,
special files, oversized/ambiguous JSON, unowned existing `tessera` entries,
modified ownership, and project/user collisions are refused. A matching server
name is not proof of installer ownership. An entry installed by `quickstart` or
manually is not silently adopted, even if its command already matches.

The project descriptor is `tessera-mcp --global <name>`. Each machine must
register that logical store separately. It deliberately contains no path to
another developer's checkout or home. This is a selected shared-store binding,
not automatic project identity or isolation (#257). A user-local absolute path
is available only at user scope. The installed `tessera-mcp` entrypoint is used;
setup does not install packages or use a machine-specific Python/source path.

## Experimental filesystem API

`integration_setup.build_plan` is a pure snapshot transformation.
`apply_plan` and `rollback_plan` require matching snapshots and return immutable
states. `integration_files.bind_file_plan` binds a reviewed plan to explicit
paths; `apply_file_plan` and `rollback_file_plan` perform the filesystem changes.
These are experimental Python module APIs, not new top-level Engine exports.

A caller must first read the requested config and its fingerprint-only ownership
sidecar into `DocumentState`, build and inspect the plan, bind the same exact
snapshots and explicit target/other-scope paths, and then explicitly choose
apply. The sidecar filename is `.tessera-<runtime>-<scope>-owner.json` beside the
config. The receipt returned by apply retains byte-exact rollback data in memory.
This API must only be used for paths and access changes the caller authorized.
All delivered tests use temporary synthetic configs; no actual agent settings,
accounts, security policy, credentials, clients, or MCP registrations were changed.

Transaction mechanics:

1. Refuse stale config, ownership, other-scope snapshots, permissions, symlinks,
   hardlinks, special files, path aliases, and an existing installer lock
2. Stage with a private same-directory temporary file, flush/fsync it, recheck
   expected state, then use atomic `os.replace` per changed file
3. Preserve existing file modes; use private modes for new config/ownership files
4. On a caught write failure, restore completed files only while their exact
   post-write snapshots still match; preserve intervening edits and report
   `recovery_complete=False` for partial recovery
5. Roll back exact bytes/modes/absence and remove only empty directories created
   by the transaction; removal deletes only the owned server and owned empty wrappers

Important limit: two files are not an OS-atomic transaction. A crash or forced
termination between replacements can leave partial state or a lock requiring
manual inspection. No crash-durable journal is claimed. Close the client before
using the experimental API: client writers do not honor TESSERA's lock, and an
uncooperative write between the final check and replace remains a race. Tests
exercise detected races and caught failures, not universal interprocess locking.
This limitation is a real acceptance gate, not a claim that implementing an
apply API requires runtime-account access.

## Primary-source verification and pins

Provider contracts were checked on **2026-10-02**. These are schema/CLI evidence
pins, not a supported runtime-version matrix:

- Claude [current MCP scopes and native CLI](https://code.claude.com/docs/en/mcp)
  documents `.mcp.json`, user/local `.claude.json`, `mcpServers`, and the stdio
  `--` delimiter. The public documentation has no immutable revision; scope
  behavior is explicitly an observed-date contract. The official
  [stdio shape example](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/plugins/plugin-dev/skills/mcp-integration/examples/stdio-server.json)
  pins `command`/`args` at commit `52c76441cae91f6891e4712306bffb057ff6fec5`
  (blob `60af1c69dd539cebe1ea7daad34181a68de063ac`). It is plugin documentation;
  the live MCP page, not the plugin wrapper, supplies this adapter's scope paths.
- Gemini [native add implementation](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/commands/mcp/add.ts)
  pins scope choices and stdio fields at `fb972b2f87fe7d5b06d37eac711490162d98de2c`
  (blob `98e6a708797001b7e9993acb5cd2f96eb2177a0f`). Its
  [storage paths](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts)
  and [home resolver](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/paths.ts)
  establish standard settings paths and `GEMINI_CLI_HOME`.
- Codex [native MCP implementation](https://github.com/openai/codex/blob/4dd51f4a5f2037f8aa322fe7807315e6530a4ec8/codex-rs/cli/src/mcp_cmd.rs)
  is pinned at `4dd51f4a5f2037f8aa322fe7807315e6530a4ec8`
  (blob `ac4b0154b36ea7db008ce3e47de2d3ac06320b4e`). Add writes through
  `find_codex_home`/global MCP configuration. Its
  [official MCP documentation](https://developers.openai.com/codex/mcp)
  describes `mcp_servers` TOML tables in user/project configs. Those are different
  surfaces, so this candidate does not fabricate a project-scoped CLI command.
- Copilot [official MCP setup](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
  was checked for discovery context only. No adapter schema is asserted.

Native registration remains the preferred route to evaluate for production.
We do not execute it here because real version-specific overwrite, ownership,
rollback, and policy behavior have not been accepted. The strict JSON fixture
adapter proves reversible mechanics independently of those client processes.

## Remaining acceptance gates

- Actual supported versions on Linux, macOS, and Windows, including native add/remove,
  startup/restart behavior, inherited environment, client approvals, and store resolution
- Robust crash recovery and noncooperating client-writer coordination before CLI apply
- Comment-preserving Codex TOML and a verified Copilot MCP adapter before generating configs
- Provider hook adapters (#177), canonical Hook Core (#196), semantic API (#171),
  and future shared renderer integration (#166); no imports from unmerged candidates
- Portable project-local identity/store binding (#257), beyond explicit named global stores

The issue remains open. Synthetic correctness is not real runtime integration acceptance.
