# PR Evolution Audit — Issue #93 storage configuration parity

Audited starting main:
`5d43a2d4cdda0c17be6516f47920121070339d0f`, the canonical lifecycle merge
from PR #127. It includes the canonical #95 implementation merge
`6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`. Candidate branch:
`test-card/93-storage-config-parity`; [PR #129](https://github.com/LuigiFerronatto/TESSERA/pull/129).
The pre-reconciliation candidate was
`8f3827b39b6ceaf0a4b77a2a3ca8f63089032f5c`.

Issue #115 ran in parallel and later advanced `main` through PR #128 at
`b475f1cd805f86cc8ad9526e563e3c6fb8409ff1`. Before merge, the #93 branch was
rebased onto that newer canonical main. This preserves the original #93 audit
base as history while incorporating ADR 0002, the #115 evolution audit and Test
Card, repository-layout ownership findings, package/benchmark/test distribution
findings, and current #115/#116 routing. PR #128 is a parallel architecture delivery, not part of #93's capability delivery. The record remains
`IN_PROGRESS` and no #93 merge commit is claimed while PR #129 is open.

## Previous capability state

The historical Issue #93 baseline was true when written: quickstart emitted
`LAO_MEM_DIR`, CLI preferred it, and MCP read `TESSERA_STORAGE_DIR`. PR #126
later superseded that baseline for #95. Current main already has one shared
resolver, canonical-over-legacy precedence, a warning-backed compatibility
alias, generic `./memories`, canonical quickstart output, no implicit
`.claude/memory` quickstart selection and provider-independent MCP import.

The missing item was executable integration evidence. Running that evidence
exposed a separate exact-corpus defect: `TesseraEngine._iter_markdown_files()`
could supplement `storage_dir` with project/ancestor Markdown sources. In the
clean reproduction, a store at `/tmp/tessera-93-audit.../canonical-store`
reported the configured path correctly but also indexed `/tmp/pr95_body.md`
and `/tmp/issue95_evidence.md`. The selected directory therefore was not the
complete corpus boundary.

## Deliveries that established the current state

Candidate heads and canonical merge commits are one delivery per merged PR,
not separate capabilities.

| PR | Delivery type | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence | Supersedes |
|---|---|---|---|---|---|---|---|---|
| initial runtime | RUNTIME_IMPLEMENTATION | on main | `9cc8c38` and later refactor `cb8ed9d` | Engine, CLI, MCP, diagnostics | original storage/index runtime | introduced implicit project/ancestor source expansion | git blame and current-main reproduction | — |
| [#83](https://github.com/LuigiFerronatto/TESSERA/pull/83) | RUNTIME_IMPLEMENTATION | MERGED | `a6dc12cd3f9e40cf79302027710b5391377f6f26` | package metadata, MCP naming/config tests | TESSERA-native MCP and `TESSERA_STORAGE_DIR` | MCP only; CLI/quickstart still diverged | merged PR | legacy MCP key/name |
| [#98](https://github.com/LuigiFerronatto/TESSERA/pull/98) | RUNTIME_IMPLEMENTATION | MERGED | `fb23012ba4b2fddc3912d7cb593391a04fe45ae7` | Engine facade, CLI JSON, MCP query, parity tests | lossless retrieval-result parity | froze field/order/evidence projection without storage changes | #68 KEEP evidence | field-dropping MCP result |
| [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) | RUNTIME_IMPLEMENTATION | MERGED | `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05` | write gate, path validation, Python/CLI/MCP write surfaces | contained truthful writes | stable logical IDs and no write escape | #92 KEEP evidence | unsafe/ambiguous write result |
| [#126](https://github.com/LuigiFerronatto/TESSERA/pull/126) | RUNTIME_IMPLEMENTATION | MERGED | `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599` | config, CLI, MCP, diagnostics/quickstart, optional compatibility, docs/tests | shared storage resolver and generic runtime boundary | explicit → canonical → legacy warning → default; canonical quickstart; no `.claude/memory` discovery | audited candidate `1fcd71d`, #95 KEEP evidence, green CI | historical #93 configuration divergence; candidate and merge counted once |
| [#127](https://github.com/LuigiFerronatto/TESSERA/pull/127) | DOCUMENTATION_CORRECTION | MERGED | `5d43a2d4cdda0c17be6516f47920121070339d0f` | #95 audit/stage/roadmap/tests | lifecycle synchronization | #95 `VALIDATED`; #67 still `BLOCKED` | green lifecycle CI | stale post-merge state; no runtime delivery |
| [#128](https://github.com/LuigiFerronatto/TESSERA/pull/128) | ARCHITECTURE_DECISION | MERGED in parallel | `b475f1cd805f86cc8ad9526e563e3c6fb8409ff1` | ADR 0002, #115 audit/Test Card, roadmap and architecture assertions | accepted repository-layout and distribution ownership plan | no migrations; no #93 runtime hypothesis/result change | canonical current main incorporated by rebase | parallel #115 work; counted only as #115 delivery |
| Issue #93 candidate | RUNTIME_IMPLEMENTATION | OPEN | Not merged | Engine corpus iterator, golden integration, stage/audit/roadmap/docs assertions | exact configured-corpus boundary plus write-once/read-everywhere proof | removes only implicit out-of-store scanning; resolver/ranking/evidence/write contracts unchanged | 13 focused cases plus required regression/sanity/CI evidence | residual hidden corpus expansion |

## Current-main executable storage audit

Paths are compared as absolute resolved observations while retaining the #95
public resolver contract, whose fallback spelling is `./memories`.

| Scenario | Resolver / Python | CLI / doctor | Quickstart-generated MCP config | MCP bootstrap | Warning |
|---|---|---|---|---|---|
| explicit path only | explicit path | explicit path | canonical env containing that absolute path | generated canonical env selects it | none |
| `TESSERA_STORAGE_DIR` only | canonical path | canonical path | same canonical absolute path | canonical path | none |
| canonical + legacy | canonical path | canonical path | canonical only | canonical path | none |
| `LAO_MEM_DIR` only | legacy path | legacy path | translated to canonical key | legacy path | exactly one per resolving surface |
| neither variable | `./memories` under current project | same | absolute `<project>/memories` | same via generated config | none |
| existing `.claude/memory`, not selected | ignored; `./memories` | ignored | `<project>/memories` | same | none |
| explicit `.claude/memory` | accepted | accepted | canonical env containing explicit absolute path | same | none |

Warnings go to stderr; CLI/MCP JSON stdout remains parseable. MCP startup
constructs deterministic retrieval only and leaves its optional orchestrator
uninitialized.

## Original #93 criterion reconciliation

| Original success criterion | Re-audit classification | Evidence / action |
|---|---|---|
| Quickstart emits canonical configuration | already satisfied by #95 | PR #126 plus executable plan assertions |
| Python, CLI and MCP resolve the same path | satisfied at unit/contract level by #95; missing golden integration proof | seven matrix cases and golden subprocess test added |
| deterministic conflicting-variable precedence | already satisfied by #95 | shared resolver and real MCP/CLI cases |
| legacy fallback warns | already satisfied by #95 | exact one-warning stderr assertions retained/expanded |
| write once, read everywhere | still missing | golden Python write + Python/CLI/MCP equality added |
| selected store is the exact corpus | still broken | current-main ancestor/sibling leak reproduced; minimal iterator fix added |
| historical CLI-vs-MCP variable mismatch | obsolete/superseded | replaced by PR #126; not reimplemented |

## Candidate capability state

The Engine scans only Markdown files contained by `storage_dir`, recursively
when requested. It retains the existing derived-index and dependency-directory
exclusions. There is no ranking, scoring, graph, temporal, conflict, Evidence
Ledger, write-admission, path-validation or persistence-schema change.

Rebasing onto `b475f1c` did not change this implementation. The reconciled tree
contains both the complete #115/ADR 0002 architecture assertions from current
main and the additive #93 `IN_PROGRESS` audit/assertions.

The golden fixture resolves one absolute store, writes `issue-93/golden-storage-parity`
once through Python, builds once, and queries through Python, a real CLI
subprocess and actual MCP module startup. All three results are byte-equivalent
after JSON projection, contain exactly the stable ID, preserve #68 ordering and
structured evidence, and expose filepaths contained by the selected store.

## What remains unimplemented

- #115's repository-layout architecture decision is delivered through PR #128;
  its planned migrations remain unimplemented. Packaging execution remains
  owned by #116, which is not started here.
- #117 owns an explicit project/global registry and interactive initialization;
  removing a hidden heuristic does not implement a replacement registry.
- #120 owns the larger MCP/optional-adapter lifecycle; direct MCP tools and
  startup are used as they exist.
- Retrieval ranking, graph expansion, temporal/conflict behavior, Evidence
  Ledger semantics, write gate/admission, path containment and persistence
  schema remain unchanged.

## Benchmark before/after

Applicability is `SMOKE_ONLY`: configuration and corpus-boundary behavior
changed, not retrieval semantics. LongMemEval V1 dev-50 remains `NOT_RERUN`.

| Metric | Audited main | Candidate | Delta |
|---|---:|---:|---:|
| Hit@1 | 0.75 | 0.75 | 0.00 |
| Hit@3 | 1.00 | 1.00 | 0.00 |
| Hit@5 | 1.00 | 1.00 | 0.00 |
| MRR | 0.875 | 0.875 | 0.00 |
| Evidence hit rate | 1.00 | 1.00 | 0.00 |
| Missing-evidence check | passed | passed | unchanged |

No versioned file under `benchmarks/` is changed.

## Validation record

- Focused #93 integration: 13 passed.
- #95 runtime boundary: 16 passed; retrieval parity: 3 passed; architecture:
  8 passed; plain-language records: 7 passed; benchmark reporting: 51 passed.
- Full suite: 272 passed with 14 expected warnings. Compileall, `git diff
  --check` and the empty `benchmarks/` diff passed.
- [TESSERA CI 33428499798](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33428499798):
  Python 3.9/3.12, smoke and sanity all passed.
- [Benchmark Ledger 33428499819](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33428499819):
  passed; LongMemEval was skipped under `SMOKE_ONLY`.
- The first CI attempt exposed that core CI omits the optional MCP transport.
  The fixture now substitutes only decorator registration when absent; actual
  server bootstrap, resolution, Engine construction and tool calls remain real.
- Tests use temporary directories and subprocesses only. No provider, external
  service or network call occurs. Full Evidence/Learnings/Decision:
  [Issue comment](https://github.com/LuigiFerronatto/TESSERA/issues/93#issuecomment-5483152212).

## Newly unlocked work

None while the PR is open. #93 remains `IN_PROGRESS`. #67 remains `BLOCKED` on
#93 merge/lifecycle synchronization and regression-gate integration. Merging
#93 will satisfy only that named dependency; it will not itself implement or
start #67. The merged #115 architecture is preserved but not counted as #93;
#116, #117 and #120 are not started or absorbed.

## Roadmap evolution

```text
historical CLI/quickstart/MCP mismatch (#93 baseline)
→ partial canonical MCP naming (#83)
→ lossless result parity (#98)
→ contained writes (#108)
→ shared resolver/generic quickstart (#126)
→ #95 lifecycle synchronized (#127)
→ exact-corpus defect reproduced + golden #93 candidate from `5d43a2d`
→ parallel #115 architecture merge #128 / `b475f1c` advances main
→ #93 rebased additively onto `b475f1c` without changing its runtime result
→ merge/lifecycle synchronization required before #93 VALIDATED
→ #67 remains blocked on its separate regression-gate integration
```
