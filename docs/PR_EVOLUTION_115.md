# PR Evolution Audit — Issue #115 repository layout

Audited starting `main`:
`5d43a2d4cdda0c17be6516f47920121070339d0f`, fetched from `origin/main`
before the branch was created. It includes canonical #95 runtime merge
`6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599` and canonical #95 lifecycle merge
`5d43a2d4cdda0c17be6516f47920121070339d0f`.

Candidate branch: `test-card/115-repository-layout-audit`;
[PR #128](https://github.com/LuigiFerronatto/TESSERA/pull/128). Audited content
candidate: `874fea2a1f06efbac43ea4a8c7414509306cbe1c`. This audit counts a
candidate head and its later canonical merge as one delivery. It does not treat
lifecycle-only PRs as new runtime capability.

## Audit method

The audit combined tracked-tree enumeration, file-size/type inspection, AST
import parsing, manual source inspection, package metadata and entry-point
inspection, text/path/subprocess reference searches, CI inspection, Markdown
and HTML asset link resolution, pytest collection, Git history/PR inspection
and a clean detached-worktree build. Grep results were evidence inputs, not the
sole ownership test.

The repository has 146 tracked files: `.github/` 4, `archive/` 4,
`benchmarks/` 28, `docs/` 58, `examples/` 1, `tessera/` 25, `tests/` 20 and six
top-level files.

## Top-level ownership inventory

| Path/family | Current classification | Evidence and references | Runtime reachable? | Packaged today? | Proposed action |
|---|---|---|---|---|---|
| `.github/` | `CI_GOVERNANCE` | two templates; CI runs package tests, smoke and sanity; benchmark workflow reads constraints/results/reporting | no | no | KEEP |
| `.gitignore` | `BUILD_CONFIGURATION` | controls local benchmark datasets/results and Python artifacts | no | no | KEEP |
| `CHANGELOG.md` | `CURRENT_DOCUMENTATION` | root/docs links; curated by change policy | metadata reads only via repository README link | no | KEEP |
| `README.md` | `CURRENT_DOCUMENTATION`, package metadata input | `project.readme`; root navigation and brand SVG reference | metadata only | content embedded in METADATA; physical file in sdist | KEEP |
| `archive/` | `HISTORICAL_PROVENANCE` | README maps v1/v2/v3 lineage; `CODE_EXPLANATION` and PR audits refer to it; no imports | no | no | KEEP |
| `benchmarks/sanity/` | `BENCHMARK_TOOLING` | CI and roadmap invoke runner; imports public `tessera` | no reverse edge | no | KEEP repository-only |
| `benchmarks/longmemeval_v1/` | `BENCHMARK_TOOLING` | benchmark runner/tests/workflow; imports public `tessera`; constraints/setup/README omitted from artifacts | no reverse edge | Python files in wheel/sdist | SPLIT from distribution in #116 |
| `benchmarks/reporting/` | `BENCHMARK_TOOLING` | workflow and reporting tests; depends on LongMemEval runner | no reverse edge | Python files in wheel/sdist | SPLIT from distribution in #116 |
| `benchmarks/results/` | `HISTORICAL_PROVENANCE`, benchmark ledger | roadmap/Test Cards/workflow/tests reference records and schemas | no | no | KEEP repository-only |
| `docs/` current contract/reference set | `CURRENT_DOCUMENTATION` | README/docs map/tests link contracts, ADRs and roadmap | no | no | KEEP |
| `docs/adr/`, `docs/test-cards/`, `docs/PR_EVOLUTION_*`, research trace | `HISTORICAL_PROVENANCE`, governance | lifecycle tests and roadmap; exact decision evidence | no | no | KEEP |
| dated narratives and `docs/slides/` | `HISTORICAL_PROVENANCE`, `CANDIDATE_MOVE` | docs map labels historical; #78 owns naming cleanup; slide HTML resolves 25 local assets | no | no | MOVE together under explicit history only through #78 |
| `docs/assets/brand/` | `CURRENT_DOCUMENTATION` asset | root README renders small hero; asset README records canonical variants | no | no | KEEP |
| `examples/quickstart.py` | `EXAMPLE` | imports public package; referenced by its usage line and project docs | client only | no | KEEP repository-only; validate in #118 |
| `install.sh` | `DEV_TOOLING`, onboarding compatibility | installs extras, checks console commands, references current docs; no package import | installation path | no | DEFER to #118 |
| `pyproject.toml` | `BUILD_CONFIGURATION` | declares package, extras, scripts, exact package list and package data | build-time | included in sdist | KEEP; harden in #116 |
| `tessera/` | `PACKAGE_RUNTIME`, `PUBLIC_API`, `CLI_SURFACE`, `MCP_ADAPTER`, `OPTIONAL_INTEGRATION`, `PACKAGE_DATA` | runtime graph, tests, console scripts and examples | yes | all 25 files | KEEP; clarify sub-boundaries in owners |
| `tessera_mcp_server.py` | `ACTIVE_COMPATIBILITY`, `CANDIDATE_DELETE` | one-way import to `tessera.mcp_server.main`; no in-repo caller or docs command; console script replaces it | only if invoked directly | no | DEFER deprecation/deletion to #120 |
| `tests/` | `TEST_ONLY` | 258-test current suite; imports runtime and benchmark tools; docs tests inspect repository paths | no | 18 modules in sdist | SPLIT from release artifact in #116 |

## Python dependency and reference graph

The AST pass found 128 internal import edges. The ownership-relevant graph is:

```text
examples ───────────────┐
tests ──────────────────┼──> tessera public and selected internal contracts
benchmarks/sanity ──────┤
benchmarks/longmemeval ─┘

benchmarks/reporting ─────> benchmarks/longmemeval
tessera_mcp_server.py ────> tessera.mcp_server

tessera.cli ──────────────> config, engine, models, orchestrator, skills,
                            optional llm bridge, display/diagnostics
tessera.mcp_server ───────> config, engine, evidence, hooks, models,
                            optional llm bridge, diagnostics
optional orchestration ───> deterministic engine contract
engine facade ────────────> engine_core + evidence
engine_core ──────────────> canonical + conflict + models + security
skills installer ─────────> engine + importlib.resources(package data)
```

No `tessera/` module imports `benchmarks`, `tests`, `examples`, `docs` or
`archive`. The four dynamic internal imports are test-only imports of
`tessera.mcp_server`; production dynamic import inspection is limited to
standard-library metadata/resources and the explicit legacy adapter loader.

### Non-import references

- `pyproject.toml` maps `tessera` and `tessera-mcp` to packaged functions and
  explicitly declares three benchmark packages.
- CI directly invokes `benchmarks/sanity/ci_eval.py`; the benchmark workflow
  imports reporting modules and reads constraints plus versioned result records.
- `tessera/skills.py` loads `skills_library/*.md` using package resources;
  CLI and orchestrator tests require all five files.
- `README.md` references the current brand SVG, docs and benchmark ledgers.
- `docs/CODE_EXPLANATION.md` links `archive/README.md`; the docs map labels
  dated narratives and presentation material rather than claiming current APIs.
- all 25 local references in `docs/slides/tessera-apresentacao.html` resolve to
  versioned assets. Moving the deck without assets would break it.
- 112 non-placeholder local Markdown links resolve. The single mechanical
  “missing” target is literal sample text `(...)` in `CHANGE_POLICY.md`, not a
  link dependency.
- `install.sh` is a repository bootstrap surface and refers to console scripts
  and documentation; it is not used by wheel installation.

## Clean build inventory

The build ran from a detached clean worktree at audited main with Python 3.12,
`build`, setuptools and wheel in isolated environments:

```text
python -m build
Successfully built tessera-3.4.0.tar.gz and tessera-3.4.0-py3-none-any.whl
```

Setuptools also warned that the table-form license and license classifier are
deprecated, and that `tessera.skills_library` is an importable data directory
absent from the explicit package list. The data was included, but the
configuration is ambiguous. #116 owns both warnings.

The metadata correctly names TESSERA, describes its current memory/evidence
role, declares Python 3.9+, keeps provider support out of base dependencies and
points both console scripts at packaged modules. It is not yet a complete
release contract: benchmark packages have no benchmark extra/dependency set,
the license declaration is deprecated and has no tracked license file, and the
long README embedded as distribution metadata contains repository-relative
links to docs/assets that are not shipped. These are packaging findings for
#116, not reasons to change metadata in #115.

### Wheel — 46 files

| Family | Count | Exact contents |
|---|---:|---|
| `tessera/*.py` | 20 | `__init__`, `canonical`, `cli`, `config`, `conflict`, `decomposer`, `diagnostics`, `display`, `engine`, `engine_core`, `episode_boundary`, `evidence`, `hooks`, `legacy_compat`, `llm_bridge`, `mcp_server`, `models`, `orchestrator`, `security`, `skills` |
| `tessera/skills_library/*.md` | 5 | docker environment, runtime verification, schema compliance, service lifecycle, shell execution |
| `benchmarks/longmemeval_v1/*.py` | 7 | `__init__`, `adapter`, `dataset`, `metrics`, `prepare_dataset`, `run`, `schemas` |
| `benchmarks/reporting/*.py` | 8 | `__init__`, `applicability`, `cli`, `compare`, `environment`, `records`, `render`, `schema` |
| `benchmarks/__init__.py` | 1 | benchmark namespace root |
| `.dist-info` | 5 | METADATA, RECORD, WHEEL, entry points, top-level names |

All required runtime Python and current Skills data are present. Unexpected:
all 16 benchmark implementation modules. Missing from that accidentally shipped
benchmark surface: its READMEs, constraints, setup shell, sanity runner, result
schemas/records and benchmark dependency declaration. This is an incomplete
tool, not an intentional distributable benchmark product.

Docs, tests, examples, archives, slide/assets, `install.sh`, `CHANGELOG.md`,
`pyproject.toml` and `tessera_mcp_server.py` are absent from the wheel as expected.
The root README text is represented inside package METADATA rather than as a
standalone wheel file. No required runtime file is missing.

### Sdist — 69 files

The exact families are:

- package metadata/build: `PKG-INFO`, `README.md`, `pyproject.toml`, generated
  `setup.cfg` and six `tessera.egg-info/*` files;
- the same 25 `tessera/` runtime/data files;
- the same 16 benchmark Python files; and
- 18 `tests/test_*.py` modules.

The sdist omits `tests/conftest.py` and `tests/stress_test.py`, so its test set is
not self-contained. It also omits all benchmark non-Python support listed above,
docs, archive, examples, CI, assets, changelog, installer and top-level MCP shim.
No source required to rebuild the current wheel is missing, but the sdist is not
a complete repository/source-evidence bundle. #116 must define whether tests
belong in the sdist; ADR 0002's target is exclusion from release artifacts.

The 18 exact test paths in the sdist are:

```text
tests/test_architecture_boundary_docs.py
tests/test_benchmark_reporting.py
tests/test_canonical.py
tests/test_canonical_compatibility.py
tests/test_contract_regression.py
tests/test_engine.py
tests/test_evidence_ledger.py
tests/test_issue_95_runtime_boundary.py
tests/test_longmemeval_v1.py
tests/test_memory_architecture.py
tests/test_orchestrator.py
tests/test_persistence_format_contract.py
tests/test_plain_language_test_card_docs.py
tests/test_project_agnostic_runtime.py
tests/test_retrieval_contract_parity.py
tests/test_retrieval_ranking_evidence.py
tests/test_tessera_banner_brand.py
tests/test_write_gate_contract.py
```

The exact remaining sdist-only build/metadata paths are `PKG-INFO`, `README.md`,
`pyproject.toml`, generated `setup.cfg`, and `tessera.egg-info/{PKG-INFO,
SOURCES.txt,dependency_links.txt,entry_points.txt,requires.txt,top_level.txt}`.
Together with the exact wheel package paths above, this accounts for all 69
sdist files without treating generated container prefixes as repository paths.

## Detailed ownership/action matrix

| Path | Current owner/status | Imported/referenced by | Runtime reachable? | Packaged? | Tests? | Docs? | Historical? | Action | Migration / rollback |
|---|---|---|---|---|---|---|---|---|---|
| `tessera/{canonical,conflict,engine,engine_core,evidence,models,security}.py` | `ACTIVE_RUNTIME`, deterministic core | public API, CLI/MCP, tests, benchmarks | yes | wheel+sdist | required | current contracts | no | KEEP | no move in #115; rollback any later module move if public imports/artifact tests fail |
| `tessera/{config,diagnostics,display,cli}.py` | `CLI_SURFACE` / runtime support | console entry point, tests, installer guidance | yes | wheel+sdist | required | current CLI docs | no | KEEP | #117/#119 own config/UX; preserve command compatibility |
| `tessera/mcp_server.py` | `MCP_ADAPTER` | console entry point, dynamic tests, docs | optional | wheel+sdist | required | current MCP docs | no | KEEP | #120 owns protocol/subpackage change; rollback to module entry point |
| `tessera/{orchestrator,hooks,decomposer,llm_bridge,legacy_compat,episode_boundary}.py` | `OPTIONAL_INTEGRATION`, some `ACTIVE_COMPATIBILITY` | CLI/MCP assisted paths and tests | explicit/optional | wheel+sdist | required | ADR 0001 | partial compatibility | DEFER/SPLIT | #116/#120 may clarify package boundary; compatibility imports and warnings required before move |
| `tessera/skills.py` + `skills_library/` | `ACTIVE_RUNTIME`, `PACKAGE_DATA`, not official #121 Skills | public export, CLI, tests, package-data declaration | yes | wheel+sdist | required | current skills docs | no | DEFER/SPLIT | #121 owns versioned replacement; keep old IDs/CLI during migration; rollback to these five resources |
| `tessera_mcp_server.py` | `ACTIVE_COMPATIBILITY`, candidate stale shim | no in-repo caller; direct invocation only | explicit script | no | no | no current command | lineage from initial commit | DEFER then DELETE candidate | #120 deprecation/usage check; restore from audited main |
| `benchmarks/sanity/` | `DEV_ONLY`, benchmark smoke | CI, roadmap | client of runtime | no | benchmark reporting indirectly | yes | results are evidence | KEEP | repository path can move only with CI/docs updates; restore prior path |
| `benchmarks/longmemeval_v1/` | `DEV_ONLY`; accidentally packaged | tests, workflow, reporting | client only | partial wheel/sdist | required | README/roadmap | evaluation history | SPLIT | #116 excludes from artifact; keep repository imports; revert pyproject declaration if build gate fails |
| `benchmarks/reporting/` | `DEV_ONLY`; accidentally packaged | tests/workflow | no | wheel+sdist | required | benchmark docs | governance evidence | SPLIT | same #116 boundary and rollback |
| `benchmarks/results/` | `HISTORICAL_PROVENANCE` / active ledger | workflow, tests, Test Cards, roadmap | no | no | required | required | yes | KEEP | never delete without superseding ledger and named commit |
| `tests/` | `TEST_ONLY`; unexpectedly partial sdist | pytest/CI | no | 18/20 in sdist | itself | docs contract tests | some fixtures preserve compatibility | SPLIT | #116 artifact exclusion; repository tests remain; rollback manifest config |
| `examples/quickstart.py` | `EXAMPLE` | human use | public client | no | no direct test | referenced conceptually | no | KEEP | #118 should execute against wheel; restore path/docs on move |
| current docs listed in `docs/README.md` | `CURRENT_DOCUMENTATION` | root/docs navigation and static tests | no | no | docs tests | yes | some decision history | KEEP | link checker before/after any reorg |
| `docs/{COMO-FUNCIONA-E-PROXIMOS-PASSOS,ROTEIRO-DEMO-VIDEO,QUMEM-GAP-ANALYSIS}.md` | `STALE_BUT_REFERENCED` or `HISTORICAL_PROVENANCE` | docs map, tests, PR audits | no | no | path assertions | yes | yes | MOVE/ARCHIVE | #78 classifies content, rewrites links/tests; restore from prior commit |
| `docs/slides/` | `HISTORICAL_PROVENANCE`, presentation bundle | docs map/audits; HTML → 25 local assets | no | no | legacy-reference test | yes | yes | MOVE/ARCHIVE | move HTML and assets atomically under #78; rollback whole directory |
| `docs/assets/brand/` | `CURRENT_DOCUMENTATION` asset | README HTML image | no | no | identity docs | yes | canonical brand history | KEEP | change root README and variants together |
| `archive/legacy/` | `HISTORICAL_PROVENANCE`, not dead | archive README, code explanation, audits | no | no | reference guard | yes | yes | KEEP | no deletion; recovery baseline named above |
| `install.sh` | `DEV_ONLY`, onboarding compatibility | direct human invocation | install-time | no | no | dated docs | no | DEFER | #118 owns replacement/retirement; preserve documented command or migration note |
| `.github/workflows/` | `CI_GOVERNANCE` | GitHub Actions | no | no | invokes suite | docs describe gates | run history | KEEP | update atomically with moved tool paths; revert workflow commit |

## Duplicate and stale findings

| Finding | Status | Evidence | Decision |
|---|---|---|---|
| root `tessera_mcp_server.py` versus packaged `tessera.mcp_server` console entry point | `ACTIVE_COMPATIBILITY` / potentially stale | one-line forwarding implementation; no repository reference; existed since initial commit | DEFER to #120; not safe to delete from internal evidence alone |
| benchmark packages in explicit setuptools list | `DEV_ONLY` accidentally distributed | no runtime reverse import; incomplete wheel contents; introduced by PRs #99/#102 for test imports | SPLIT in #116 |
| tests in sdist | `DEV_ONLY`, inconsistent artifact | 18 tests included, fixtures/stress omitted | SPLIT in #116 |
| `skills_library` versus planned official Skills | `ACTIVE_RUNTIME`, not duplicate capability | CLI/package resources/tests use current procedural anchors; #121 describes a different versioned integration layer | DEFER/SPLIT in #121 |
| v2 and v3 archive engines versus current modules | `HISTORICAL_PROVENANCE`, not copied active runtime | no imports; archive README and current docs explain lineage/delta | KEEP |
| dated docs mixed with current docs | `STALE_BUT_REFERENCED` and `HISTORICAL_PROVENANCE` | docs map labels precedence; tests/audits link paths | MOVE/ARCHIVE only through #78 |
| slides and legacy brand assets | `HISTORICAL_PROVENANCE` | self-contained deck with resolving local assets; not product docs | MOVE bundle through #78; no deletion |
| explicit package list and importable data directory warning | `BUILD_CONFIGURATION` ambiguity | clean build warning; data still included | #116 fixes declaration and tests installed resources |
| license metadata without repository license file | `BUILD_CONFIGURATION` / release gap | `license = {text = "MIT"}`; clean build deprecation; no `LICENSE*` tracked | #116 decides SPDX/license-file contract |

No path is classified `DEAD` with enough evidence for immediate deletion.

## KEEP / MOVE / ARCHIVE / DELETE / SPLIT / DEFER decisions

| Decision | Candidates | Why / prerequisites | Failure impact | Rollback | Owner |
|---|---|---|---|---|---|
| KEEP | root package layout, runtime package, current docs/brand, benchmarks repository tree, ledgers, tests repository tree, examples, CI, archive | active contracts, clients or provenance | broken API/tests/docs/evidence if removed | restore from audited main | ongoing / #116 verification |
| MOVE | dated narratives and slides to explicit docs history | current/history clarity; first classify in #78, update every link/test and keep slide bundle intact | broken links or loss of context | revert move commit | #78 |
| ARCHIVE | dated demo/research narrative within docs history | presentation/research provenance remains valuable | mistaken current guidance if unlabeled; evidence loss if deleted | revert archive commit | #78 |
| DELETE | none approved now; root MCP shim is eventual candidate | must meet all ADR deletion gates plus a deprecation window | downstream direct script users break | restore file from `5d43a2d...` | #120 |
| SPLIT | benchmark packages and tests from distributions; current procedural anchors from future official Skills contract | direction of dependency and artifact purpose differ | installed package bloat/incomplete tools; Skills compatibility break if rushed | revert packaging or Skills migration commit | #116, #121 |
| DEFER | optional integration subpackage shape, installer retirement, MCP shim, exact docs-history paths | existing cards own public/config/protocol/onboarding decisions | duplicate ownership and hidden behavior change | no change in #115 | #117–#121, #78 |

## Migration stages and test/rollback gates

| Stage | Scope/files | Dependencies | Validation | Benchmark | Rollback | Card |
|---|---|---|---|---|---|---|
| 1 | `pyproject.toml`, artifact tests; exclude `benchmarks` and partial tests while retaining all `tessera` data/entry points; resolve metadata warnings | merged/lifecycle-synced #115 | Python 3.9/3.12 clean wheel+sdist inventory, wheel install, imports, CLI/MCP extra, Skills resources | `SMOKE_ONLY` | revert packaging commit; compare artifacts to this inventory | #116 |
| 2 | clean bootstrap, installer/examples and config consumers | #116, #117 | artifact install/init/doctor/query/uninstall matrix | `SMOKE_ONLY` | preserve previous installer command and config migration | #117/#118/#119 |
| 3 | MCP/optional adapter placement and top-level shim deprecation | #116/#117 plus #120 dependencies | protocol-level clean-wheel tests, deprecation test, zero core provider import | `SMOKE_ONLY` | retain forwarding shim and previous entry point | #120 |
| 4 | official Skills artifact split/migration | #116/#117/#120 plus #121 dependencies | package/resource/version/CLI/MCP compatibility tests | `SMOKE_ONLY` | keep current five resources/IDs and installer during window | #121 |
| 5 | docs current/history move including slides/assets | #78 content audit | local Markdown + HTML asset links, docs navigation, static governance tests | `NOT_APPLICABLE` | revert atomic moves | #78 |
| 6 | deletion gate for any proven obsolete compatibility | successful owning migrations | zero imports/package/CI/test/current-doc refs; provenance decision; user note | owner-specific | restore from named pre-delete commit | owning card; no new card yet |

No new child Test Card is necessary now: every executable finding has an
existing owner. A new removal card should be opened only if #120 declines the
MCP shim migration or a later zero-reference audit finds an unowned candidate.

## Routing to existing cards

| Card | Inputs from #115 |
|---|---|
| #116 | benchmark Python packages are accidentally/incompletely shipped; tests are partially in sdist; all runtime/Skills data is present; public artifacts need clean-install checks; license/package-data warnings need resolution |
| #117 | preserve root layout; configuration owns store discovery, not repository rearrangement; do not make docs/archive paths runtime inputs |
| #118 | `install.sh` and quickstart example are repository onboarding surfaces; validate them against a built wheel, not editable imports |
| #119 | CLI remains shipped adapter in `tessera/`; command/output inventory changes no package ownership or retrieval semantics |
| #120 | packaged MCP module remains; optional dependency/protocol boundary and top-level shim deprecation/move belong here |
| #121 | current five Markdown procedural anchors are active package data and public CLI behavior, not disposable placeholders; provide compatibility when official Skills replace/split them |
| #78 | classify and move dated docs/slides as provenance; update all links/assets atomically; do not rewrite runtime in a docs move |

## Relevant delivery history

| Delivery | Classification | Canonical commit | Architecture relevance |
|---|---|---|---|
| initial repository delivery | `RUNTIME_IMPLEMENTATION` + `PACKAGING` | `9cc8c38` | created root package, package metadata, examples, installer, shim, skills data and source archive |
| PRs #1/#2/#3/#6 | `RUNTIME_IMPLEMENTATION` | `83d716c`, `5590b1d`, `4cbc585`, `b3a1501` | established public contract, deterministic retrieval, canonical metadata and Evidence Ledger |
| PR #4 | `BENCHMARK_INFRASTRUCTURE` | `6d9b194` | established CI and sanity path |
| PR #53 | `DOCUMENTATION_CORRECTION` | `25e7df8` | aligned current architecture docs with implementation |
| PR #56 | `DOCUMENTATION_CORRECTION` | `eb4d5d8` | created docs navigation/precedence map |
| PR #79 | `DOCUMENTATION_CORRECTION` | `aa02fad` | made public surface project-agnostic |
| PR #81 | `DOCUMENTATION_CORRECTION` | `75eae59` | versioned canonical current brand assets |
| PR #83 | `PACKAGING` + `RUNTIME_IMPLEMENTATION` | `a6dc12c` | corrected package metadata and MCP naming |
| PR #84/#85/#97 | `GOVERNANCE` | `9012786`, `864a38e`, `3fdaa0d` | established change and Test Card/PR policy |
| PR #98 | `RUNTIME_IMPLEMENTATION` | `fb23012` | aligned Engine, CLI and MCP retrieval contracts |
| PR #99 | `BENCHMARK_INFRASTRUCTURE` + `PACKAGING` | `812c3aa` | added LongMemEval and first benchmark package declaration |
| PR #102 | `BENCHMARK_INFRASTRUCTURE` + `PACKAGING` | `39febe3` | added ledger/reporting and additional package declaration |
| PR #107 | `ARCHITECTURE_DECISION` | `0c0b638` | accepted core/optional/benchmark boundary |
| PR #110 | `GOVERNANCE` | `7f92dd9` | added versioned plain-language records |
| PR #113 | `RUNTIME_IMPLEMENTATION` | `a80a5f1` | corrected CLI identity; did not restructure package |
| PR #123 | `GOVERNANCE` | `a79b5ae` | required auditable evolution reconstruction |
| PR #124 | `DOCUMENTATION_CORRECTION` | `a0a482c` | lifecycle sync only, no new capability |
| PR #126 | `RUNTIME_IMPLEMENTATION` | `6d4a32b` | made default runtime generic and compatibility explicit |
| PR #127 | `DOCUMENTATION_CORRECTION` | `5d43a2d` | lifecycle sync only; made #115 READY |
| issue #115 candidate | `ARCHITECTURE_DECISION` | pending | inventories and accepts target; no migration/runtime implementation |

PR #5 and #6 share canonical merge `b3a1501` and are one Evidence Ledger
delivery, not two capabilities. Candidate commits and a later canonical merge
likewise remain one architecture decision. PRs #124/#127 synchronize lifecycle
records and do not duplicate the governance/runtime deliveries they document.
A closed-unmerged attempt is a `SUPERSEDED_OPERATIONAL_PR`, not a capability.

## Candidate validation

| Check | Result |
|---|---|
| `python -m pytest -q tests/test_architecture_boundary_docs.py` | 10 passed |
| `python -m pytest -q tests/test_plain_language_test_card_docs.py` | 7 passed |
| `python -m pytest -q tests/test_benchmark_reporting.py` | 51 passed |
| `python -m pytest -q` | 261 passed, 14 expected path-shape warnings |
| `python -m compileall -q tessera benchmarks tests` | passed |
| `git diff --check` | passed |
| `git diff --exit-code origin/main -- tessera/` | empty |
| `git diff --exit-code origin/main -- benchmarks/` | empty |
| clean candidate `python -m build` | wheel 46 files; sdist 69 files; exact inventories match audited main |

The deterministic sanity fixture was run in both the clean audited-main
worktree and the candidate worktree:

| Metric | Audited main | Candidate |
|---|---:|---:|
| Hit@1 | 0.75 | 0.75 |
| Hit@3 | 1.00 | 1.00 |
| Hit@5 | 1.00 | 1.00 |
| MRR | 0.875 | 0.875 |
| Evidence hit rate | 1.00 | 1.00 |
| Missing-evidence check | passed | passed |

Latency is deliberately not compared for this architecture card. LongMemEval
V1 was not run because the declared applicability is `SMOKE_ONLY`.

## Safety and decision

The candidate changes documentation and static architecture assertions only.
`git diff origin/main -- tessera/` and `git diff origin/main -- benchmarks/`
must remain empty. Retrieval ranking, indexing, graph expansion, temporal
behavior, conflict resolution, Evidence Ledger, write gate, persistence, path
containment, storage precedence, optional backend selection, MCP protocol and
CLI behavior remain unchanged.

Decision: `KEEP` the accepted architecture. Migration status remains explicitly
unimplemented. Benchmark applicability is `SMOKE_ONLY`; LongMemEval V1 remains
skipped.
