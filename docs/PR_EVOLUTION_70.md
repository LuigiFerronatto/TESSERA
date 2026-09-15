# PR Evolution Audit — Issue #70 structural segmentation

Audited starting main: `b4137120286488ab274bf9e5989441c1ea710fea` (PR #273,
governance template clarification). Candidate branch:
`feat/70-structural-segmentation`; [PR #270](https://github.com/LuigiFerronatto/TESSERA/pull/270).
Audited candidate head: `e14ef92e2891d8429539ec4a47174c76ab241839` (exact-head
evidence `6f493ad239504999242128a3b02fba6775f4bc73`). Canonical delivery:
[PR #270](https://github.com/LuigiFerronatto/TESSERA/pull/270), merged as
merge commit `8ca854f14f8f57443784e6cf3524419a953c2ce6`; Issue #70 is
`VALIDATED` with decision `KEEP`.

## Previous capability state

Before this PR, TESSERA indexed every Markdown/plain-text source (#69) as one
atomic memory. Long or structurally headed documents had no addressable
sub-span: retrieval could only return or fail to return the whole document,
and the Evidence Ledger could not point at a narrower exact span inside a
large source.

## What changed

- Adds `tessera.segmentation`, a deterministic local segmenter with no LLM or
  provider dependency, applied to long/structured Markdown and long plain-text
  sources; short native memory cards remain atomic.
- Stores each derived `source_segment` with parent memory ID, stable document
  ID, exact document hash, source path/format, heading, ordinal, and exact
  line span, linked via bidirectional `has_segment` / `segment_of` edges
  outside the three semantic drawers.
- Segment facets refine lexical candidate selection and Evidence Ledger span
  precision on the ranked parent document; they never enter the parent
  document candidate/PageRank pool and never surface as standalone
  pseudo-memory results.
- Removes stale segments on source edit/move/delete; segment/document
  identity is preserved across moves when content and line spans match.
- Versions the derived index schema so pre-segmentation caches rebuild; cache
  reuse now verifies exact source paths and SHA-256 values.
- Adds `segments=N` to `tessera index` lifecycle statistics.

## Evidence

```text
exact-head CI full suite: PASS (Python 3.9 and Python 3.12)
focused #70/retrieval/conflict/LongMemEval unit suite: 44 passed
exact-head LongMemEval dev-50: KEEP against immediate parent; repeatability=true
wheel + sdist build: PASS; twine check: PASS
clean-room installed-artifact harness: PASS
```

Benchmark applicability was `REQUIRED` because segment matching changes
evidence selection and index structure. The frozen LongMemEval V1 dev-50
candidate-versus-parent gate confirmed zero aggregate or per-query retrieval
regressions; Maintainer Audit recorded `KEEP` with zero P0/P1 findings.

## Downstream routing

- [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) (corpus/metadata
  doctor): its only remaining hard blocker, #70, is now satisfied. #13 moves
  from `BLOCKED` to `READY`.
- [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) (harness adapter
  registry): still depends on further work beyond this PR's segmentation
  surface (an adapter registry was not implemented here) and remains
  `BLOCKED`.

## Evolution

```text
Markdown/plain-text sources as single atomic memories (#12, #69)
-> #70 document + addressable derived segment (D3) modeling
-> current state: complete parent documents plus deterministic, addressable
   heading/paragraph-window segments with exact provenance on main
-> next validated dependency: #13 corpus/metadata doctor
```
