# PR Evolution Audit — Issue #95 legacy runtime boundary

Audited starting main: `270bc29a0b0bb93ab1885947303caa6887a8b809` (includes
runtime merge `9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05` and lifecycle
merge `270bc29a0b0bb93ab1885947303caa6887a8b809`). Candidate branch:
`test-card/95-remove-legacy-runtime-coupling`; [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126).
Audited candidate head: `1fcd71df95993cfbfd8b8fe1e833fa879e947930`.
Canonical delivery: [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126),
merged at `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`; Issue #95 is
`VALIDATED` with decision `KEEP`.

GitHub and local Git both show that the canonical SHA is a two-parent merge
commit whose parents are the audited starting main and audited candidate. Its
tree is identical to the candidate tree. The task's pre-supplied “squash” label
was therefore not retained as a merge-method claim. Candidate/squash deduplication
still applies to delivery accounting: the candidate head and
canonical merge commit represent one runtime delivery, never two capabilities.

## Previous capability state

PR #79 made the intended public surface agent-agnostic and PR #83 made package
metadata plus MCP naming TESSERA-native, but the initial runtime remained the
source of truth for several unexamined defaults. At the audited main, CLI
storage still preferred `LAO_MEM_DIR`; quickstart generated that alias;
diagnostics auto-selected `.claude/memory` and inspected a project-specific
credential; the optional resolver preferred a hard-coded Blip gateway then
walked parents for `lao_core/engine_router.py`; backend failures could return
the input prompt as if it were model output. Package/help/examples and ordinary
fixtures reinforced that identity.

### Reproduced current-main behavior

The audit ran `270bc29` in a detached temporary worktree with no network calls.
Given a temporary project containing both `.claude/memory/` and a parent
`lao_core/engine_router.py`, current main returned:

```text
quickstart storage_dir: <project>/.claude/memory
quickstart MCP env:     LAO_MEM_DIR=<project>/.claude/memory
TESSERA_AZURE_GATEWAY_API_KEY=test → selected backend: azure
_find_engine_router(<project>)      → <project>/lao_core/engine_router.py
```

The CLI source and parser also resolved omitted storage from `LAO_MEM_DIR`, and
its empty-corpus diagnostic instructed the user to export that alias. These
outputs are baseline evidence only; the compatibility tests use mocks and never
call the discovered router or gateway.

## Deliveries that established the state

Candidate, head and merge commits are counted once per canonical PR delivery.

