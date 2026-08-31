# PR Evolution Audit — Issue #116 distribution hardening

Audited starting `main`: `055a35f4a7e8298013bcb816b30f67d9706b9516`,
fetched from `origin/main` before branch `test-card/116-packaging-hardening` was
created. This includes canonical #115 architecture delivery
`b475f1cd805f86cc8ad9526e563e3c6fb8409ff1` and lifecycle synchronization
`055a35f4a7e8298013bcb816b30f67d9706b9516`.

## Audit method

The audit inspected actual merge commits and file lists, the full
`pyproject.toml` history, runtime imports, optional imports, package resource
access, console entry points, benchmark setup/constraints, CI, a detached
current-main build, exact wheel/sdist members and clean installed-artifact
behavior. Titles alone were not treated as capability evidence.

## Deliveries that established the boundary

| Delivery | Merge and state | Type | Packaging-relevant evidence | Capability accounting |
|---|---|---|---|---|
| Initial TESSERA repository/package | `9cc8c38c2618ba6029d64a31b76742b968574a2b`, merged | `RUNTIME_IMPLEMENTATION` + `PACKAGING` | introduced root `tessera/`, `pyproject.toml`, five Markdown resources, both scripts, dependencies/extras, tests, docs and archive | one initial delivery |
| [PR #83](https://github.com/LuigiFerronatto/TESSERA/pull/83) | `a6dc12cd3f9e40cf79302027710b5391377f6f26`, merged | `PACKAGING` | corrected package identity, URLs and MCP naming without changing the package list | one packaging correction |
| [PR #98](https://github.com/LuigiFerronatto/TESSERA/pull/98) | `fb23012ba4b2fddc3912d7cb593391a04fe45ae7`, merged | `RUNTIME_IMPLEMENTATION` | aligned Engine/CLI/MCP result contracts; confirmed shipped adapters depend on public/runtime contracts | no new packaging declaration |
| [PR #99](https://github.com/LuigiFerronatto/TESSERA/pull/99) | `812c3aa37b59a3e99135a9d8b39245aeb71356d0`, merged | `BENCHMARK_INFRASTRUCTURE` + `PACKAGING` | added LongMemEval modules and explicitly added benchmark packages to setuptools | one benchmark delivery; accidental distribution begins here |
| [PR #102](https://github.com/LuigiFerronatto/TESSERA/pull/102) | `39febe36f016997f0c54ede9824f15dec04cc1ee`, merged | `BENCHMARK_INFRASTRUCTURE` + `PACKAGING` | added reporting modules, constraints/ledger CI and the third benchmark package declaration | one benchmark/ledger delivery; not a runtime capability |
| [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107) | `0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2`, merged | `ARCHITECTURE_DECISION` | ADR 0001 keeps deterministic core provider-independent and integrations explicit | one architecture delivery |
| [PR #113](https://github.com/LuigiFerronatto/TESSERA/pull/113) | `a80a5f19671a002e6ec2ed1846d041afb090b7a2`, merged | `DOCUMENTATION_CORRECTION` + `RUNTIME_IMPLEMENTATION` | corrected the CLI banner identity; did not alter package ownership | one branding correction |
| [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126) | `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`, merged | `RUNTIME_IMPLEMENTATION` | made generic runtime/default storage and optional compatibility boundaries explicit | one runtime delivery |
| [PR #128](https://github.com/LuigiFerronatto/TESSERA/pull/128) | `b475f1cd805f86cc8ad9526e563e3c6fb8409ff1`, merged | `ARCHITECTURE_DECISION` | accepted ADR 0002: keep root package, exclude benchmarks/tests from artifacts through #116 | audited candidate and squash merge count once |
| [PR #130](https://github.com/LuigiFerronatto/TESSERA/pull/130) | `055a35f4a7e8298013bcb816b30f67d9706b9516`, merged | `DOCUMENTATION_CORRECTION` | synchronized #115 to `VALIDATED` and #116 to `READY` | no architecture/runtime count |
| Issue #116 implementation PR | open | `PACKAGING` | removes accidental benchmark/test artifact ownership, modernizes equivalent MIT metadata, adds artifact tests/CI | one candidate packaging delivery; not counted as merged |

No `SUPERSEDED_OPERATIONAL_PR` materially established the current packaging
boundary. Candidate heads and later squash merges represent one delivery, not
independent capabilities.

## Baseline artifact evidence

The clean detached build of current main used standard PEP 517 isolation and
setuptools 84.0.0.

### Wheel before — 46 files

| Family | Count | Members |
|---|---:|---|
| `tessera/*.py` | 20 | all current Python modules |
| `tessera/skills_library/*.md` | 5 | all five active resources |
| `benchmarks/**/*.py` | 16 | root, LongMemEval V1 and reporting packages |
| `*.dist-info/*` | 5 | metadata, wheel, entry points, top-level and record |

### Sdist before — 77 entries

| Family | Count | Result |
|---|---:|---|
| archive root/directories | 8 | sdist root plus family directories |
| README/build/generated metadata | 8 | README, pyproject, setup.cfg, PKG-INFO and egg-info metadata |
| TESSERA modules/resources | 25 | complete current runtime/data |
| benchmark modules | 16 | incomplete benchmark surface |
| test modules | 18 | incomplete repository test surface |
| benchmark/test directories | 2 | repository-only ownership leaked |

The build emitted the table-form `project.license` deprecation and deprecated
MIT classifier warning at metadata, sdist and wheel phases. Unlike the earlier
#115 build environment, this current-main build did not reproduce the
`tessera.skills_library` importable-directory warning. Explicit package data is
still retained and tested so behavior does not depend on that warning.

## Target artifact evidence

The candidate uses:

```toml
[tool.setuptools]
packages = ["tessera"]
include-package-data = false

[tool.setuptools.package-data]
tessera = ["skills_library/*.md"]
```

`MANIFEST.in` explicitly admits README/build metadata and TESSERA source/data,
then prunes repository-only families. The candidate wheel contains 30 files
(20 modules, five resources, five metadata files); the sdist contains 40
entries and rebuilds the same wheel. Both have zero benchmark and test members.

## Dependency classification

| Dependency | Classification | Evidence |
|---|---|---|
| `networkx` | `BASE_RUNTIME_REQUIRED` | imported by `engine_core` for the runtime graph |
| `numpy` | `BASE_RUNTIME_REQUIRED` | imported by `engine_core` scoring/index operations |
| `PyYAML` | `BASE_RUNTIME_REQUIRED` | canonical parsing and Markdown frontmatter persistence |
| `scikit-learn` | `BASE_RUNTIME_REQUIRED` | runtime TF-IDF/cosine retrieval and episode boundaries |
| `rich` | `BASE_RUNTIME_REQUIRED` for the shipped CLI product | display/diagnostic surfaces use it, with plain fallback retained |
| `requests` | `OPTIONAL_RUNTIME` | imported only inside explicit legacy HTTP compatibility; `llm` extra |
| `mcp` | `OPTIONAL_RUNTIME` | imported only by `tessera.mcp_server`; `mcp` extra |
| `pytest` | `DEV_ONLY` | tests and benchmark verification, never runtime |
| `tomli` on Python <3.11 | `DEV_ONLY` | packaging-contract test parser compatibility |

Benchmark dependencies remain in repository-specific pinned constraints and
editable dev setup. No misleading benchmark extra is added because benchmark
implementation is not distributed.

## Public, version and entry-point contracts

The supported Python surface remains exactly `tessera.__all__`, including
`TesseraEngine`, models, write-gate/evidence contracts, orchestration/hooks,
current Skills helpers and `__version__`. Clean artifact tests at minimum prove
`import tessera` and `from tessera import TesseraEngine`; no new export is added.

`project.version`, `tessera.__version__`, wheel `METADATA` and installed
`importlib.metadata.version("tessera")` all remain `3.4.0`. A Test Card does not
itself require a version bump; release governance owns future SemVer changes.

Console metadata remains `tessera = tessera.cli:main` and
`tessera-mcp = tessera.mcp_server:main`. Base install has no `mcp`, `requests`,
provider SDK or credential requirement for deterministic Python/CLI use. MCP
extra validation imports the installed adapter and resolves its console entry
point without starting an uncontrolled server.

## Scope and routing

- #87 owns the standalone license and copyright decision. This card only
  expresses the existing MIT intent with equivalent SPDX syntax.
- #117 owns project/global configuration and `tessera init` design.
- #118 owns complete clean-machine onboarding and publication-facing README
  work, including repository-relative long-description links.
- #119 owns CLI product UX; current behavior is only exercised.
- #120 owns MCP protocol/lifecycle and the root compatibility shim.
- #121 owns official Skills; all five current resources remain byte-for-byte
  package data.

No runtime/retrieval semantics, benchmark implementation, migration, PyPI
release or tag is part of #116.
