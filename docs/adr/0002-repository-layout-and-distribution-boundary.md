# ADR 0002: Repository Layout and Distribution Boundary

- **Status:** Accepted
- **Date:** 2026-08-31
- **Decision owner:** TESSERA architecture governance / issue #115
- **Audited main:** `5d43a2d4cdda0c17be6516f47920121070339d0f`
- **Benchmark applicability:** `SMOKE_ONLY`

## Context

TESSERA is already a Python project. It has a root `tessera/` package, console
scripts, tests, benchmarks, documentation and provenance material. The problem
is not the absence of a library: the repository and distribution boundaries
are insufficiently explicit.

The clean build from audited main proves the ambiguity. The wheel contains all
25 runtime/package-data files, but it also contains 16 Python files under
`benchmarks/`. The sdist contains those benchmark modules and 18 tests, while
omitting benchmark constraints, setup instructions, result schemas and the
sanity runner. A user therefore receives an incomplete benchmark package even
though benchmark code is repository evaluation tooling, not runtime cognition.

Old-looking paths are not automatically dead. `archive/legacy/` is not imported,
but documents the three implementations from which the package evolved.
`docs/slides/` is historical presentation provenance and its HTML references
its local assets. `tessera/skills_library/`, despite its name, is active package
data read through `importlib.resources`, installed by the CLI and exercised by
tests. The root `tessera_mcp_server.py` is an unadvertised compatibility shim;
its console-script replacement is current, but user reliance cannot be ruled
out without a deprecation step.

ADR 0001 remains authoritative for the deterministic core, optional adapter,
consumer and benchmark-cognition boundary. This ADR assigns repository and
distribution ownership without changing any runtime behavior.

## Decision drivers

- correct wheel and sdist contents;
- unambiguous imports from installed artifacts and editable checkouts;
- no benchmark, test, documentation or archive dependency in runtime;
- stable Python, CLI and MCP surfaces;
- preservation of historical evidence;
- low-risk, reviewable migrations with simple rollback;
- minimal Git-history disruption;
- clear ownership by issues #78 and #116–#121.

## Alternatives considered

| Option | Benefits | Costs and risks | Decision |
|---|---|---|---|
| Option A — keep every current path and declaration | no moves; smallest immediate diff | preserves accidental benchmark distribution, mixed current/history docs and ambiguous shims | Rejected as target; acceptable only as the audited starting state |
| Option B — move to `src/tessera/` | strongest mechanical protection against checkout-only imports; conventional distribution boundary | high history churn; every path-sensitive test/tool/doc changes; does not itself fix explicit benchmark packaging; adds migration risk without evidence of a current import bug | Rejected for now |
| Option C — preserve root `tessera/`, make ownership explicit and restructure only proven sub-boundaries | correct packaging can be achieved through explicit declarations and artifact tests; stable imports/history; small staged moves | requires disciplined clean-artifact tests because repository-root imports remain possible | Accepted |

The project may reconsider a `src/` layout if clean-wheel tests reveal a defect
that explicit packaging cannot prevent. It is not an architectural default.

## Accepted target ownership

| Surface | Target owner and rule |
|---|---|
| `tessera/` deterministic modules | `PACKAGE_RUNTIME`; installable base library |
| `tessera/__init__.py` exports | `PUBLIC_API`; versioned and tested from a wheel by #116 |
| `tessera/cli.py`, `display.py`, `diagnostics.py` | `CLI_SURFACE`; shipped with the package; UX changes remain #119 |
| `tessera/mcp_server.py` | `MCP_ADAPTER`; shipped only with an explicit MCP dependency extra; protocol/lifecycle design remains #120 |
| optional LLM/orchestration modules | `OPTIONAL_INTEGRATION`; package sub-boundary may be made clearer by #116/#120, but core must not import providers |
| `tessera/skills_library/*.md` and current installer | `PACKAGE_DATA` and active compatibility surface; keep until #121 defines official versioned Skills and migration |
| `benchmarks/` | `BENCHMARK_TOOLING`; repository-only, independently runnable against the public package, never imported by runtime and not in the base wheel/sdist Python package set |
| `tests/` | `TEST_ONLY`; repository and source-hosting evidence, excluded from release artifacts unless #116 documents a deliberate test-artifact policy |
| `examples/` | `EXAMPLE`; repository-only, tested against public interfaces |
| current contract/reference docs | `CURRENT_DOCUMENTATION`; repository-only and linked from the documentation map |
| Test Cards, PR evolution and research trace | `HISTORICAL_PROVENANCE` plus governance evidence; repository-only and preserved |
| dated narratives, demo and slides | `HISTORICAL_PROVENANCE`; move under an explicit history area only with link/asset rewrites and #78 review |
| `archive/legacy/` | `HISTORICAL_PROVENANCE`; preserve as non-importable source lineage |
| `install.sh` | `DEV_TOOLING` / onboarding compatibility; repository-only; clean-install ownership is #118 |
| `.github/` | `CI_GOVERNANCE`; repository-only |
| `pyproject.toml` | `BUILD_CONFIGURATION`; the only authoritative distribution declaration |
| root `tessera_mcp_server.py` | `ACTIVE_COMPATIBILITY` candidate; deprecate and eventually delete only through #120 after usage/migration evidence |

