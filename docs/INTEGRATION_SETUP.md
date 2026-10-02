# Experimental integration setup (#190)

Direct and guided commands share one preview-by-default plan core. Applying a
plan changes configuration; it does not establish that a client is connected,
compatible with a tested version, trusted, or ready to use its tools. Existing
`quickstart` and #120 MCP server semantics are unchanged.

## Preview, apply, remove and undo

```bash
# Identical single-target plans and hashes through either entrypoint.
tessera integrate claude --scope project --store-name shared-notes --dry-run --json
tessera mcp setup --runtime claude --scope project --store-name shared-notes --json

# A terminal can prompt for explicit target selection when --runtime is omitted.
tessera mcp setup --scope user --store-name shared-notes

# Inspect the plan first, then repeat its exact selection, binding and action.
tessera integrate gemini --scope project --store-name shared-notes --json
tessera integrate gemini --scope project --store-name shared-notes \
  --apply --plan-hash <reviewed-sha256> --json

# Removal also requires a preview and its exact hash.
tessera integrate gemini --scope project --remove --json
tessera integrate gemini --scope project --remove \
  --apply --plan-hash <reviewed-removal-sha256> --json

# Undo the last meaningful owned-entry change, including removal.
tessera integrate gemini --scope project --rollback --json
tessera integrate gemini --scope project --rollback \
  --apply --plan-hash <reviewed-inverse-sha256> --json
```

Scope is required. Omitting `--apply` changes zero files. Noninteractive setup
never chooses a runtime for the user. `--config-home PATH` explicitly selects the
user-config home; `--project-root PATH` selects the project. All delivered
mutation tests use temporary synthetic roots. Missing/stale hashes, changed
scope/binding/action, or changed config/ownership/receipt bytes or modes require
a fresh preview and exit 2 before writes.

