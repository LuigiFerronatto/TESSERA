# #166 / #119 — One inspectable terminal interface

| Field | Value |
|---|---|
| Issue | [#166](https://github.com/LuigiFerronatto/TESSERA/issues/166), parent [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) |
| Record status | `IMPLEMENTED` |
| Capability type | `runtime`, CLI presentation |
| Pull request | [PR #298](https://github.com/LuigiFerronatto/TESSERA/pull/298) (merged) |
| Head commit | Final candidate `d40833c2a3293fc52ad508509936e5b98a207f3a` |
| Merge commit | `7566fc701a5227de18995cd8c01e556547bf886a` |
| Decision | `PENDING` lifecycle adoption |
| Benchmark applicability | `SMOKE_ONLY`, no retrieval/storage semantics changed |
| Last audited | 2026-10-12 |

## In one sentence

One terminal interface renders the same command results for humans, pipes and agents.

## What problem existed?

Each command selected text/Rich output independently. Most lacked JSON, an empty
query printed human prose despite `--json`, parser/config errors could leave
stdout empty, and no arguments produced a usage error. Rich and plain query output
showed different details and full-panel/full-body results were noisy.

## How did TESSERA behave before?

`query empty-store question --json` printed human prose; most commands rejected
`--json`; no-args startup returned a usage error and redirected query output always
printed full bodies. Baseline captures are checked in under `docs/process/evidence/166/`.

## What changed or is being tested?

A common `CommandResult`/`UiEvent` presentation boundary, centralized terminal
policy, Rich/plain/JSON renderers and stable operational errors. Legacy successful
JSON payloads remain intact. The no-args/status dashboard reads existing
configuration and Corpus Doctor state without rebuilding anything. Human query
results become compact, with `--full`/`--explain` available for detail.

Existing init now foregrounds the saved config and offers Keep/update, Change or
Cancel. The same #155 source picker/plan/apply semantics remain in charge; no new
source, provider, permission or persistence policy is hidden in the UI.

## How does it work now?

IMPLEMENTED ON `main`. Command results pass through a shared presentation
policy. JSON serializes existing semantic data; Rich/plain share message text.
Initialization consumes the unchanged #155 plan. Dashboard consumes read-only
Corpus Doctor diagnostics, without constructing an Engine or activating providers.

## Concrete example

```sh
tessera
tessera status --verbose
tessera query "Aurora project" --plain
tessera query "Aurora project" --full --explain
tessera --json query "Aurora project"
tessera init --project . --sources recommended --non-interactive --dry-run --json
```

## How was it validated?

The [output contract](../../reference/cli-output.md) documents modes, exit categories,
compatibility exceptions and future-surface boundaries. Checked-in evidence
contains an exhaustive parser inventory and actual before/after PTY/pipe captures
at 60/80/120 columns. Acceptance tests cover clean JSON on warnings/errors/empty
results, semantic renderer parity, literal terminal-safe source text, ASCII,
no-color, cancellation, repeated init and zero-mutation dry-run.

Local Python 3.12 regression passed: **624 passed, 8 skipped**; the new output
acceptance matrix accounts for 62 tests. Built wheel/sdist and installed-wheel
checks are recorded in the implementation PR; final candidate and canonical
CI are separately linked below. The unchanged
sanity gate reports Hit@1 0.75, Hit@3/5 1.0, MRR 0.875 and evidence hit rate 1.0.
No retrieval-quality improvement is claimed. The same-environment startup smoke
measured 1.146 s baseline / 1.100 s candidate median across five `--version` runs;
this is descriptive, not a statistically supported performance claim.

## Canonical delivery and check evidence

[PR #298](https://github.com/LuigiFerronatto/TESSERA/pull/298) merged on 2026-10-12. Final candidate
`d40833c2a3293fc52ad508509936e5b98a207f3a` and canonical merge
`7566fc701a5227de18995cd8c01e556547bf886a` are distinct identities for one delivery.

- Final-candidate [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38205377624)
  and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38205377619)
  completed successfully on `d40833c2a3293fc52ad508509936e5b98a207f3a`.
- Exact-canonical [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38205379993)
  and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38205379999)
  completed successfully on `7566fc701a5227de18995cd8c01e556547bf886a`.

These are historical engineering checks, not newly run benchmarks. The reviewed
PR discussion has no final-head formal reviews or accepted final-head KEEP
record. Earlier automatic BLOCK comments concern older candidates and are not
current-head defects. Current governance does not require a positive human or
automatic AI review. This correction records delivery and available validation;
it does not invent a retrospective approval or a new capability-adoption decision.

## What improved?

Commands now share a machine-output policy and semantic result source; automation
can parse empty and failed invocations without scraping text. Quiet/verbose and
no-color choices no longer alter evidence. Current human surfaces use English;
PT-BR translation remains explicitly unsupported rather than mixed accidentally.

## What remains unimplemented?

#119's integration/enrichment/review/intelligence taxonomy targets remain owned
by #177/#176/#19/#157–#165. No future capability is simulated in this delivery.
The numbered picker remains the supported parity path; optional full-screen
selection is separately owned by #351/#357. Progress is deliberately a delayed stable line, without animation.

## What is unlocked next?

The presentation contract is merged with successful exact candidate/canonical
checks. #119 retains its cross-capability taxonomy work; the newly reported
actionable-error/debug fixes belong to #356 and optional selection to #351/#357.
No dependent capability is promoted by this correction. Rollback requires no
data migration, source rewrite, model download or index schema change.

## Technical provenance

| Artifact | Evidence |
|---|---|
| Canonical base | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Prior init delivery | [PR #210](https://github.com/LuigiFerronatto/TESSERA/pull/210), merge `4c112195f1572bf352d1cc6a1042c69711381da8` |
| Prior Corpus Doctor delivery | [PR #277](https://github.com/LuigiFerronatto/TESSERA/pull/277), canonical base above |
| Output and scope contracts | [CLI_OUTPUT.md](../../reference/cli-output.md) |
| Terminal evidence | [captures](../evidence/166/terminal-snapshots.txt), [inventory](../evidence/166/command-inventory.json) |
| Decision / canonical merge | Adoption pending / `7566fc701a5227de18995cd8c01e556547bf886a` |

## Evolution

#112 banner + #117 configuration + #155 init + #13 read-only corpus diagnostics
→ canonical shared presentation implementation
→ successful exact candidate and canonical CI/ledger
→ lifecycle adoption and separately owned product follow-ups remain explicit
