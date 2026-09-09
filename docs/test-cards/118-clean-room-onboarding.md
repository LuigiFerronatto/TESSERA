# #118 — Onboarding from an installed distribution

| Field | Value |
|---|---|
| Issue | [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) |
| Record status | `VALIDATED` |
| Capability type | `runtime` / distribution validation |
| Pull request | [#225](https://github.com/LuigiFerronatto/TESSERA/pull/225) |
| Head commit | `b83c18494f9a2bc5687010ee27f077ac81688b6f` |
| Merge commit | `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d` |
| Decision | `KEEP`; final audit and canonical-merge checks passed |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-09 |

## In one sentence

A third party should be able to install a wheel, enter an unrelated project,
initialize it safely, use its knowledge offline, and remove the package without
losing source files or durable memories.

## What problem existed?

Tests inside a checkout can accidentally import source code, inherit a developer's
configuration, or rely on files absent from the distribution. #116 proved basic
packaging; #117/#153/#154/#155 established configuration and onboarding. #118
tests their complete composition from installed artifacts.

## How did TESSERA behave before?

The audited main is `112ae63c9ba1d8ffbe6ed3f2edf439d7dbe5b3a0`.
The clean baseline suite exposed a global repeat-init failure. Installed-wheel
experiments reproduced it and found a second diagnostic failure:

1. With a local project configured, the second `init --global shared ...`
   rediscovered the local configuration and failed after indexing the wrong
   corpus (`indexing escaped the selected source set`).
2. An unselected symlink to a selected README was incorrectly treated as a
   configured forbidden source. Initial init succeeded, but config doctor and
   repeat init then failed.

Both are `IN_SCOPE_FIX` findings. Neither requires changing ranking, evidence
selection, conflict behavior, the semantic drawers, or provider setup.

The required independent audit also exposed a pre-existing malformed hosted-site
gitlink: checkout credential cleanup failed because `.gitmodules` was absent.
The candidate records the existing module metadata with `update = none`, keeping
its commit/files intact and preventing product checkout from fetching the site.

## What changed or is being tested?

The global no-change apply path now uses the accepted named-global plan.
Forbidden-source diagnostics match the discovered entry's own path instead of
resolving a forbidden symlink to its selected target. Symlinks remain forbidden;
an explicitly configured alias still produces a blocking diagnostic.

The repository-only harness lives in `scripts/clean_room/`. It freezes source
content in `fixture.json`, creates a temporary virtual environment, installs the
wheel, copies only its test driver/fixture outside the checkout, and launches the
installed console script for every product operation. Python observation probes
verify installed metadata, config, discovery timing and actual index membership.

## How does it work now?

```text
clean source commit -> python -m build -> sdist -> wheel
  -> isolated Python 3.9 / 3.12 venv -> installed site-packages
  -> unrelated frozen project -> init -> doctor / index / query
  -> delete derived index -> rebuild -> equivalent evidence
  -> repeat init -> move project -> uninstall
```

Exactly three semantic drawers remain: `facts`, `preferences`, `insights`.
The base environment excludes provider SDKs and optional MCP/HTTP extras. A
CI-only Python audit hook blocks and records network attempts and implicit home
scans in actual CLI subprocesses; a deliberate network probe verifies the guard.
There is no product dependency on this instrumentation.

## Concrete example

```bash
tessera init --project . --store memories/generated \
  --sources recommended --non-interactive --dry-run --json
tessera init --project . --store memories/generated \
  --sources recommended --non-interactive --json
tessera doctor --plain
tessera index --plain
tessera query "what is this project?" --json
```

The fixture contains `README.md`, `AGENTS.md`, docs, research, existing memories,
optional examples, archive/dependency/environment exclusions, fake credential
filenames, `.git`, derived-index sentinels, an internal alias, an escaping link,
a FIFO, and `.tessera-ignore`. Its README describes the Aster Observatory.

Configuration v2 persists `store.path: memories/generated`, explicit ordered
source includes, and `index.path: .tessera/index`. All project-local paths remain
relative. Generated writes stay in the store; the selected sources remain
byte-identical. Relocation removes the old project path before commands run.

## How was it validated?

The `distribution` CI matrix checks out the exact PR head and runs the complete installed-wheel gate on Linux
with Python 3.9 and 3.12. Each job uploads `clean-room-python-<version>`:

- `environment.json`: source SHA, artifact hashes/sizes/inventories, interpreter,
  installer, environment/installation durations and offline guard proof;
- `installed.json`: commands, outputs, timings, fixture digest, per-stage source
  hashes, semantic comparisons, controlled TTY transcript and uninstall proof.
- `build.json`: build frontend/interpreter, source SHA and duration; the wheel is
  built from the freshly produced sdist.

The non-interactive commands use closed stdin. The separate standard-library
PTY cases exercise the actual installed executable, including confirmation,
negative confirmation, Cancel, source-selection Cancel, EOF and Ctrl+C. Before
each prompt response, the harness asserts the complete fixture is unchanged.
Equivalent TTY/non-TTY runs use the same physical project identity and compare
the persisted config, ordering, counts, store ID, index and actual corpus.

Dry runs compare complete filesystem snapshots, including registry state.
The ignore cases cover recursive exclusion, safe re-inclusion, mandatory
non-negation, explicitly persisted exclusion, and one-run deselection. Invalid
source paths cover `..`, absolute escape, symlink and special entries. A
named global store with distinct source content remains isolated.

Permission fixtures cover config, generated store and derived index. A real
filesystem obstruction at `graph.pkl` forces failure after config persistence;
the experiment observes partial state and removes only the obstruction before
retrying. No runtime function is replaced to create that failure.

The predecessor local matrix used Python 3.9.25 and 3.12.13; each passed 67 installed
CLI commands plus observation probes, including successful uninstall. The clean
full suite passed **538 tests, 5 skipped**. Canonical sanity stayed Hit@1 0.75,
Hit@3/5 1.00, MRR 0.875 and evidence hit 1.00. The predecessor CI matrix also
passed on Python 3.9.25/3.12.14. The strengthened final gate additionally compares
filesystem mtimes, exercises read-only source files and checks human partial-failure
output.

[Versioned measurements, inventories, hashes and TTY transcripts](../evidence/118-clean-room/validation.json)
identify their measured candidate explicitly. The final PR body and CI artifact
links bind the final exact head; neither predecessor evidence nor candidate KEEP
substitutes for its independent audit or canonical merge.

The final candidate passed 68 installed CLI commands and 69 source-integrity
checkpoints per interpreter. Its independent [Maintainer Audit returned KEEP](https://github.com/LuigiFerronatto/TESSERA/pull/225#issuecomment-5603811873)
with no supported P0/P1 findings, and the maintainer merged #225 on 2026-09-09.
Candidate and merge have identical Git trees: one runtime delivery.

Canonical-merge [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34367274210)
and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34367274180)
passed on `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d`. Both installed Python
3.9.25/3.12.14 reports bind that SHA and pass the full onboarding/uninstall
contract. [Canonical evidence](../evidence/118-clean-room/canonical-merge.json)
preserves report hashes, artifact metadata, import origins and sanity results.

## What improved?

Release reviewers gain a repeatable installed-artifact gate that exercises the
whole onboarding contract. The two reproduced failures receive focused
regressions as well as installed-wheel coverage.

## What remains unimplemented?

- No release/tag, GitHub Release, TestPyPI or PyPI publication.
- Linux is the executed platform; macOS uses equivalent POSIX/venv commands.
  Windows uses `Scripts/python.exe` and `Scripts/tessera.exe`; its filesystem
  permissions and interactive rendering require separate platform evidence.
- The controlled TTY harness uses POSIX `pty` and is enabled in Linux CI only.
- Discovery remains Markdown-only and uses the existing ignore subset. It is
  not content-based secret detection or full gitignore compatibility.
- Timing measurements are observations, with no release performance promises.
- No #119/#120/#121/#134, model/intelligence, enrichment, hook, integration setup,
  conversation import, incremental indexing or ranking work is included.

## What is unlocked next?

#118 is closed, `VALIDATED / KEEP`, with historical Queue 4 preserved. #120
remains `READY` / Queue 5 and is the next implementation after this lifecycle
correction merges into main. #134's #118 prerequisite is satisfied; its only
remaining blocker is #87's owner/legal decision. Neither downstream implementation
nor publication is included in this lifecycle correction.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) |
| Regression tests | `tests/test_issue_118_clean_room.py` |
| Installed driver | `scripts/clean_room/check_installed.py` |
| Environment driver | `scripts/clean_room/run_clean_room.py` |
| Evidence/Learnings/Decision | [PR Evolution Audit](../PR_EVOLUTION_118.md) and exact-head PR evidence |
| Benchmark | `benchmarks/sanity/ci_eval.py`, `SMOKE_ONLY` |
| Merge commit | `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d` |

## Evolution

```text
#116 packaging + #117/#153 configuration + #154 discovery + #155 init
-> #118 installed-artifact contract VALIDATED / KEEP
-> canonical merge 0ee5bbfe and green post-merge CI
-> #120 next; #134 still requires #87
```