Project descriptors use the installed `tessera-mcp --global <name>` entrypoint.
Each machine must register that named store separately. No developer's absolute
checkout/home path is committed into project config. This is a selected shared
store, not automatic project identity/isolation (#257). An absolute
`--store-path /local/memories` binding is available at user scope only.

## Provider boundaries

| Runtime | Implemented candidate | Scope / format | Remaining boundary |
|---|---|---|---|
| Claude Code | JSON preview/apply/remove/undo | project `.mcp.json`; user `.claude.json` | local-scope collisions detected; no local-scope edits |
| Gemini CLI | JSON preview/apply/remove/undo | project/user `.gemini/settings.json` | ambiguous/commented JSON refused |
| Copilot CLI | JSON preview/apply/remove/undo | project `.github/mcp.json`; user `.copilot/mcp-config.json`; wrapped or bare server map | `.mcp.json` precedence checked; Git/trust/readiness unverified |
| Codex | inspected native add/remove/reversal argv plan | user scope; existing TOML parsed without rewriting | executor does not launch native commands; current native CLI has no project-scope flag |
| Generic MCP | explicit diagnostic | no universal client config standard | client-specific adapter required |

Native command candidates are evaluated from current official contracts. Copilot
native add/remove, like Codex, writes user configuration; project Copilot setup
uses its documented JSON adapter. Codex's native plan includes exact command
arguments, current file/mode guards, desired entry and reverse command. It does
not rewrite TOML or run a provider process. This is a concrete executor boundary,
not a claim that code implementation is blocked by user approval.

Known home overrides block default-path planning. Symlinks, hardlinks, special
files, oversized/ambiguous JSON, malformed ownership, unowned existing names,
and scope collisions are refused. An existing `tessera` name is not ownership
proof. Entries created manually or by `quickstart` are not silently adopted.

## Inspectable output

Plans expose PATH/config evidence separately, with version `null` and runtime
compatibility `unverified`. No detection command launches a provider. Output
includes explicit target/scope/binding, config/ownership/undo paths, guarded
fingerprints and modes, exact managed-entry/sidecar mutations, formatting impact,
rollback prerequisites, native CLI candidates and provider source pins.

Existing #120 stdio MCP tools are the only current tool capability claimed.
#171 semantic tools and #177/#196 lifecycle hooks remain unavailable. No future
renderer (#166), semantic or hook code is imported from unmerged candidates.

## Ownership and safe durable undo

The sidecar `.tessera-<runtime>-<scope>-owner.json` stores hashes and creation
flags. The CLI writes `.tessera-<runtime>-<scope>-undo.json` in the same
transaction. The undo record contains only the previous known TESSERA launcher,
prior ownership metadata, config format/existence/mode flags and post-apply
fingerprints. Arbitrary environment/header fields are rejected. Unrelated config
or credential values are never copied into these files or the public preview.

A no-op preserves the receipt. A new meaningful change replaces it, providing
one level of undo. `--rollback` refuses intervening config/ownership edits and
consumes the receipt after successful semantic reversal. It restores managed
entry/ownership values, recorded file modes and prior file absence, while
preserving unrelated values. Original formatting is not restored, and empty
config directories may remain across CLI processes.

The lower-level in-process API separately retains exact original bytes:
`build_plan`, `apply_plan`, `rollback_plan`, `bind_file_plan`, `apply_file_plan`
and `rollback_file_plan`. That in-memory receipt restores exact bytes/modes/
absence and cleans only empty directories created by its transaction. Raw
snapshots can contain unrelated secrets: do not persist `dataclasses.asdict`,
pickle or debug dumps of plans/receipts. `plan.to_dict()` is the safe preview.
These remain experimental module APIs, not new top-level Engine exports.

## Filesystem and multi-target mechanics

1. Check target, owner, undo, other-scope and precedence guards before writing
2. Hold an exclusive cooperating-installer lock; stage private sibling temporary
   files, flush/fsync, recheck, and atomically replace each changed file
3. Preserve existing modes; use private modes for new files
4. On a caught failure, reverse completed writes only while they still match
   this transaction; preserve intervening edits and report partial recovery
5. Apply guided targets sequentially after preflighting all targets; report
   completed targets through `applied_integrations` if a later target fails

There is no OS-atomic multi-file or multi-runtime commit. A crash can leave
partial state or a lock requiring inspection. Client writers do not honor the
installer lock and can race a final check/replace; close clients before using
these experimental actions. Those are production-hardening acceptance risks,
not claims of tested crash durability. A Claude project `.mcp.json` would shadow
the same Copilot server in `.github/mcp.json`, so that combined plan is blocked
before all writes. User scope or explicit nonconflicting targets remain available.

## Verified primary sources and pins

Checked **2026-10-02**. Schema evidence pins do not establish a tested client
version matrix:

- Claude [current MCP scope/CLI documentation](https://code.claude.com/docs/en/mcp)
  supplies project/user/local paths, `mcpServers` and stdio `--` separation.
  This live scope documentation has no immutable revision, so its observed date
  is explicit. The official [stdio shape example](https://github.com/anthropics/claude-code/blob/52c76441cae91f6891e4712306bffb057ff6fec5/plugins/plugin-dev/skills/mcp-integration/examples/stdio-server.json)
  pins `command`/`args` at `52c76441cae91f6891e4712306bffb057ff6fec5`
  (blob `60af1c69dd539cebe1ea7daad34181a68de063ac`). It is a plugin example;
  its wrapper is not substituted for the live scope contract.
- Gemini [native add source](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/cli/src/commands/mcp/add.ts)
  pins scope and stdio fields at `fb972b2f87fe7d5b06d37eac711490162d98de2c`
  (blob `98e6a708797001b7e9993acb5cd2f96eb2177a0f`). Its
  [storage paths](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/config/storage.ts)
  and [home resolver](https://github.com/google-gemini/gemini-cli/blob/fb972b2f87fe7d5b06d37eac711490162d98de2c/packages/core/src/utils/paths.ts)
  establish standard locations and `GEMINI_CLI_HOME`.
- Codex [native MCP source](https://github.com/openai/codex/blob/4dd51f4a5f2037f8aa322fe7807315e6530a4ec8/codex-rs/cli/src/mcp_cmd.rs)
  at `4dd51f4a5f2037f8aa322fe7807315e6530a4ec8`
  (blob `ac4b0154b36ea7db008ce3e47de2d3ac06320b4e`) uses global config through
  `find_codex_home`. [Official MCP docs](https://developers.openai.com/codex/mcp)
  describe `mcp_servers` TOML tables; those are distinct from a nonexistent
  native project-scope CLI flag. Plans do not invent that flag or rewrite TOML.
- Copilot [official MCP source](https://github.com/github/docs/blob/0b8c768bf0d5a13560ec82fd3daa414137e2e436/content/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers.md)
  at `0b8c768bf0d5a13560ec82fd3daa414137e2e436`
  (blob `419a3b499fe54f776f0d243920f4a5cc20679f7c`) documents native user add/remove,
  local command/args/tools, wrapped/bare project maps, project path precedence,
  and trust requirements. No trust setting is changed by setup.

## Remaining acceptance gates

- Actual supported client versions on Linux/macOS/Windows, native startup/restart,
  inherited environment, approval behavior and store resolution
- Controlled native execution for Codex's verified user-command plan; no native
  project-scoped registration is established by the current source
- Crash recovery and coordination with noncooperating client writers
- Generic client mapping, #171 semantic API, #177/#196 hooks and #257 automatic
  project identity; no dependent issue is declared satisfied here

#190 remains open. Hash-bound JSON code mechanics and native command planning are
implemented candidates. All mutation evidence is synthetic; no actual runtime
settings, clients, accounts, credentials, access or trust were changed in testing.
