# PR Evolution Audit — Issue #13 Corpus Doctor

## Canonical lifecycle state

- **Issue:** #13
- **Decision:** `PENDING` (exact-head CI, Maintainer Audit and Merge Governor
  passed; no explicit maintainer `KEEP`/`ITERATE`/`REVERT` Decision is yet
  recorded)
- **Lifecycle status:** `IMPLEMENTED` (not `VALIDATED` — merge alone does not
  constitute validation)
- **Implementation PR:** [#277](https://github.com/LuigiFerronatto/TESSERA/pull/277)
- **Candidate branch:** `feat/13-corpus-doctor`
- **Final candidate SHA:** `dbcf5e737c4bd365f38915ae9e70a527713e6aa5`
- **Canonical merge SHA:** `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- **Benchmark applicability:** `SMOKE_ONLY` (`longmemeval-v1-dev-50` correctly
  skipped; no retrieval/ranking/evidence behavior changed)
- **Canonical merge date:** 2026-09-15

Exact-head CI passed `test`/`distribution` (Python 3.9/3.12), `smoke`,
`sanity-eval`, `benchmark-reporting (offline)`; `TESSERA Maintainer Audit` and
`tessera-merge-governor` both succeeded. PR #277 merged to canonical `main`;
Issue #13 closed as completed by that merge. The final candidate SHA and the
canonical merge SHA are recorded separately and must not be confused.

## Capability lineage

| Issue / delivery | Canonical contribution consumed by #13 |
|---|---|
| #12 / PR #246 / `971801cd` | incremental/idempotent indexing and identity-manifest reuse |
| #69 / PR #264 / `c815a684` | body-only plain-text (`.txt`) source ingestion |
| #70 / PR #270 / `8ca854f1` | deterministic structural segmentation and parent-only evidence |
| #13 / PR #277 / `20814a47` | read-only corpus/index diagnostic report, CLI, JSON/exit-code contract |

#13 did not duplicate discovery, ingestion or segmentation. It added a
separate, read-only diagnostic boundary over configured sources and the
already-validated derived index/manifest/evidence artifacts.

## Before

```text
tessera index
-> parse warnings only, no aggregate corpus/index health report
-> tessera doctor covers installation/runtime readiness only
```

## After

```text
tessera corpus doctor
-> deterministic human/JSON report: source parse, metadata completeness,
   identity collisions, broken/ambiguous relations, stale manifest/evidence
-> zero source mutation; stable exit codes (0 healthy/warning, 1 error,
   2 with --strict on warnings)
```

## Downstream routing

- #19 (evidence-aware memory admission) remains `DEFERRED` independent of
  this merge; its blocker set is unrelated to #13's implementation state, so
  it is not reconciled here.
- No other open issue lists #13 as its sole remaining blocker as of this
  merge.
- Corpus-quality CI activation for downstream repositories remains
  unstarted; it was explicitly out of scope for #13 and requires a separate
  Test Card once #13 records `KEEP`.

## Outstanding lifecycle step

A maintainer must record an explicit `KEEP` / `ITERATE` / `REVERT` /
`DROP` / `DEFER` Decision on Issue #13 based on the canonical merge evidence
above. Until that Decision is recorded, #13 remains `IMPLEMENTED` rather than
`VALIDATED`, and no dependent capability should be treated as unblocked by
#13 specifically.