| PR | Delivery type | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence | Supersedes |
|---|---|---|---|---|---|---|---|---|
| initial direct delivery | RUNTIME_IMPLEMENTATION | on main | `9cc8c38` | `tessera/`, CLI, diagnostics, hooks, tests | original memory runtime and assisted bridge | introduced project-coupled defaults | git history/current-main reproduction | — |
| [#79](https://github.com/LuigiFerronatto/TESSERA/pull/79) | DOCUMENTATION_CORRECTION | MERGED | `aa02fad` | public docs/examples/tests | agent-agnostic public-surface intent | required project-neutral docs/fixtures | PR and Issue #62/#77 history | earlier public prose |
| [#82](https://github.com/LuigiFerronatto/TESSERA/pull/82) | DOCUMENTATION_CORRECTION | MERGED | `ffe76b3` | README | canonical product entrypoint | separated implemented product from development context | merged PR | earlier README |
| [#83](https://github.com/LuigiFerronatto/TESSERA/pull/83) | RUNTIME_IMPLEMENTATION | MERGED | `a6dc12c` | package metadata, MCP config, naming guard | TESSERA-native package/MCP names and `TESSERA_STORAGE_DIR` | canonicalized MCP only; CLI/diagnostics remained divergent | Issue #77, PR files/tests | legacy MCP name |
| [#84](https://github.com/LuigiFerronatto/TESSERA/pull/84) | GOVERNANCE | MERGED | `9012786` | changelog/change policy | curated product history | required migration-impact records | changelog policy | ad-hoc history |
| [#98](https://github.com/LuigiFerronatto/TESSERA/pull/98) | RUNTIME_IMPLEMENTATION | MERGED | `fb23012` | Engine/CLI/MCP retrieval surfaces | lossless retrieval-contract parity | froze ordering and structured evidence | parity tests | narrower projections |
| [#102](https://github.com/LuigiFerronatto/TESSERA/pull/102) | BENCHMARK_INFRASTRUCTURE | MERGED | `39febe3` | benchmark ledger/CI | applicability-aware benchmark gate | defines `SMOKE_ONLY` routing | reporting tests/CI | implicit benchmark routing |
| [#107](https://github.com/LuigiFerronatto/TESSERA/pull/107) | ARCHITECTURE_DECISION | MERGED | `0c0b638` | ADR 0001, architecture/features/roadmap | core vs optional-LLM ownership | forbids mandatory LLM in deterministic retrieval | Issue #74 decision | ambiguous cognition ownership |
| [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) | RUNTIME_IMPLEMENTATION | MERGED | `9ab03f7` | write gate, Engine/CLI/MCP/docs/tests | truthful admission/persistence boundary and path containment | froze #92 write semantics | #92 Evidence/Learnings/Decision | unsafe write claims |
| [#110](https://github.com/LuigiFerronatto/TESSERA/pull/110) | GOVERNANCE | MERGED | `7f92dd9` | stage records/templates/tests | reusable plain-language lifecycle | open work stays in progress | docs contract tests | prose-only stages |
| [#113](https://github.com/LuigiFerronatto/TESSERA/pull/113) | DOCUMENTATION_CORRECTION | MERGED | `a80a5f1` | CLI banner/tests/docs | corrected active TESSERA wordmark | preserved research citations/history | Issue #112 evidence | legacy banner |
| [#123](https://github.com/LuigiFerronatto/TESSERA/pull/123) | GOVERNANCE | MERGED | `a79b5ae` | issue/PR templates, roadmap, tests | mandatory evolution audits | canonical delivery deduplication and lifecycle sync | Issue #114 evidence | incomplete audits |
| [#125](https://github.com/LuigiFerronatto/TESSERA/pull/125) | DOCUMENTATION_CORRECTION | MERGED | `270bc29` | #92 audit/roadmap/stage/tests | synchronized lifecycle state | #92 becomes `VALIDATED`; #95 remains separate | green CI and merge | stale #92 state |
| #57, #59 and earlier superseded documentation candidates | SUPERSEDED_OPERATIONAL_PR | CLOSED_UNMERGED | — | architecture/source-audit candidate branches | no canonical delivery | none; later merged PRs are authoritative | GitHub closed-PR audit | — |
| [#126](https://github.com/LuigiFerronatto/TESSERA/pull/126) | RUNTIME_IMPLEMENTATION | MERGED | `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599` | config, CLI, diagnostics, compatibility bridge, hooks, docs, generic fixtures/tests | generic defaults plus explicit deprecated compatibility | removes implicit project behavior without changing retrieval/write semantics | audited candidate `1fcd71df95993cfbfd8b8fe1e833fa879e947930`, canonical merge with identical tree, focused/full tests, [TESSERA CI 33410027311](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33410027311), [Benchmark Ledger 33410027344](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33410027344) | remaining initial-runtime coupling; candidate and canonical merge counted as one delivery |

## Exact current-main reference inventory

The required case-insensitive search produced **367 matches in 29 tracked
paths**. Every result is assigned exactly one classification below; line lists
are the captured `270bc29` line numbers. Rows marked removed are changed only in
current runtime/reference material. Historical and research records are not
rewritten to erase provenance.

| Path | Symbol/line | Classification | Runtime reachable | Decision | Replacement or justification |
|---|---|---|---|---|---|
| `archive/legacy/v2_memory_graph_retrieval.py` | 468,469,471,472,475,487,500 | HISTORICAL_RECORD | no | preserve | archived v2 provenance |
| `archive/legacy/v3_memory_graph_retrieval_original.py` | 474,475,477,478,481,493,506 | HISTORICAL_RECORD | no | preserve | archived v3 provenance |
| `docs/CHEATSHEET.md` | 4,36–40,84,94,104–126,143–194,210,212,241,268,276,289,301,322,372,381,414,447,457,463,561,611–612 | CURRENT_DOCUMENTATION | human-facing | replace | generic `./memories`, project/agent examples, canonical config and explicit adapters |
| `docs/CODE_EXPLANATION.md` | 15,30,39,72–74,78,97 | CURRENT_DOCUMENTATION | no | preserve for #78 | broader narrative cleanup is owned by #78, not runtime #95 |
| `docs/COMO-FUNCIONA-E-PROXIMOS-PASSOS.md` | 3,4,11,14,62,72,115,150,176–291 (28 captured lines) | HISTORICAL_RECORD | no | preserve | dated internal evolution narrative and source evidence |
| `docs/PROCEDURAL_ANCHORS.md` | 3,4,5,8,11,16,19 | CURRENT_DOCUMENTATION | no | preserve for #78/#121 | legacy narrative; official Skills remain #121 |
| `docs/QUMEM-GAP-ANALYSIS.md` | 16–18 | HISTORICAL_RECORD | no | preserve | benchmark/research observation |
| `docs/ROTEIRO-DEMO-VIDEO.md` | 47–311 (24 captured lines) | HISTORICAL_RECORD | no | preserve | dated demo evidence, not current runtime guidance |
| `docs/adr/0001-core-vs-optional-llm-boundary.md` | 73,118 | CURRENT_DOCUMENTATION | no | update | records explicit adapter/current boundary; larger envelope stays #120 |
| `docs/slides/README.md` | 1,4,5,28,50,52 | HISTORICAL_RECORD | no | preserve | presentation provenance |
| `docs/slides/assets/LOGO_PRIMARIA_fundo_claro.svg` | 3,10,12 | HISTORICAL_RECORD | no | preserve | archived presentation asset |
| `docs/slides/assets/LOGO_SECUNDARIA_fundo_escuro.svg` | 3,10,12 | HISTORICAL_RECORD | no | preserve | archived presentation asset |
| `docs/slides/assets/mascots/LAO-3D-happy-birthday-transparent.png` | binary match | HISTORICAL_RECORD | no | preserve | archived presentation asset |
| `docs/slides/assets/mascots/LAO-3D-transparent.png` | binary match | HISTORICAL_RECORD | no | preserve | archived presentation asset |
| `docs/slides/tessera-apresentacao.html` | 5–820 (67 captured lines) | HISTORICAL_RECORD | no | preserve | dated presentation and brand evidence |
| `docs/test-cards/112-tessera-ascii-banner.md` | 62 | HISTORICAL_RECORD | no | preserve | prior stage evidence explicitly scopes #95 |
| `tessera/__init__.py` | module description line 5 | DEFAULT_RUNTIME | import | remove | agent-neutral package description |
| `tessera/cli.py` | 24,27,28,151,289,462,478,544 | DEFAULT_RUNTIME | yes | remove | shared canonical resolver, neutral diagnostics/help/examples |
| `tessera/decomposer.py` | example line 108 | EXAMPLE | docs/help | replace | `project/some-run` |
| `tessera/diagnostics.py` | 9,176,217,218,248 | DEFAULT_RUNTIME | doctor/quickstart | remove | no credential/path discovery; canonical MCP config |
| `tessera/engine_core.py` | 55,72,286,598,931,932,986,1276,1306 | DEFAULT_RUNTIME | indexing/write warnings | remove | generic schema language/examples; exact duplicate constant removed once |
| `tessera/hooks.py` | 14,217 | DEFAULT_RUNTIME | import/hook | remove | consuming-agent/project examples; assisted object becomes lazy |
| `tessera/llm_bridge.py` | 11–299 (37 captured lines) | OPTIONAL_RUNTIME | assisted resolution | replace | default selects nothing; shims delegate to explicit compatibility module |
| `tessera/orchestrator.py` | example line 25 | EXAMPLE | public description | replace | application-owned callable example |
| `tests/stress_test.py` | 55,86,124,126,130,134 | TEST_FIXTURE | tests only | replace | generic scale fixture |
| `tests/test_canonical_compatibility.py` | 55,56,62,63,88,99,109,112,118,119 | TEST_FIXTURE | tests only | retain | intentionally isolated foreign-schema compatibility fixture |
| `tests/test_contract_regression.py` | 15–59 (17 captured lines) | TEST_FIXTURE | tests only | replace | generic Engine contract fixture |
| `tests/test_evidence_ledger.py` | 24–203 (34 captured lines) | TEST_FIXTURE | tests only | replace | generic evidence fixture |
| `tests/test_retrieval_ranking_evidence.py` | 21–149 (27 captured lines) | TEST_FIXTURE | tests only | replace | generic ranking/evidence fixture; assertions unchanged in meaning |

No captured match was a `FALSE_POSITIVE`. `EXPLICIT_COMPATIBILITY` did not
exist as a safe boundary on audited main; it is introduced by this candidate.
The old optional runtime references were runtime-reachable and therefore
classified `OPTIONAL_RUNTIME`, not retroactively relabeled compatibility.

## Merged inventory and retained allowlist

- Project-specific text removed from default runtime: package description,
  CLI storage/help/warnings/examples, diagnostics/doctor/quickstart, Engine and
  hook comments, ordinary fixtures, implicit optional-backend resolver.
- Intentionally retained compatibility: `tessera/config.py` (`LAO_MEM_DIR`
  alias), `tessera/legacy_compat.py`, deprecated shims/selections in
  `tessera/llm_bridge.py`, focused compatibility tests, and migration prose.
- Intentionally preserved history: `archive/`, dated research/demo/slides,
  prior stage/evolution records and curated changelog history.
- Residual current narrative cleanup: Issue #78 owns `CODE_EXPLANATION.md` and
  other broad documentation prose; #115 owns repository/package layout; #117
  owns registry/interactive discovery; #120 owns MCP/adapter envelopes.

## Change introduced by PR #126

```text
before: explicit CLI path → LAO_MEM_DIR → ./memories
after:  explicit command/API path → TESSERA_STORAGE_DIR
        → deprecated LAO_MEM_DIR (one actionable warning) → ./memories
```

Quickstart no longer discovers `.claude/memory` and emits
`TESSERA_STORAGE_DIR`. Explicit `.claude/memory` remains a valid user choice.
Generic doctor/help/import/index/direct retrieval do not inspect provider
credentials, endpoints or project-specific files. `resolve_llm_fn()` chooses no
backend by default. Explicit legacy adapters require their name and endpoint or
exact router path, warn, and fail deterministically without prompt echo.

## Candidate capability state

The audited candidate made the default runtime project-neutral. Compatibility
is narrow,
deprecated, explicit, reversible and covered without network/subprocess calls.
Retrieval, ranking, graph expansion, temporal/conflict behavior, Evidence
Ledger and #92 write admission/path containment are unchanged.

## Current merged capability state

PR #126 is integrated on `main` at canonical merge
`6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`. Required implementation CI
remained successful for candidate `1fcd71df95993cfbfd8b8fe1e833fa879e947930`,
the merged tree is identical to that candidate, and Issue #95 is `VALIDATED`
with decision `KEEP`.

## What remains unimplemented

- #78: residual non-runtime narrative cleanup.
- #93: full cross-surface configuration parity/golden integration audit. #95
  establishes only the storage precedence and warning channel touched here.
- #115: repository/package layout redesign.
- #117: registry, project/global discovery and interactive `tessera init`.
- #120 / ADR 0001: optional-adapter output envelope and MCP lifecycle redesign.

## Benchmark before/after

Implementation benchmark applicability: `SMOKE_ONLY`. Baseline and candidate deterministic
sanity expectations are Hit@1 `0.75`, Hit@3 `1.00`, Hit@5 `1.00`, MRR `0.875`,
evidence hit rate `1.00`, missing-evidence check `passed`. `benchmarks/` has no
candidate diff; LongMemEval dev-50 was intentionally skipped. This lifecycle
synchronization changes no runtime contract, adds no second runtime capability,
does not increase runtime-delivery accounting, and declares benchmark
applicability `NOT_APPLICABLE` because it changes only documentation and static
documentation assertions.

## Newly unlocked work

#95's dependency edge is satisfied for #67 and #115. #67 remains `BLOCKED` on
#93 and regression-gate integration. #74, #95 and #112 are satisfied, so #115
becomes `READY`. #116–#121 keep their declared dependency chain; no unrelated
issue is promoted.

## Roadmap evolution

```text
partial product naming (#79/#83)
→ project-coupled CLI/diagnostics/provider defaults remained
→ PR #126 candidate `1fcd71df95993cfbfd8b8fe1e833fa879e947930`
→ canonical merge `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`
→ #95 VALIDATED
→ #115 READY
→ later #117/#120 work under their own cards
```
