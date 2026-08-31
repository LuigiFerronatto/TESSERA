# 95 — TESSERA stops assuming it lives inside one project

| Field | Value |
|---|---|
| Issue | [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | Candidate branch pending publication |
| Head commit | Pending final candidate commit |
| Merge commit | Not merged |
| Decision | `PENDING` |
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

**TARGET — NOT YET ON MAIN.** Deterministic import, indexing, retrieval, help,
doctor and quickstart do not activate or probe LAO/Blip behavior. A legacy user
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
provider probing, explicit compatibility, typed failure and foreign schema.
The full Engine/CLI/MCP, #92 write/path, docs and benchmark reporting suites,
Python 3.9/3.12 CI, smoke and deterministic sanity evaluation are required.
Exact final counts and CI links will be recorded on the PR and Issue #95 before
the candidate is handed to the maintainer.

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

After merge and lifecycle synchronization, #95's dependency edge is satisfied
for #67 and #115. #67 remains blocked on #93 and regression-gate integration;
#115 must not start before this candidate is merged.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) |
| Pull request | Candidate pending publication |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Pending final Issue #95 comment |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity output in PR evidence |
| PR Evolution Audit | [`docs/PR_EVOLUTION_95.md`](../PR_EVOLUTION_95.md) |

## Evolution

```text
project-coupled defaults
→ #95 generic runtime + explicit compatibility candidate
→ IN_PROGRESS until audited merge
→ #115/#117/#120 productization work under their own cards
```
