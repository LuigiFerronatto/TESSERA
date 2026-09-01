# #154 — Safe, explainable project source discovery

| Field | Value |
|---|---|
| Issue | [#154](https://github.com/LuigiFerronatto/TESSERA/issues/154) |
| Record status | `IN_PROGRESS` |
| Capability type | `SOURCE_DISCOVERY` |
| Pull request | [#175](https://github.com/LuigiFerronatto/TESSERA/pull/175) |
| Head commit | Pending final candidate |
| Merge commit | Not merged |
| Decision | candidate `KEEP`, subject to final CI |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-01 |

## In one sentence

TESSERA can inspect one configured project and explain which Markdown sources
are recommended, supported, ignored, or forbidden without changing what is
configured or indexed.

## What problem existed?

Configuration v2 could use explicitly configured sources, but it could not
safely inspect a project and produce a structured proposal for what else might
be useful. A future picker therefore had no bounded, deterministic source of
candidate files, reasons, security exclusions, or meaningful directory groups.

## How did TESSERA behave before?

```text
ResolvedConfiguration.sources
-> Engine reads exactly configured Markdown

project inspection / candidate plan
-> not implemented
```

The conservative behavior was intentional: schema v1 and newly initialized v2
projects retained the store as their only source.

## What changed or is being tested?

The candidate adds a pure Python discovery layer:

```text
physical project root
-> mandatory safety exclusions
-> .tessera-ignore subset
-> Markdown format/size/readability checks
-> RECOMMENDED / SUPPORTED / IGNORED / FORBIDDEN
-> top-level location clusters
-> SourceDiscoveryPlan
```

`SourceDiscoveryPlan.to_dict()` exposes candidates, clusters, totals,
diagnostics, supported formats, the size limit, and deterministic scan metrics.
Machine-readable reason codes explain every classification.

## How does it work now?

**IMPLEMENTATION CANDIDATE — not yet validated on `main`.**

The scanner resolves the supplied project root once and calls `os.scandir`
only inside that tree. It does not follow symlinks. Metadata checks happen
before any candidate content read; only the optional UTF-8 `.tessera-ignore`
file is read. Markdown is the sole selectable format, matching current Engine
ingestion. Files above 2 MiB are ignored without parsing.

Mandatory exclusions precede ignore matching and cannot be negated: `.git`,
the resolved v2 index, legacy `.tessera_index`, special files, unsafe symlinks,
and high-confidence credential/private-key names. Common dependency/build/cache
trees are safe convenience ignores and may be re-included by a supported `!`
rule.

The ignore subset supports comments, blanks, ordered `*`, `?`, `**`, directory
suffix `/`, and `!` re-inclusion. It explicitly does not claim complete
`.gitignore` compatibility; parent traversal, empty negations, and bracket
classes produce deterministic diagnostics.

Important root files remain standalone. Nested entries are grouped by their
actual top-level directory. A cluster reports counts for every classification,
so a forbidden child cannot disappear behind an otherwise recommended group.

## Concrete example

```text
README.md                 RECOMMENDED  project_entrypoint
docs/                     RECOMMENDED  2 recommended, 0 forbidden
examples/demo.md          SUPPORTED    supported_project_source
archive/old.md            IGNORED      recommended_exclusion
private.key               FORBIDDEN    sensitive_file
.tessera/index/           FORBIDDEN    derived_index
```

This is only a proposal. No candidate is added to `sources` until a separate
#155 display/select/confirm/persist workflow exists.

## How was it validated?

`tests/test_issue_154_source_discovery.py` freezes basic discovery, standalone
root files, clustering/counts, configured-source recommendation, Markdown-only
truthfulness, mandatory/default exclusions, ignore patterns and safe
re-inclusion, mandatory re-inclusion rejection, invalid syntax, ignore-file
self exclusion, private keys/credentials, `.env` examples, symlink
inside/outside/loop behavior, duplicate prevention, oversized/unreadable/special
files, deterministic output/metrics, config doctor JSON, no mutation,
root-bounded filesystem calls, schema-v2 stability, and conservative schema-v1
behavior. Final counts, packaging, sanity, CI, and Benchmark Ledger evidence are
recorded in the PR and Issue evidence comment.

## What improved?

- Future onboarding receives a small versioned machine-readable plan.
- Security exclusions and user ignores have explicit, testable precedence.
- Root files stay legible while nested projects do not flood the summary.
- Diagnostics explain invalid ignore rules and unreadable paths.
- Existing configured corpora remain unchanged.

## What remains unimplemented?

No checkbox picker, prompt, confirmation, config edit, ignore-file edit, index
build, incremental indexing, new ingestion format, segmentation, broad renderer,
embedding, model, or semantic classification is included. Filename-based
sensitive policy is conservative and does not claim content secret detection.

## What is unlocked next?

#155 remains blocked until #154 is canonically merged and post-merge lifecycle
evidence is synchronized. #118 and #134 remain blocked through the onboarding
and release chains. No downstream implementation starts in this candidate.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #154](https://github.com/LuigiFerronatto/TESSERA/issues/154) |
| Pull request | [PR #175](https://github.com/LuigiFerronatto/TESSERA/pull/175) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Pending final Issue comment |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity required, LongMemEval skipped |
| PR Evolution Audit | [PR_EVOLUTION_154.md](../PR_EVOLUTION_154.md) |
| Architecture decision | [ADR 0004](../adr/0004-safe-project-source-discovery.md) |

## Evolution

```text
#117 project/global configuration
-> #153 explicit store / sources / index
-> #154 discover / classify / group / explain
-> #155 display / select / confirm / persist / index
```
