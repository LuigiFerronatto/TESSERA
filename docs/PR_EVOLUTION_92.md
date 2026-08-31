# Issue #92 — Write-Gate PR Evolution Audit

Audit date: 2026-08-30  
Starting `main`: `0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2`  
Candidate PR: [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108)  
Candidate head audited before this documentation commit: `8169da3d5b6c0cfbc1bab9cd6372a86aa251c64d`

This audit reconstructs repository evidence rather than treating issue state,
PR titles, or documentation as proof of implementation. Merge SHAs below are
the GitHub merge commits. The initial write gate itself predates the PR history:
root commit `9cc8c38c2618ba6029d64a31b76742b968574a2b` introduced
`WriteGatingEngine`, `write_memory_note()`, CLI/MCP writes, Markdown source
files, and the original security frontmatter.

## Deduplicated PR evolution

| PR | Primary type | Merge status | Merge commit | Files/surfaces changed | Capability added | Contract changed | Evidence/decision | Supersedes |
|---|---|---|---|---|---|---|---|---|
| [#1](https://github.com/LuigiFerronatto/TESSERA/pull/1) | `RUNTIME_IMPLEMENTATION` | `MERGED` | [`83d716c`](https://github.com/LuigiFerronatto/TESSERA/commit/83d716c372b5cb7d7245f6f84fe959f4d6c4ee00) | `orchestrator.py`, retrieval contract tests, roadmap | Froze the structured retrieval result consumed downstream of stored memories. | Retrieval output became additive/stable; it did not define a write decision. | [#7 KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/7#issuecomment-5466934812) | — |
| [#3](https://github.com/LuigiFerronatto/TESSERA/pull/3) | `RUNTIME_IMPLEMENTATION` | `MERGED` | [`4cbc585`](https://github.com/LuigiFerronatto/TESSERA/commit/4cbc5850960412e2e0f22970dd37225401eed563) | `canonical.py`, `engine.py`, metadata/conflict/orchestrator tests | Canonical metadata, stable memory/document identity, source hashes, frontmatter compatibility. | Established the normalization/provenance substrate used after Markdown persistence; did not repair gate truthfulness. | [#9 KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/9#issuecomment-5466936601); four review blockers fixed before merge | — |
| [#4](https://github.com/LuigiFerronatto/TESSERA/pull/4) | `BENCHMARK_INFRASTRUCTURE` | `MERGED` | [`6d9b194`](https://github.com/LuigiFerronatto/TESSERA/commit/6d9b194fa98817dda547002067ab7ab533b1bf86) | `tessera-ci.yml`, `benchmarks/sanity`, CLI smoke | Python 3.9/3.12, real write→index→query smoke, deterministic sanity metrics. | Created the regression gate later reused by #67 and #92; no write-gate semantic assertion. | [#10 KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/10#issuecomment-5466937517) | — |
| [#5](https://github.com/LuigiFerronatto/TESSERA/pull/5) | `SUPERSEDED_OPERATIONAL_PR` | `MERGED` (duplicate GitHub record) | [`b3a1501`](https://github.com/LuigiFerronatto/TESSERA/commit/b3a1501eb193f379daaa57dcd18f896b36110982) | Same `engine`, `engine_core`, `evidence`, exports and tests as #6 | No independent capability: same head `b9fc349` and same merge commit as #6. | No independent contract or code delta. Its comments retain the operational/P0 audit trail. | [PR evidence](https://github.com/LuigiFerronatto/TESSERA/pull/5) | Superseded by canonical delivery #6 |
| [#6](https://github.com/LuigiFerronatto/TESSERA/pull/6) | `RUNTIME_IMPLEMENTATION` | `MERGED` | [`b3a1501`](https://github.com/LuigiFerronatto/TESSERA/commit/b3a1501eb193f379daaa57dcd18f896b36110982) | `engine.py`, `engine_core.py`, `evidence.py`, exports, ledger tests | Version-aware Evidence Ledger, document/content hashes, freshness, exact-or-null spans, derived `evidence.json`, retrieval provenance. | Source Markdown remained authoritative; ledger/index remained derived and rebuildable. Writes still carried the old security metadata. | [#11 KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/11#issuecomment-5466938428) | Canonical delivery for duplicate #5 |
| [#23](https://github.com/LuigiFerronatto/TESSERA/pull/23) | `SUPERSEDED_OPERATIONAL_PR` | `CLOSED_UNMERGED` | — | Superseded roadmap/templates attempt; GitHub records no surviving file delta | No unique capability or evidence beyond the rebasing explanation. | None landed. | [PR replacement record](https://github.com/LuigiFerronatto/TESSERA/pull/23) | Superseded by #24 |
| [#24](https://github.com/LuigiFerronatto/TESSERA/pull/24) | `GOVERNANCE` | `MERGED` | [`089590c`](https://github.com/LuigiFerronatto/TESSERA/commit/089590c63fa21a418e23a1916b43cf1865de5d14) | issue/PR templates, `ROADMAP.md` | Issue→Test Card→PR→Evidence→Decision delivery model. | Made evidence and explicit KEEP/ITERATE/REVERT/DROP decisions repository policy. | [#22 KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/22#issuecomment-5466939322) | #23 |
| [#46](https://github.com/LuigiFerronatto/TESSERA/pull/46) | `DOCUMENTATION_CORRECTION` | `MERGED` | [`8b8b57c`](https://github.com/LuigiFerronatto/TESSERA/commit/8b8b57c08804480988d83fd30d30f4395fbd862d) | `docs/FEATURES.md`, `CONCEPTS.md`, `QUERY_EXAMPLES.md` | First current-feature catalog and provenance/identity terminology. | Distinguished provenance from assessment/arbitration and current features from proposed work; no runtime write change. | [PR evidence/decision](https://github.com/LuigiFerronatto/TESSERA/pull/46) | — |
| [#52](https://github.com/LuigiFerronatto/TESSERA/pull/52) | `SUPERSEDED_OPERATIONAL_PR` | `CLOSED_UNMERGED` | — | `docs/ARCHITECTURE.md` only | No runtime capability; an earlier current-state documentation attempt. | None landed from this PR; the replacement corrected the write-gate description. | [PR replacement record](https://github.com/LuigiFerronatto/TESSERA/pull/52) | Superseded by #53 |
| [#53](https://github.com/LuigiFerronatto/TESSERA/pull/53) | `DOCUMENTATION_CORRECTION` | `MERGED` | [`25e7df8`](https://github.com/LuigiFerronatto/TESSERA/commit/25e7df88ad2fbe8a1b6470a612187cd1af2e2a83) | `docs/ARCHITECTURE.md` | Documented the existing heuristic `audit_and_sanitize()` path separately from future #19 admission. | Corrected current-vs-proposed claims, but inherited the runtime's false assumption that “sanitized” meant successful neutralization. | [PR decision](https://github.com/LuigiFerronatto/TESSERA/pull/53) | #52 |
| [#55](https://github.com/LuigiFerronatto/TESSERA/pull/55) | `DOCUMENTATION_CORRECTION` | `MERGED` | [`1a2f0f2`](https://github.com/LuigiFerronatto/TESSERA/commit/1a2f0f2483015565cd4cfaf93583f6f5568c6ce0) | `docs/OUTPUT_CONTRACT.md` | Field-level retrieval/evidence/provenance/nullability reference. | Established that source provenance and evidence are not confidence, truth or arbitration; did not define write admission. | [PR evidence/decision](https://github.com/LuigiFerronatto/TESSERA/pull/55) | — |
| [#56](https://github.com/LuigiFerronatto/TESSERA/pull/56) | `GOVERNANCE` | `MERGED` | [`eb4d5d8`](https://github.com/LuigiFerronatto/TESSERA/commit/eb4d5d800a6f7ea4d6e6c1d113ebea9d78250d34) | `docs/README.md` | Documentation navigation and precedence contract. | Current code/tests and current-reference docs outrank historical prose when they disagree. | [PR evidence/decision](https://github.com/LuigiFerronatto/TESSERA/pull/56) | — |
| [#57](https://github.com/LuigiFerronatto/TESSERA/pull/57) | `SUPERSEDED_OPERATIONAL_PR` | `CLOSED_UNMERGED` | — | `docs/FEATURES.md` only | No unique delivery; exact audited documentation blob promoted to #61. | None landed from this PR. | [replacement evidence](https://github.com/LuigiFerronatto/TESSERA/pull/57#issuecomment-5469775221) | Superseded by #61 |
| [#61](https://github.com/LuigiFerronatto/TESSERA/pull/61) | `DOCUMENTATION_CORRECTION` | `MERGED` | [`2559e62`](https://github.com/LuigiFerronatto/TESSERA/commit/2559e62283d19fafa68c801bbcc25dfffa022265) | `docs/FEATURES.md` | Distinguished the small deterministic gate from future evidence-aware memory admission. | Explicitly kept #19 unimplemented, but still described the old tuple/boolean sanitizer as current. | [#54 KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/54#issuecomment-5469774348) | #57 |
| [#79](https://github.com/LuigiFerronatto/TESSERA/pull/79) | `GOVERNANCE` | `MERGED` | [`aa02fad`](https://github.com/LuigiFerronatto/TESSERA/commit/aa02fad31935c3ec22d23b2099af269ae900d4ac) | public docs, workflow smoke, `benchmarks/sanity` fixture | Project-agnostic public/CI surface and sanity v2 fixture. | Kept ranking and thresholds fixed; established the current 75%/100%/100%/0.875 sanity baseline. | [CI + KEEP](https://github.com/LuigiFerronatto/TESSERA/pull/79#issuecomment-5470185709) | — |
| [#83](https://github.com/LuigiFerronatto/TESSERA/pull/83) | `RUNTIME_IMPLEMENTATION` | `MERGED` | [`a6dc12c`](https://github.com/LuigiFerronatto/TESSERA/commit/a6dc12cd3f9e40cf79302027710b5391377f6f26) | `pyproject.toml`, `mcp_server.py`, runtime naming tests | TESSERA-native package metadata and `TESSERA_STORAGE_DIR` MCP configuration. | Removed the legacy environment-key alias; write semantics remained the Engine's old path. | [PR decision/evidence](https://github.com/LuigiFerronatto/TESSERA/pull/83) | — |
| [#84](https://github.com/LuigiFerronatto/TESSERA/pull/84) | `GOVERNANCE` | `MERGED` | [`9012786`](https://github.com/LuigiFerronatto/TESSERA/commit/9012786e2112bf65a68892202fe34f3aef58d062) | `CHANGELOG.md`, change policy, docs index | Curated product-change record and mandatory-update/N/A policy. | Separated what changed from ADR rationale, Test Card decision, PR implementation and CI evidence. | [PR evidence/decision](https://github.com/LuigiFerronatto/TESSERA/pull/84) | — |
| [#85](https://github.com/LuigiFerronatto/TESSERA/pull/85) | `GOVERNANCE` | `MERGED` | [`864a38e`](https://github.com/LuigiFerronatto/TESSERA/commit/864a38e12277498b56eb9245b31a75dfc71b3b5e) | PR template, changelog | PR Contract v2: affected surfaces, Evaluation Card, regressions, changelog and decision. | Constrained how #92 must report behavior; enforcement remains #67 work. | [PR evidence/decision](https://github.com/LuigiFerronatto/TESSERA/pull/85) | — |
| [#97](https://github.com/LuigiFerronatto/TESSERA/pull/97) | `GOVERNANCE` | `MERGED` | [`3fdaa0d`](https://github.com/LuigiFerronatto/TESSERA/commit/3fdaa0da84c615a4409cf94f1db670c6a1cc8b8b) | Test Card template, operating model, roadmap/docs index | Definition of Ready, WIP, stop rules, P0 routing and M0–M5 order. | Made the issue routing block and measured decision authoritative over historical prose. | [PR evidence/decision](https://github.com/LuigiFerronatto/TESSERA/pull/97) | — |
| [#98](https://github.com/LuigiFerronatto/TESSERA/pull/98) | `RUNTIME_IMPLEMENTATION` | `MERGED` | [`fb23012`](https://github.com/LuigiFerronatto/TESSERA/commit/fb23012ba4b2fddc3912d7cb593391a04fe45ae7) | Engine facade, CLI/MCP retrieval projections, evidence helper, parity tests | Lossless Engine/CLI/MCP retrieval contract and direct MCP regression coverage. | Engine became the golden retrieval projection; did not create write-result parity. Review caught and fixed missing direct MCP parity testing. | [#68 Evidence/Learnings/KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/68#issuecomment-5471122707) | — |
| [#99](https://github.com/LuigiFerronatto/TESSERA/pull/99) | `BENCHMARK_INFRASTRUCTURE` | `MERGED` | [`812c3aa`](https://github.com/LuigiFerronatto/TESSERA/commit/812c3aa37b59a3e99135a9d8b39245aeb71356d0) | LongMemEval V1 adapter, schemas, runner, tests, setup | Reproducible retrieval-only dev-50 benchmark with isolated corpora. | Review fixed two P0s: evaluation-label leakage into indexed Markdown and incorrect measured-code provenance. No runtime write/retrieval change. | [#96 final remediation/KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/96#issuecomment-5471323841) | — |
| [#101](https://github.com/LuigiFerronatto/TESSERA/pull/101) | `RUNTIME_IMPLEMENTATION` | `MERGED` | [`467ba64`](https://github.com/LuigiFerronatto/TESSERA/commit/467ba649f53312cedcecf40caf548af5f766c67b) | `engine_core.py`, MCP types, persistence tests, README/architecture/features/cheatsheet/changelog | Markdown-only write contract and first-line rejection of unsupported formats. | Fixed the P0 acknowledged-but-unindexable JSON write; rejection precedes sanitizer, warnings, timestamps, files, registry, graph, ledger and MCP rebuild. It did not validate sanitizer truthfulness. | [#94 Evidence/Learnings/KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/94#issuecomment-5471509112) | — |
| [#102](https://github.com/LuigiFerronatto/TESSERA/pull/102) | `BENCHMARK_INFRASTRUCTURE` | `MERGED` | [`39febe3`](https://github.com/LuigiFerronatto/TESSERA/commit/39febe36f016997f0c54ede9824f15dec04cc1ee) | benchmark workflow/reporting/schema/records/constraints/docs/tests | Versioned benchmark ledger, applicability metadata, immediate-parent and canonical comparisons, forward environment fingerprint. | Review fixed three P0s: hard-coded future issue attribution, absent immediate-parent gate, and hidden environment drift. Establishes why #92 is `SMOKE_ONLY`. | [#100 final Evidence/Learnings/KEEP](https://github.com/LuigiFerronatto/TESSERA/issues/100#issuecomment-5471939801) | — |
| [#107](https://github.com/LuigiFerronatto/TESSERA/pull/107) | `ARCHITECTURE_DECISION` | `MERGED` | [`0c0b638`](https://github.com/LuigiFerronatto/TESSERA/commit/0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2) | ADR 0001, architecture/output/features/cheatsheet/roadmap/readme docs, static tests | Accepted deterministic-core vs optional-LLM boundary. | Core writes/retrieval may not require provider SDK/key/network; optional failures may not mutate source memory; O1–O4 runtime deviations remain unimplemented. | [#74 Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/74#issuecomment-5472247141) | — |
| [#108](https://github.com/LuigiFerronatto/TESSERA/pull/108) | `RUNTIME_IMPLEMENTATION` | `OPEN` | — | `security`, write path/result models, CLI/MCP, bundled metadata, contract docs/tests/roadmap | Canonical deterministic detection→transformation→admission→persistence result with exact hashes and mutation-free reject/review. | Makes sanitization truthful across Python/CLI/MCP/Markdown while preserving Markdown-only and provenance boundaries. | [#92 Evidence/Learnings/KEEP candidate](https://github.com/LuigiFerronatto/TESSERA/issues/92#issuecomment-5472677026) | — |

There are **20 distinct merged deliveries** in this scoped PR history, one open
candidate delivery (#108), and four superseded operational PR rows (#5, #23,
#52, #57). PRs #5 and #6 are one delivery because both point to head
`b9fc3496689b06b9325ffd65462f97ac4ba5559b` and merge commit `b3a1501...`.
The superseded rows add audit history but do not inflate the delivery count.

## Current-state reconstruction

```text
root implementation: heuristic WriteGatingEngine + direct Markdown writes
→ canonical metadata and derived Evidence Ledger/provenance (#3, #6)
→ architecture/features documentation of a small gate (#53, #61)
→ project-agnostic runtime and deterministic sanity gate (#79, #83)
→ lossless Engine/CLI/MCP retrieval result parity (#98)
→ Markdown-only pre-mutation persistence integrity (#94 / #101)
→ versioned benchmark applicability and regression records (#96/#100)
→ accepted deterministic-core boundary (#74 / #107)
→ current main still returns (content, score, is_sanitized=True)
→ #92 reproduces safe-text overclaim and detected English text left intact
→ #108 adds a canonical truthful write decision before durable mutation
```

### Status of fields and behavior

| Status | Fields/behavior |
|---|---|
| Canonical in the #108 candidate | `WriteGateDecision`, `WriteResult`, `threat_detected`, hash-derived `content_changed`, `admission`, ordered `reasons`, exact UTF-8 `original_hash`/`persisted_hash`, `persisted`, `filepath`, and `write_memory_note_result()` |
| Compatibility-only | `write_memory_note()` filepath return for accepted writes; `audit_and_sanitize()` tuple projection; `is_sanitized`; MCP `mem_id`/`connected_to`; historical `gating_status`/`toxicity_score` metadata |
| Deprecated by accepted architecture | Implicit optional-provider startup/selection and generated-context paths listed in ADR 0001; they are reachable but are not part of the deterministic write decision. |
| Documented but not implemented | Comprehensive semantic injection protection, a quarantine/review store, evidence-aware novelty/duplication/utility admission (#19), State Contamination evaluation, O1–O4 adapter migration, and #67 CI enforcement. |
| Implemented but previously documented too strongly | The small regex/tag gate was implemented, but “sanitization before persistence” obscured that detection and transformation had different coverage. |
| Invalid on starting `main` | Safe unchanged content had `sanitized=true`; detected English/mixed hostile content could remain byte-identical while frontmatter said `flagged_and_sanitized`; no explicit reject/review result existed. |

The starting-main public write surfaces all delegated to the same Engine write,
but did not share a write-result contract: Python returned only a filepath, CLI
rendered success, MCP returned filepath/ID/connections and always rebuilt the
index after a returned write. Evidence Ledger provenance was derived later by
indexing and did not prove whether gate metadata was truthful.

## Review findings that changed the evolution

- PR #3 fixed four canonical/frontmatter compatibility blockers before merge.
- PR #5's implementation audit fixed missing Engine/Ledger integration,
  retrieval provenance, exact-span ambiguity and cache/rebuild equivalence;
  #6 carried the exact validated delivery.
- PR #98 added a direct `mcp_server.query_memories()` parity test after review
  found that Engine/CLI tests did not prove the MCP boundary.
- PR #99 was `ITERATE` until ground-truth leakage was removed from indexed
  Markdown and measured-commit provenance was corrected.
- PR #101 fixed the P0 JSON write that was acknowledged but invisible after a
  clean index rebuild.
- PR #102 was `ITERATE` until Test Card attribution, immediate-parent gating and
  forward environment fingerprinting were corrected.
- ADR 0001 records current optional-LLM deviations as follow-up work; it did not
  silently implement them.
- PR #108 initially failed benchmark-reporting because its PR metadata omitted
  the required `Benchmark rationale`; metadata was corrected and the complete
  `SMOKE_ONLY` CI rerun passed.

## Benchmark and regression comparison

The previous sanity state is both the versioned project-agnostic baseline from
PR #79 and a fresh run from an isolated worktree at starting-main commit
`0c0b638...`. Latency is observational and is not a merge metric.

| Evaluation | Previous state | Candidate state | Delta | Applicability |
|---|---|---|---|---|
| Focused write-gate contract | One legacy hostile-redaction test passed but no truthful result schema, multilingual matrix, hash invariant or mutation snapshots existed; reproduced fixtures exposed the false sanitation state | 29 focused contract tests pass; eight deterministic fixtures; normalized repeated-run SHA-256 `524285669c29e388bd3fec7b638e973dbfd3dc4e9f078939eb6adc2827967f5d` | Explicit canonical schema plus 29 focused assertions; demonstrated overclaim removed | `REQUIRED` |
| Persistence contract | 15/15 #94 Markdown-only tests passed | 15/15 pass unchanged, plus atomic failure and reject/review mutation snapshots in #92 tests | 0 regressions; stronger admitted-write boundary | `REQUIRED` |
| Deterministic sanity evaluation | Hit@1 0.75; Hit@3 1.00; Hit@5 1.00; MRR 0.875; evidence hit 1.00; missing-evidence passed | Same metrics and missing-evidence result | 0.00 on every quality metric | `SMOKE_ONLY` |
| LongMemEval V1 dev-50 | [Canonical historical/forward records](../benchmarks/results/longmemeval-v1-dev-50/) remain versioned | `NOT_RERUN` | N/A | `NOT_APPLICABLE` |

No file under `benchmarks/` and no dedicated retrieval/ranking/evidence/conflict
module changes in #108. The `engine_core.py` diff is confined to write admission
and persistence. Therefore historical LongMemEval numbers are not presented as
a new candidate result.

## Roadmap and dependency consequence

```text
existing deterministic write gate
→ Markdown-only persistence integrity (#94 / PR #101)
→ deterministic-core boundary (#74 / PR #107)
→ truthful detection/transformation/admission contract (#92 / PR #108)
→ future State Contamination and evidence-aware admission (#19; still blocked)
```

#92 contributes one required contract to #67. An open PR does not complete that
dependency: #67 remains blocked until #92 is merged and #93/#95 plus their
regression checks are completed. #92 satisfies only its portion of #19; #19
also depends on #13, #16 and #73 and remains blocked. No downstream card becomes
READY solely because #108 exists.

## Remaining scope

- General semantic prompt-injection classification is not implemented or
  claimed; the deterministic patterns remain intentionally narrow.
- Review has no canonical quarantine store and means zero canonical mutation.
- #19 still owns evidence-aware memory admission and State Contamination
  evaluation.
- #67 still owns automated Quality Gate v2 enforcement.
- #93 storage-resolution parity, #95 remaining runtime coupling, and the ADR
  0001 optional-adapter migrations are untouched.
- Retrieval, ranking, graph expansion, temporal semantics, conflict resolution,
  Evidence Ledger scoring, readers/judges and LongMemEval behavior are unchanged.
