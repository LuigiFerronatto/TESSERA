# PR Evolution Audit — Issue #155 initialization UX

## Canonical lifecycle state

- **Issue:** #155
- **Decision:** `KEEP`
- **Lifecycle status:** `VALIDATED`
- **Implementation PR:** [#210](https://github.com/LuigiFerronatto/TESSERA/pull/210)
- **Candidate branch:** `feature/155-init-ux`
- **Starting canonical main:** `51d7f6240dc094ef57ea0d42f38e69976a96d381`
- **Final candidate SHA:** `cf9f9c754becb87923c5a5c6bad4c3172cc9f344`
- **Canonical merge SHA:** `4c112195f1572bf352d1cc6a1042c69711381da8`
- **Benchmark applicability:** `SMOKE_ONLY`
- **Canonical merge date:** 2026-09-04

The candidate head received an independent Maintainer Audit `KEEP` decision with no supported P0/P1 findings and exact-head green CI. PR #210 then merged to canonical `main`; Issue #155 closed as completed. Candidate and canonical merge SHAs are intentionally recorded separately.

## Capability lineage

| Issue / delivery | Canonical contribution consumed by #155 |
|---|---|
| #117 / PR #150 | project-local and explicitly named global configuration resolution |
| #153 / PR #173 / `2508676` | separate generated-memory store, source roots and derived index |
| #154 / PR #175 / `05ce0dd` | `SourceDiscoveryPlan`, classification, clustering, safety and ignore policy |
| #155 / PR #210 / `4c112195` | source selection, complete initialization plan, confirmation, persistence and selected-source indexing |

#155 did not duplicate scanning, ignore parsing or indexing. It added the application/orchestration layer connecting the previously validated boundaries.

## Before

```text
project/global choice
→ storage-only InitPlan
→ immediate config mutation
→ immediate store-only index
```

The old interactive path did not present safe discovered project knowledge, did not separate source-selection policy from generated-memory destination, and did not expose a complete source-aware dry-run/JSON plan.

## After

```text
InitRequest
  → resolve project/global scope
  → #154 SourceDiscoveryPlan
  → recommended/custom/memory-only selection
  → InitializationPlan + preflight
  → human or JSON rendering
  → explicit confirmation when interactive
  → Configuration v2 + explicit ignore edit
  → canonical selected-source index
```

`InitializationPlan` is deterministic and serializable. It records configuration/store/index paths, selected project sources, discovery counts/details, current/proposed configuration, planned mutations, warnings and preflight problems.

## Safety and mutation boundary

Planning does not create config, store, ignore or index state. Interactive confirmation occurs after the full plan is visible. Cancel, EOF, Ctrl+C and dry-run stop before apply.

Existing configuration is compared against the proposal. Equivalent reruns preserve config bytes; non-interactive material changes require `--update-existing`. Schema-v1 migration remains conservative/store-only unless broader sources are selected explicitly.

`.tessera-ignore` persistence is explicit, uses #154 parsing semantics and re-runs canonical discovery after persistence. Deselection alone never edits the ignore file.

Indexing begins only after configuration and approved ignore mutations. Partial index failure is reported truthfully and remains recoverable/idempotent.

## Evidence

Exact final candidate evidence recorded on PR #210:

- focused #117/#153/#154/#155 suite: `89 passed`;
- Python 3.9: `502 passed, 5 skipped` in clean exact-head worktree;
- Python 3.12: `502 passed, 5 skipped` in clean exact-head worktree;
- distribution build and installed-wheel smoke passed;
- selected-source indexing preserved source hashes/bytes;
- `source_files_modified: 0`;
- deterministic sanity: Hit@1 `0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence hit rate `1.00`;
- LongMemEval correctly skipped under `SMOKE_ONLY` because retrieval/ranking/evidence semantics did not change;
- Maintainer Audit: `KEEP`, exact candidate head `cf9f9c7`, no supported P0/P1 findings.

## Scope boundaries preserved

Not included:

- #118 clean installed-artifact onboarding certification;
- #119/#166 broad renderer/taxonomy work;
- #120 MCP robustness;
- #134 publication;
- #157–#165 model/intelligence capabilities;
- #176 enrichment;
- #177/#196 hooks;
- #190 agent setup;
- #191 conversation import;
- incremental indexing;
- non-Markdown ingestion.

## Downstream routing after merge

Before merge:

```text
#155 IN_PROGRESS
#135 READY
#16  READY
#118 BLOCKED on #155
#120 READY
```

After canonical merge and validation:

```text
#155 VALIDATED / KEEP / closed
#135 READY                  Queue 2 — next implementation
#16  READY                  Queue 3 — P0 containment
#118 READY                  Queue 4 — blocker #155 satisfied
#120 READY                  Queue 5
#87  BLOCKED owner decision Queue 6
#134 BLOCKED on #118 + #87  Queue 7
```

#118 becoming `READY` does not mean it becomes the next implementation task. The canonical Queue ordering remains authoritative; #135 is next.

## Lifecycle reconciliation

This document records the implementation lifecycle only. Repository roadmap and Project #9 status projection are reconciled separately through the lifecycle/portfolio tooling. The lifecycle reconciliation is tracked by #211.
