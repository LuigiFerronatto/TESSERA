# 190 — Review and reverse runtime setup explicitly

| Field | Value |
|---|---|
| Issue | [#190](https://github.com/LuigiFerronatto/TESSERA/issues/190) |
| Record status | `IN_PROGRESS` |
| Capability type | runtime |
| Pull request | [Draft PR #317](https://github.com/LuigiFerronatto/TESSERA/pull/317) |
| Head commit | See draft PR exact head; not canonical |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

## In one sentence

A user can inspect the same setup plan through direct or guided commands, then
explicitly apply or undo supported JSON changes using the reviewed plan hash.

## What problem existed?

Setup needed a common current-to-desired plan and ownership-safe removal path;
a plausible config block alone did not prove safe installation or rollback.

## How did TESSERA behave before?

Base `20814a47ec0f72d7bea0639e0b057df1ecf5cded` has quickstart and #120 MCP,
without these shared setup entrypoints or transaction core. Unmerged #166/#196
candidates are not silently imported.

## What changed or is being tested?

Preview-by-default direct/guided commands, explicit scopes and store binding,
Claude/Gemini/Copilot JSON adapters, hash-bound CLI apply/remove/semantic undo,
and byte-exact in-process rollback. Codex has an inspected, pinned user-native
argv plan without TOML rewriting or client execution.

## How does it work now?

**TARGET — NOT YET ON MAIN**

Detection observes PATH/config evidence without launching clients or asserting
version compatibility. The SHA-256 binds the selected action, paths, config,
ownership, receipt, other-scope and mode guards. Mutation needs explicit `--apply
--plan-hash`. Durable undo stores only the prior managed entry/ownership metadata,
not unrelated config or credentials. CLI rollback is semantic; in-process
rollback is byte-exact. Transactions are per-file atomic and sequential across
runtimes, with explicit partial-success reporting, not crash-atomic globally.

## Concrete example

```bash
tessera integrate gemini --scope project --store-name shared-notes --json
tessera mcp setup --runtime gemini --scope project --store-name shared-notes --json
tessera integrate gemini --scope project --store-name shared-notes --apply --plan-hash <reviewed-hash> --json
tessera integrate gemini --scope project --rollback --json
```

The first two return identical plans/hashes and change zero files. The third
applies exactly the reviewed JSON action. The last previews a separately
hash-bound inverse. Codex project native scope gets a source-backed diagnostic.

## How was it validated?

`tests/test_issue_190_integration_setup.py` covers synthetic temporary configs:
parity, no provider execution, hash replay/staleness, idempotency, ownership,
legacy launcher updates, scope/precedence conflicts, Copilot wrapped/bare maps,
Codex argv-only plans, cross-process apply/remove/undo, secret-free receipts,
byte/mode restoration, absent files, malformed inputs, unsafe paths, caught
failures and preservation of detected concurrent edits.

The PR records final focused/full-suite counts, installed-wheel smoke and
exact-head deterministic CI. A test-only #95 flake was repaired: identifier
boundary matching replaces random substring matching, with 13 positive/negative
cases and neutral test IDs. Runtime behavior and its source inventory gate stay
unchanged. Sanity remains Hit@1 0.75, Hit@3/5 1.0, MRR 0.875 and evidence hit 1.0;
no retrieval-quality improvement is claimed.

## What improved?

One shared contract spans preview and explicit mutation. Fixture actions avoid
duplicate registrations, preserve unrelated config, refuse stale plans and
unsafe ownership, and keep unrelated credentials out of persisted undo metadata.

## What remains unimplemented?

Real client/version/OS acceptance, crash durability, controlled native Codex
execution, generic-client mapping, #171 semantic tools, #177/#196 lifecycle
integration and #257 automatic project identity remain outside this candidate.
The issue is not closed by synthetic correctness.

## What is unlocked next?

The setup mechanics are available for review and client acceptance. No downstream
semantic/hook dependency is marked satisfied.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#190](https://github.com/LuigiFerronatto/TESSERA/issues/190), including Copilot/portability comments |
| Pull request | [Draft PR #317](https://github.com/LuigiFerronatto/TESSERA/pull/317) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | [Boundaries and source pins](../INTEGRATION_SETUP.md); `PENDING` |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity, no retrieval changes |
| PR Evolution Audit | Existing #120 retained; #317 first adds previews/transactions, then hash-bound CLI and provider planning; no canonical #190 delivery claimed |

## Evolution

```text
manual/quickstart MCP config
→ shared previews and synthetic reversible transactions
→ explicit hash-bound JSON CLI actions and pinned native command plans
→ draft candidate; client acceptance and semantic/hook dependencies remain open
```