## Target dependency rules

1. Runtime may import only runtime or declared third-party dependencies. It must
   not import `benchmarks`, `tests`, `examples`, `docs` or `archive`.
2. Benchmarks, tests and examples may import the public package. Their reverse
   dependency is prohibited.
3. MCP and CLI are adapters over package contracts; neither owns retrieval
   semantics.
4. Optional integrations may depend on deterministic core contracts. Core must
   not depend on them.
5. Package data must be declared and accessed through package-resource APIs,
   never through a repository-relative path.
6. Historical files are not current instructions and must be labeled as such.
7. A deletion needs zero runtime, packaging, CI/test and current-doc references;
   a provenance assessment; a user migration note where applicable; and a named
   recovery commit. The recovery baseline for this audit is
   `5d43a2d4cdda0c17be6516f47920121070339d0f`.
8. A clean wheel/sdist inventory and clean-environment artifact smoke are release
   evidence, not optional diagnostics.

## Illustrative target tree

```text
TESSERA/
├── tessera/                         # shipped Python package
│   ├── core-facing modules          # deterministic memory/evidence runtime
│   ├── cli.py                       # shipped CLI adapter
│   ├── mcp_server.py                # shipped optional MCP adapter
│   ├── optional integrations        # explicit adapter boundary; exact move deferred
│   └── skills_library/              # current package data pending #121
├── tests/                           # repository-only contract and integration tests
├── benchmarks/                      # repository-only evaluation and ledgers
│   ├── sanity/
│   ├── longmemeval_v1/
│   ├── reporting/
│   └── results/
├── examples/                        # public-interface examples
├── docs/
│   ├── reference and current guides
│   ├── adr/
│   ├── test-cards/
│   ├── research/
│   └── history/                     # target for dated narratives/slides after #78 audit
├── archive/legacy/                  # preserved source-code provenance
├── .github/                         # CI and governance
├── pyproject.toml                   # distribution contract
├── README.md
└── CHANGELOG.md
```

The labels `core-facing modules`, `optional integrations` and `history/` express
ownership, not moves performed by issue #115. Exact Python module moves require
compatibility design in their owning follow-up cards.

## Staged execution

1. **Distribution boundary (#116):** remove benchmark packages and tests from
   release artifacts, retain required `tessera/` data, address metadata warnings,
   and test wheel-installed Python/CLI/MCP entry points. Roll back the packaging
   commit if artifact smoke fails.
2. **Installation/configuration (#117–#119):** make repository-only installer,
   examples and CLI consume the accepted artifact/config contracts. No layout
   move is required for this stage.
3. **MCP and optional adapters (#120):** decide subpackage placement and retire
   the root MCP shim only after deprecation and clean-wheel protocol tests.
4. **Official Skills (#121):** split or migrate the current bundled procedural
   anchors only after the Skills artifact/version contract exists. Preserve the
   old CLI surface through an explicit compatibility window.
5. **Documentation/history (#78):** identify current versus dated documents,
   move historical narratives/slides together with their assets, rewrite links,
   and retain provenance.
6. **Final deletion gate (owners above):** delete only items satisfying all ADR
   deletion criteria. No item is approved for immediate deletion by this ADR.

Every stage is independently revertible because no stage requires changing
retrieval, indexing, graph, temporal, conflict, evidence, write or persistence
semantics.

## Consequences

The accepted architecture keeps contributor ergonomics and Git history stable
while making the built artifact—not the checkout—the proof of distribution.
The main known cost is continued responsibility for clean-artifact tests because
root-layout imports can mask missing package declarations during local testing.

Issue #115 accepts the plan, not its migrations. #116 remains blocked until the
canonical merge and lifecycle synchronization for this decision exist.
