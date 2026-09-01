# #116 — Hand users the library, not the laboratory

| Field | Value |
|---|---|
| Issue | [#116](https://github.com/LuigiFerronatto/TESSERA/issues/116) |
| Record status | `IN_PROGRESS` |
| Capability type | `packaging` |
| Pull request | [PR #131](https://github.com/LuigiFerronatto/TESSERA/pull/131) |
| Head commit | Current PR head; canonical delivery is recorded after merge |
| Merge commit | Not merged |
| Decision | `KEEP` candidate |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA already worked from the repository, but the package we handed to
someone else was carrying pieces of our laboratory with it.

## What problem existed?

The package declaration named `tessera` and three benchmark packages as peers.
That made repository evaluation code look like installable product code. The
wheel shipped 16 benchmark Python files without their setup guide, constraints,
results, schemas or sanity runner. The sdist also copied a partial test suite.
Neither artifact represented a coherent benchmark product or an intentional
source release.

Editable installs were weak evidence because the repository root remained on
the import path. A missing packaged module or data file could be read from the
checkout and appear to work.

The first CI candidate also exposed the inverse boundary: invoking the
environment's `pytest` console script no longer placed the checkout root on
`sys.path`, so repository-only benchmark tests could not import repository-only
benchmark modules. CI now uses `python -m pytest`, the documented repository
test command, while the separate artifact job proves benchmarks are absent from
an installed wheel outside the checkout.

## How did TESSERA behave before?

At audited current `main` `055a35f4a7e8298013bcb816b30f67d9706b9516`,
an isolated `python -m build` produced:

- a 46-file wheel: 20 `tessera` modules, five Markdown resources, 16
  benchmark modules and five metadata files; and
- a 77-entry sdist: the runtime/data, all 16 benchmark modules, 18 of the 20
  repository test modules, README/build metadata and generated metadata.

The build succeeded but repeatedly warned that table-form license metadata and
the MIT classifier were deprecated. The older #115 audit observed a setuptools
ambiguity warning for `tessera.skills_library`; the current-main reproduction
did not emit that warning, but the directory still depended on an implicit
data-only convention.

The packaging branch later incorporated #93's runtime merge at `c6124548` and
its independent lifecycle correction at canonical merge `65f42d76`. That
parallel documentation delivery leaves the artifact contract unchanged while
preserving #93 `VALIDATED` and #67 `BLOCKED` on regression-gate integration.

## What changed or is being tested?

The explicit setuptools package list now contains only `tessera`. Package data
remains explicit and automatic manifest inclusion is disabled. `MANIFEST.in`
defines the sdist as rebuildable package source plus README/build metadata and
prunes repository-only benchmark, test, docs, archive, example and CI families.

The existing MIT intent is expressed as an SPDX string using the smallest
setuptools generation that supports it; the deprecated license classifier is
removed. No standalone `LICENSE` or copyright owner was invented. That legal
repository entrypoint remains the owner decision in #87.

Artifact CI builds and inspects both distributions on Python 3.9 and 3.12,
installs the wheel in a fresh environment, changes outside the checkout,
clears `PYTHONPATH`, exercises the public imports and CLI, loads all five
resources, and separately loads the optional MCP surface.

## How does it work now?

**CANDIDATE — NOT YET ON `main`.**

The candidate wheel has 30 files: the same 20 TESSERA modules, five required
Markdown resources and five metadata files. The candidate sdist has 40 entries:
its root, README, `pyproject.toml`, `MANIFEST.in`, generated build metadata,
the same runtime/data sources and egg metadata. Neither artifact includes
benchmark or test Python files.

`tessera/skills_library/*.md` remains active package data. Installed code reads
it with `importlib.resources`, exactly as the current CLI does. This card does
not redesign official Skills; #121 retains that ownership.

## Concrete example

Before, installing the wheel made this import possible even though it was not a
supported product surface:

```python
import benchmarks.longmemeval_v1
```

The package omitted the benchmark's setup script, pinned constraints and result
contract, so that import was a misleading fragment. After this change the
benchmark stays in the Git repository and runs against the public library, but
it is absent from wheel and sdist.

The supported import remains:

```python
import tessera
from tessera import TesseraEngine
```

The full intentional surface is the names in `tessera.__all__`; this card adds
no new public export.

## How was it validated?

Validation covers package-contract tests, the full repository suite, compile
checks, warning-free isolated builds, exact wheel/sdist inspection, clean
Python 3.9 and 3.12 wheel installs outside the checkout, installed metadata and
resource reads, `tessera --help`, a deterministic temporary-corpus write/query,
and optional MCP import/entry-point loading. The deterministic sanity contract
must remain Hit@1 0.75, Hit@3/5 1.00, MRR 0.875, evidence hit rate 1.00 and the
missing-evidence check passed. LongMemEval remains skipped under `SMOKE_ONLY`.

## What improved?

The distribution boundary now matches accepted ADR 0002. A wheel consumer gets
the runtime, CLI/MCP adapter modules and required resources, without an
incomplete benchmark namespace. Build warnings owned by packaging are removed,
and CI proves imports come from `site-packages` rather than the checkout.

## What remains unimplemented?

The source tree does not move. Benchmarks and tests remain in the repository and
continue to run there. The README long description still contains
repository-relative links; because no PyPI publication exists, broad README
rewriting is deferred to clean onboarding/publication work in #118. A standalone
license and copyright decision remain #87. Project/global configuration remains
#117, full onboarding #118, CLI UX #119, MCP protocol/lifecycle #120 and official
Skills #121. The root MCP compatibility shim is unchanged.

## What is unlocked next?

Nothing is promoted while this PR is open. After canonical merge and lifecycle
synchronization, #117 may become `READY`. Issues #118–#121 retain their full
dependency chains and no downstream implementation has started.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#116](https://github.com/LuigiFerronatto/TESSERA/issues/116) |
| Pull request | [PR #131](https://github.com/LuigiFerronatto/TESSERA/pull/131) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Published before merge on Issue #116 |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity, LongMemEval skipped |
| PR Evolution Audit | [`docs/PR_EVOLUTION_116.md`](../PR_EVOLUTION_116.md) |

## Evolution

```text
working checkout and accidental mixed artifacts
→ explicit TESSERA-only package and sdist ownership
→ clean installed-wheel proof on Python 3.9/3.12
→ #93 runtime/lifecycle current-main truth reconciled additively
→ current candidate remains IN_PROGRESS until merge
→ #117 becomes eligible only after lifecycle synchronization
```
