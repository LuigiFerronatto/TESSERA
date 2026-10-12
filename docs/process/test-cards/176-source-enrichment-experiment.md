# #176 — Source-preserving enrichment experiment

| Field | Value |
|---|---|
| Issue | [#176](https://github.com/LuigiFerronatto/TESSERA/issues/176) |
| Record status | `IN_PROGRESS` |
| Capability type | Optional offline experiment infrastructure |
| Pull request | [Draft PR #322](https://github.com/LuigiFerronatto/TESSERA/pull/322) |
| Merge commit | Not merged |
| Decision | `ITERATE`; semantic KEEP unmeasured |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

Prepare a bounded, source-preserving enrichment preview and inspect captured
model proposals without automatically turning them into durable memories.

## What problem existed?

Legacy notes mix facts, preferences, instructions and old/new state. Deterministic
indexing is safe and searchable but cannot infer all of their semantic boundaries.

## How did TESSERA behave before?

Canonical #154 discovery and #70 segmentation were available; there was no
independent offline #176 preview/capture-validation surface.

## What changed or is being tested?

An optional Python-module entrypoint plans exact source files and replays
bounded captures with source hashes, exact line evidence and explicit origins.

## How does it work now?

In this unmerged candidate, `python -m tessera.enrichment plan` exposes source
sizes, fingerprints, destination and budget requirements. `replay` validates
captured JSON against fresh source bytes. Every surviving proposal requires
human review; no source, memory, index or model is written or downloaded.

## Concrete example

A document says “Prefiro relatórios concisos.” A captured preference can cite the
exact line and source hash. A conflicting fact drawer is flagged when the author
explicitly specified preferences. Neither proposal changes the author's file.

## How was it validated?

Focused source-discovery/enrichment tests and the checksum-frozen synthetic
runner cover exclusions, symlinks/races, limits, CRLF evidence, invalid schemas,
stale plans, duplicates, failures, mode boundaries and source-byte preservation.
The clean full suite passed 635 tests with 5 expected gh-aw-extension skips.
Pinned deterministic dev-50 was repeatable and matched an isolated canonical
base reconstruction exactly (Recall@10 0.916667, MRR 0.778502, provenance 1.0).
Offline wheel/sdist build and installed-wheel module help also passed. These
measure unchanged deterministic retrieval, not assisted-enrichment quality.
Exact candidate CI belongs to [PR #322](https://github.com/LuigiFerronatto/TESSERA/pull/322).

## What improved?

Eight synthetic source documents produce two canonical structural segments.
A2/A3 replay keeps nine review candidates after one exact duplicate and one bad
span, with zero source edits/provider calls/admissions. This proves mechanics,
not retrieval or semantic quality.

## What remains unimplemented?

Real reviewed corpus, human labels, explicit source-content consent, funded model
route, semantic quality comparison, admission, canonical episode-lineage adapter,
global semantic dedup, scalable cache/resume and validated relation consumption
remain open. No `KEEP` decision or product-default change is justified.

## What is unlocked next?

A reviewer can inspect bounded profile/capture artifacts now. Authorized research
can later compare E0–E4 while #192 owns execution and #19 owns admission.

## Technical provenance

- [Experiment protocol](../ENRICHMENT_EXPERIMENT.md)
- `tessera/enrichment.py`, `tests/test_issue_176_enrichment.py`
- `benchmarks/enrichment_176/synthetic-v1.json` and `synthetic-result-v1.json`
- Canonical base: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- #154/PR #175 canonical `05ce0dd234a7756d4a5ba315b77e4a6ec33c9429`
- #70/PR #270 canonical `8ca854f14f8f57443784e6cf3524419a953c2ce6`
- #136/PR #313 and #137/PR #297 are optional unmerged work, not dependencies

## Evolution

The initial experiment now has executable offline mechanics and a frozen synthetic
protocol exercise. No merge, issue closure or canonical capability promotion is
recorded. After review/merge, reconcile the exact canonical commit and remaining
semantic experiment gates before changing this record's status.
