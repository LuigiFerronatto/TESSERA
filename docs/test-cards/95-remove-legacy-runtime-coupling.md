# 95 — TESSERA stops assuming it lives inside one project

| Field | Value |
|---|---|
| Issue | [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [#126](https://github.com/LuigiFerronatto/TESSERA/pull/126) |
| Head commit | [`1fcd71d`](https://github.com/LuigiFerronatto/TESSERA/commit/1fcd71df95993cfbfd8b8fe1e833fa879e947930) audited candidate |
| Merge commit | [`6d4a32b`](https://github.com/LuigiFerronatto/TESSERA/commit/6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599) canonical merge commit; its tree matches the audited candidate |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA previously behaved as if it still lived inside one specific project;
it now uses generic defaults and treats that project only as an explicit,
deprecated compatibility integration.

## What problem existed?

An ordinary CLI or quickstart could mention or select a legacy project path,
and asking for an optional model could silently inspect that project's gateway
credentials and source tree. That made a standalone install surprising and
made provider failure look like successful raw-prompt output.

## How did TESSERA behave before?

```text
no CLI path
→ LAO_MEM_DIR
→ maybe .claude/memory during quickstart

optional assisted call
→ hard-coded gateway preference
→ parent-directory engine-router search
→ raw prompt echo on failure
```

## What changed or is being tested?

One shared resolver enforces explicit path → `TESSERA_STORAGE_DIR` → deprecated
alias → `./memories`. Doctor and quickstart are neutral. Optional resolution
does nothing unless an adapter is explicitly selected; the legacy adapters
require explicit configuration and raise actionable errors.

## How does it work now?

**CURRENT ON MAIN.** Deterministic import, indexing, retrieval, help, doctor and
quickstart do not activate or probe LAO/Blip behavior. A legacy user
can temporarily keep `LAO_MEM_DIR` with one warning or explicitly select the
deprecated compatibility adapter and supply its endpoint/router path.

## Concrete example

```bash
export TESSERA_STORAGE_DIR="$PWD/memories"
tessera doctor
tessera quickstart
```

Both surfaces use the canonical generic storage. If `LAO_MEM_DIR` is the only
variable, it still works for migration but prints an actionable deprecation
warning to stderr, leaving JSON stdout valid.

## How was it validated?

Focused #95 tests cover the behavior matrix, warning channel, no discovery or
provider probing, explicit compatibility, typed failure and foreign schema:
16 focused tests passed. The full local suite passed 257 tests; #92 write/path
passed 67, persistence 15, retrieval parity 3, documentation contracts 13 and
benchmark reporting 51. Compileall and diff checks passed. Sanity remained
Hit@1 0.75, Hit@3/5 1.00, MRR 0.875, evidence hit rate 1.00 and missing-evidence
check passed. Python 3.9/3.12, smoke, sanity and reporting CI links are recorded
on PR #126 and in the Issue #95 evidence.

## What improved?

- Generic users see only TESSERA defaults.
- Canonical configuration deterministically outranks the alias.
- Existing users have a warning-backed, explicit migration route.
- Provider and project-file probing cannot occur in the default path.
- Backend failures cannot masquerade as a model response.

## What remains unimplemented?

#93 still owns full configuration parity; #115 owns layout; #117 owns
registry/interactive discovery; #120 owns MCP lifecycle and the larger adapter
envelope; #78 owns residual historical/current narrative cleanup. Those remain
separate.

## What is unlocked next?

#95 satisfies its dependency edge for #67 and #115. #67 remains `BLOCKED` on
#93 and regression-gate integration. Because #74, #95 and #112 are satisfied,
#115 becomes `READY`. No unrelated Test Card becomes ready.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) |
| Pull request | [#126](https://github.com/LuigiFerronatto/TESSERA/pull/126) |
| Audited candidate | [`1fcd71d`](https://github.com/LuigiFerronatto/TESSERA/commit/1fcd71df95993cfbfd8b8fe1e833fa879e947930) |
| Canonical merge | [`6d4a32b`](https://github.com/LuigiFerronatto/TESSERA/commit/6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599) |
| Evidence/Learnings/Decision | [Superseding pre-merge KEEP evidence](https://github.com/LuigiFerronatto/TESSERA/issues/95#issuecomment-5480777109) |
| Post-merge audit | [Maintainer audit](https://github.com/LuigiFerronatto/TESSERA/issues/95#issuecomment-5482216967) |
| Implementation CI | [TESSERA CI 33410027311](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33410027311), [Benchmark Ledger 33410027344](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33410027344) |
| Benchmark record | `SMOKE_ONLY`; unchanged deterministic sanity output in implementation evidence |
| PR Evolution Audit | [`docs/PR_EVOLUTION_95.md`](../PR_EVOLUTION_95.md) |

## Evolution

```text
project-coupled defaults
→ PR #126 candidate `1fcd71df95993cfbfd8b8fe1e833fa879e947930`
→ canonical merge `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`
→ VALIDATED
→ #115 READY
→ later #117/#120 work under their own cards
```
