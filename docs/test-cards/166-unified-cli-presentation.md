# #166 / #119 — One inspectable terminal interface

| Field | Value |
|---|---|
| Issue | [#166](https://github.com/LuigiFerronatto/TESSERA/issues/166), parent [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime`, CLI presentation |
| Pull request | Draft candidate, linked in submission evidence |
| Head commit | See draft PR exact-head checks |
| Merge commit | Not merged |
| Decision | `PENDING` human review |
| Benchmark applicability | `SMOKE_ONLY`, no retrieval/storage semantics changed |
| Last audited | 2026-10-02 |

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
printed full bodies. Baseline captures are checked in under `docs/evidence/166/`.

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

TARGET — NOT YET ON MAIN. Command results pass through a shared presentation
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

The [output contract](../CLI_OUTPUT.md) documents modes, exit categories,
compatibility exceptions and future-surface boundaries. Checked-in evidence
contains an exhaustive parser inventory and actual before/after PTY/pipe captures
at 60/80/120 columns. Acceptance tests cover clean JSON on warnings/errors/empty
results, semantic renderer parity, literal terminal-safe source text, ASCII,
no-color, cancellation, repeated init and zero-mutation dry-run.

Local Python 3.12 regression passed: **624 passed, 8 skipped**; the new output
acceptance matrix accounts for 62 tests. Built wheel/sdist and installed-wheel
checks are recorded in the draft PR, alongside final exact-head CI. The unchanged
sanity gate reports Hit@1 0.75, Hit@3/5 1.0, MRR 0.875 and evidence hit rate 1.0.
No retrieval-quality improvement is claimed. The same-environment startup smoke
measured 1.146 s baseline / 1.100 s candidate median across five `--version` runs;
this is descriptive, not a statistically supported performance claim.

## What improved?

Commands now share a machine-output policy and semantic result source; automation
can parse empty and failed invocations without scraping text. Quiet/verbose and
no-color choices no longer alter evidence. Current human surfaces use English;
PT-BR translation remains explicitly unsupported rather than mixed accidentally.

## What remains unimplemented?

#119's integration/enrichment/review/intelligence taxonomy targets remain owned
by #177/#176/#19/#157–#165. No future capability is simulated in this delivery.
Full-screen selectors are not necessary: the numbered picker is the supported
parity path. Progress is deliberately a delayed stable line, without animation.

## What is unlocked next?

Revert this presentation-only candidate if the output contract fails review.
No data migration, source rewrite, model download or index schema change is needed.
After merge and canonical validation, future owning cards can emit this shared
result/event contract, while #119 retains its cross-capability taxonomy work.

## Technical provenance

| Artifact | Evidence |
|---|---|
| Canonical base | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Prior init delivery | [PR #210](https://github.com/LuigiFerronatto/TESSERA/pull/210), merge `4c112195f1572bf352d1cc6a1042c69711381da8` |
| Prior Corpus Doctor delivery | [PR #277](https://github.com/LuigiFerronatto/TESSERA/pull/277), canonical base above |
| Output and scope contracts | [CLI_OUTPUT.md](../CLI_OUTPUT.md) |
| Terminal evidence | [captures](../evidence/166/terminal-snapshots.txt), [inventory](../evidence/166/command-inventory.json) |
| Decision / canonical merge | Pending review / not merged |

## Evolution

#112 banner + #117 configuration + #155 init + #13 read-only corpus diagnostics
→ this presentation candidate
→ human review and exact-head CI
→ canonical lifecycle reconciliation before dependent capability adoption
