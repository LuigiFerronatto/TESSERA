# 190 — Review runtime setup before changing anything

| Field | Value |
|---|---|
| Issue | [#190](https://github.com/LuigiFerronatto/TESSERA/issues/190) |
| Record status | `IN_PROGRESS` |
| Capability type | runtime |
| Pull request | Draft candidate on `codex/issue-190-reversible-setup`; link added on publication |
| Head commit | See draft PR exact head; not canonical |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

## In one sentence

A user can inspect one consistent runtime setup plan through direct or guided
commands, while temporary-fixture tests prove reversible filesystem mechanics.

## What problem existed?

Setup needed a common current-to-desired plan and an ownership-safe removal path;
writing a plausible JSON block alone did not prove safe installation or rollback.

## How did TESSERA behave before?

Canonical base `20814a47ec0f72d7bea0639e0b057df1ecf5cded` provides the existing
quickstart and #120 MCP server. It has neither these direct/guided entrypoints nor
this setup transaction core. #166/#196 unmerged candidates are not dependencies
silently imported by this work.

## What changed or is being tested?

The candidate adds read-only direct and guided plans over one implementation,
strict Claude/Gemini JSON document planning, fingerprint-based ownership,
explicit scopes, and an opt-in experimental filesystem apply/rollback API.

## How does it work now?

**TARGET — NOT YET ON MAIN**

Detection observes PATH and known config files without launching clients or
claiming version compatibility. Plans show exact owned-entry changes and safe
rollback prerequisites. A named store avoids committed machine-specific paths.
The filesystem API uses per-file atomic replacements, checks stale snapshots,
and restores completed writes after caught failures without overwriting edits.
It does not promise crash-atomic multi-file commits; CLI apply stays unavailable.

## Concrete example

```bash
tessera integrate claude --scope project --store-name shared-notes --dry-run --json
tessera mcp setup --runtime claude --scope project --store-name shared-notes --dry-run --json
```

Both emit the same structured plan and change zero files. A Codex or Copilot
selection gives an explicit unavailable-adapter diagnostic instead of guessed config.

## How was it validated?

`tests/test_issue_190_integration_setup.py` exercises synthetic temporary configs:
plan parity; no client execution; ownership/idempotency; updates/removal; byte and
mode restoration; absent files/directories; stale config/owner/other-scope guards;
intervening edits; caught write failures and partial recovery; lock/symlink/hardlink/
special-file rejection; malformed/redacted JSON; and portable descriptor generation.
Final local/full-suite and exact-head CI evidence are recorded in the draft PR.
Deterministic sanity remains Hit@1 0.75, Hit@3/5 1.0, MRR 0.875, evidence hit 1.0;
this work changes no retrieval behavior and claims no quality gain.

## What improved?

Reviewable direct/guided plans share one result. Fixture setup does not duplicate
entries, remove another server, leak credentials into the preview/ownership
record, or overwrite a detected intervening edit during rollback.

## What remains unimplemented?

Real client/version/OS acceptance, CLI apply, crash-durable transactions, Codex
TOML/Copilot/generic adapters, #171 semantic tools, #177/#196 lifecycle integration,
and #257 automatic project identity remain unimplemented. This is a bounded
candidate, not completion or closure of #190.

## What is unlocked next?

A reviewable setup-plan contract and isolated filesystem experiments are ready
for review. No downstream semantic/hook dependency is declared satisfied.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#190](https://github.com/LuigiFerronatto/TESSERA/issues/190), including its Copilot/portability comments |
| Pull request | Draft candidate; see publication evidence |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | [Detailed boundaries and source pins](../INTEGRATION_SETUP.md); `PENDING` |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity, no retrieval changes |
| PR Evolution Audit | Existing #120 baseline retained; no #190 implementation on the audited canonical base; this is the first bounded candidate in this delivery |

## Evolution

```text
manual/quickstart MCP configuration
→ shared inspectable setup plan + temporary-fixture reversible transactions
→ draft candidate only
→ actual client acceptance and semantic/hook dependencies still required
```
