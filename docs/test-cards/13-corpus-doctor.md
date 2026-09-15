# 13 — Know whether a configured corpus is safe to trust

| Field | Value |
|---|---|
| Issue | [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [#277](https://github.com/LuigiFerronatto/TESSERA/pull/277) |
| Head commit | `dbcf5e737c4bd365f38915ae9e70a527713e6aa5` (final candidate head) |
| Merge commit | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Benchmark rationale | The change adds a read-only diagnostic path and does not alter indexing, retrieval, ranking, evidence generation, or the frozen corpus. |
| Last audited | 2026-09-15 |

## In one sentence

TESSERA can inspect its configured source corpus and derived index, explain
specific defects, and prove that the audit did not modify source files.

## What problem existed?

Indexing reported parse warnings, but users had no focused command for checking
source metadata, identity collisions, relations, manifest freshness, and
evidence freshness together. The existing `tessera doctor` tests installation
and runtime readiness, so adding corpus checks there would mix two different
responsibilities.

## How did TESSERA behave before?

```text
tessera index
-> malformed files may be skipped with warnings
-> no reusable corpus-health report or CI severity contract
```

A user had to inspect index output and derived JSON files manually. There was
no deterministic aggregate count for complete, partial, or absent frontmatter.

## What changed or is being tested?

The candidate adds `tessera corpus doctor`. It enumerates only configured
source roots, parses sources without building an index, validates explicit
metadata, detects identity collisions and unresolved relations, compares source
versions with the identity manifest and evidence ledger, and hashes source
bytes before and after the audit.

## How does it work now?

**VALIDATED ON `main`.** The default human report summarizes sources,
metadata, relations, derived state, errors, warnings, and source mutations.
`--json` returns the same data under schema version 1. Errors return exit code
1. Warning-only reports remain successful by default; `--strict` returns exit
code 2 so CI can opt into warning-free enforcement.

The command never calls `build_index`, writes configuration, creates a missing
store, repairs metadata, or changes a source file.

## Concrete example

```text
$ tessera corpus doctor
tessera corpus doctor — warning
sources: selected=265 parsed=244
metadata: complete=180 partial=40 none=24 inferred_fields=392
relations: total=88 resolved=84 broken=4 ambiguous=0
source files modified: 0
findings: errors=0 warnings=24
```

The numbers above illustrate the report shape. Only fixture-backed results are
used as acceptance evidence; they are not claims about a particular user
repository.

## How was it validated?

The focused candidate tests cover a healthy indexed corpus, deterministic
repeated reports, byte-for-byte source preservation, malformed YAML, duplicate
explicit identities, invalid drawers and dates, broken relations, missing
derived state, stale manifest/evidence after an edit, body-only sources,
machine-readable output, strict warning exit behavior, and symlink escape
rejection. Related configuration, initialization, ingestion, segmentation, and
CLI contract tests also run against the candidate.

Exact-head CI and installed-distribution checks passed on Python 3.9 and 3.12.
Smoke, sanity evaluation, and offline benchmark reporting passed. The
Maintainer Audit recorded `KEEP` with no supported P0/P1 findings, and the
Merge Governor authorized the exact candidate head before merge.

## What improved?

- corpus defects have stable codes, severities, paths, messages, and repair
  hints;
- expected metadata inference is counted without treating every source as
  unhealthy;
- stale derived state is visible without rebuilding it;
- human and JSON consumers receive the same deterministic result;
- the source-mutation boundary is directly verified.

## What remains unimplemented?

- automatic source repair or metadata rewriting;
- subjective semantic quality scoring;
- a generalized policy language for custom severity thresholds;
- installation, dependency, MCP, or provider checks beyond the existing
  runtime doctor;
- corpus-quality CI activation for all repositories;
- MCP exposure of the new corpus report.

## What is unlocked next?

The canonical `KEEP` merge satisfies the Corpus Doctor prerequisite for #19 and
provides the diagnostic primitive needed by future corpus-quality CI. #19
remains intentionally `DEFERRED` at Queue 45, and activating corpus-quality CI
still requires its own Test Card.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) |
| Pull request | [#277](https://github.com/LuigiFerronatto/TESSERA/pull/277) |
| Merge commit | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Evidence/Learnings/Decision | `tests/test_issue_13_corpus_doctor.py`; exact-head CI (test/distribution Python 3.9/3.12, smoke, sanity-eval, benchmark-reporting) green; Maintainer Audit recorded `KEEP`; Merge Governor succeeded |
| Benchmark record | `SMOKE_ONLY`; `longmemeval-v1-dev-50` correctly skipped |
| PR Evolution Audit | `docs/PR_EVOLUTION_13.md` |

## Evolution

```text
index-time warnings and manual derived-state inspection
-> #13 deterministic read-only Corpus Doctor candidate
-> merged to main as 20814a47ec0f72d7bea0639e0b057df1ecf5cded
-> VALIDATED / KEEP; #19 prerequisite satisfied, corpus-quality CI remains separate
```
