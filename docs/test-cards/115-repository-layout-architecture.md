# #115 — Label the repository before moving anything

| Field | Value |
|---|---|
| Issue | [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) |
| Record status | `IN_PROGRESS` |
| Capability type | `architecture decision` |
| Pull request | Not merged |
| Head commit | Pending final candidate |
| Merge commit | Not merged |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
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

This card adds an evidence-backed inventory, dependency/reference matrix,
wheel/sdist inventory, ADR 0002 and a staged migration plan. It records the
current `#115 = IN_PROGRESS` lifecycle state. It does not move, delete or alter
runtime and benchmark implementation files.

## How does it work now?

**TARGET — NOT YET ON MAIN.**

ADR 0002 accepts the minimal-restructure option:

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

Keeping `tessera/` at the repository root avoids a high-churn `src/` migration.
Clean wheel tests in #116 will guard against checkout-only imports.

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

The architecture input for #116 is accepted by this candidate, but #116 must
remain `BLOCKED` until #115 is merged and its canonical merge is recorded.
#117–#121 retain all of their existing dependency gates and were not started.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) |
| Pull request | Pending |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Pending superseding Issue #115 comment |
| Benchmark record | Deterministic sanity; LongMemEval skipped under `SMOKE_ONLY` |
| PR Evolution Audit | [`docs/PR_EVOLUTION_115.md`](../PR_EVOLUTION_115.md) |

## Evolution

```text
working root-layout project with mixed repository/distribution ownership
→ complete #115 inventory and accepted ADR 0002
→ staged packaging, adapter, Skills and history migrations
→ clean artifact contract verified by #116/#118
```
