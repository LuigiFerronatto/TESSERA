# #115 — Label the repository before moving anything

| Field | Value |
|---|---|
| Issue | [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) |
| Record status | `VALIDATED` |
| Capability type | `architecture decision` |
| Pull request | [PR #128](https://github.com/LuigiFerronatto/TESSERA/pull/128) |
| Head commit | [`25afd31`](https://github.com/LuigiFerronatto/TESSERA/commit/25afd31b910dec97cffea34a25092c6e7f8b4f2e) (audited implementation candidate) |
| Merge commit | [`b475f1c`](https://github.com/LuigiFerronatto/TESSERA/commit/b475f1cd805f86cc8ad9526e563e3c6fb8409ff1) (canonical squash merge) |
| Decision | `KEEP` |
| Benchmark applicability | Implementation: `SMOKE_ONLY`; lifecycle synchronization: `NOT_APPLICABLE` |
| Last audited | 2026-08-31 |

## In one sentence

TESSERA keeps its existing root Python package, stops treating repository tools
as library contents, preserves history and performs any cleanup later in small,
owned migrations.

## What problem existed?

The repository works, but the words “package”, “tooling”, “documentation” and
“archive” did not consistently match what a built artifact contains. In
particular, `pyproject.toml` explicitly ships benchmark Python packages. The
wheel includes only part of the benchmark system, and the sdist also includes
most tests. Current reference documentation, dated project narratives, a
presentation deck and source-code history all live close together.

That ambiguity made ordinary cleanup unsafe. A directory called `archive` can
still be valuable evidence. A directory called `skills_library` can be active
runtime data. A top-level shim can be unused inside the repository but still be
used by people outside it.

## How did TESSERA behave before?

At audited main `5d43a2d4cdda0c17be6516f47920121070339d0f`:

- the Python package, CLI and MCP console entry points worked;
- the wheel shipped all 20 Python modules and five bundled Markdown skills;
- the wheel also shipped 16 benchmark Python modules;
- the sdist shipped those modules plus 18 test modules;
- docs, archives, examples, slide assets and the top-level MCP shim were not in
  either artifact;
- no runtime module imported benchmarks, tests, docs or archive code;
- the CLI actively loaded `tessera/skills_library/*.md` through
  `importlib.resources`;
- the root MCP shim imported the packaged MCP server but had no repository
  caller; and
- archived v1/v2/v3 engines were not imported but recorded implementation
  lineage used by current documentation.

## What changed or is being tested?

PR #128 added an evidence-backed inventory, dependency/reference matrix,
wheel/sdist inventory, accepted ADR 0002 and a staged migration plan. The
audited candidate `25afd31b910dec97cffea34a25092c6e7f8b4f2e` was squash-merged
as canonical architecture delivery
`b475f1cd805f86cc8ad9526e563e3c6fb8409ff1`. It did not move, delete or alter
runtime and benchmark implementation files.

## How does it work now?

**VALIDATED ON `main`.**

ADR 0002 now accepts the minimal-restructure option on `main`:

```text
tessera/       shipped library, CLI/MCP adapters and required package data
tests/         repository-only verification
benchmarks/    repository-only evaluation
examples/      repository-only public examples
docs/          current docs plus explicitly labeled governance/history
archive/       preserved implementation provenance
.github/       repository-only CI/governance
pyproject.toml distribution authority
```

The architecture decision is accepted; its migrations are not implemented.
Benchmarks and tests remain in the current distribution artifacts until #116
changes and verifies that packaging boundary. Keeping `tessera/` at the
repository root avoids a high-churn `src/` migration, while future clean-wheel
tests in #116 guard against checkout-only imports.

## Concrete example

`benchmarks/longmemeval_v1/run.py` imports `TesseraEngine`, so the benchmark
depends on the library. No `tessera/` module imports the benchmark. The correct
direction is therefore:

```text
repository benchmark → installed/public TESSERA package
```

not:

```text
TESSERA runtime → benchmark package
```

By contrast, `tessera/skills.py` reads the five Markdown files in
`tessera/skills_library/` and installs them through a CLI command. Those files
look like instructions, but today they are required package data and cannot be
deleted or moved without the compatibility work owned by #121.

## How was it validated?

- enumerated all 146 tracked paths and every top-level family;
- parsed 128 internal Python import edges and inspected dynamic MCP imports;
- searched CLI, package metadata, tests, benchmarks, CI, docs, subprocess/file
  references and HTML assets;
- validated 112 real local Markdown links (the only apparent miss was the
  literal placeholder `...` in change-policy sample text);
- validated all 25 local slide HTML asset references;
- built audited main in a detached clean worktree using `python -m build`;
- recorded the exact 46-file wheel and 69-file sdist inventories in
  `docs/PR_EVOLUTION_115.md`;
- ran focused architecture/plain-language/reporting tests, the complete suite,
  compileall, diff check and deterministic sanity evaluation; and
- verified empty implementation diffs for `tessera/` and `benchmarks/`.

PR #128 passed [TESSERA CI 33428299771](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33428299771)
on Python 3.9 and 3.12, CLI smoke and deterministic sanity. [Benchmark Ledger
33428299778](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33428299778)
passed reporting/applicability and correctly skipped LongMemEval V1 dev-50
under implementation applicability `SMOKE_ONLY`. The
[post-merge maintainer audit](https://github.com/LuigiFerronatto/TESSERA/issues/115#issuecomment-5483321070)
confirmed the canonical squash merge and `KEEP` decision.

## What improved?

Contributors can now tell active runtime from repository tooling and provenance
without inferring from filenames. Packaging errors are routed to #116, current
Skills migration to #121, MCP compatibility to #120, onboarding to #118 and
historical-document moves to #78.

## What remains unimplemented?

No files have moved. Benchmarks and tests still appear in current build
artifacts. The root MCP shim still exists. Current procedural anchors are not
the official Skills planned by #121. Dated documents and slides have not moved.
Package public-import, metadata and clean-install hardening remain #116/#118.

## What is unlocked next?

The accepted architecture and this lifecycle synchronization satisfy #116's
#74, #95 and #115 dependencies, so #116 becomes `READY`. #117 remains blocked
on #116; #118 and #119 remain blocked on #116/#117; #120 and #121 retain their
full declared dependency chains. None of those issues was started here.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) |
| Pull request | [PR #128](https://github.com/LuigiFerronatto/TESSERA/pull/128) |
| Merge commit | [`b475f1c`](https://github.com/LuigiFerronatto/TESSERA/commit/b475f1cd805f86cc8ad9526e563e3c6fb8409ff1) |
| Evidence/Learnings/Decision | [Issue comment](https://github.com/LuigiFerronatto/TESSERA/issues/115#issuecomment-5483088072) |
| Benchmark record | [CI 33428299771](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33428299771); [Ledger 33428299778](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33428299778); LongMemEval skipped under implementation `SMOKE_ONLY` |
| PR Evolution Audit | [`docs/PR_EVOLUTION_115.md`](../PR_EVOLUTION_115.md) |

## Evolution

```text
working root-layout project with mixed repository/distribution ownership
→ PR #128 inventory and accepted ADR 0002 at canonical merge b475f1c
→ post-merge lifecycle synchronization (`VALIDATED`)
→ staged packaging, adapter, Skills and history migrations
→ clean artifact contract verified by #116/#118
```
