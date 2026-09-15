# 70 — Long sources expose precise evidence without becoming pseudo-memories

| Field | Value |
|---|---|
| Issue | [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [#270](https://github.com/LuigiFerronatto/TESSERA/pull/270) |
| Head commit | Final candidate [`e14ef92e`](https://github.com/LuigiFerronatto/TESSERA/commit/e14ef92e2891d8429539ec4a47174c76ab241839) |
| Merge commit | Canonical merge [`8ca854f1`](https://github.com/LuigiFerronatto/TESSERA/commit/8ca854f14f8f57443784e6cf3524419a953c2ce6) |
| Decision | `KEEP` |
| Benchmark applicability | `REQUIRED` |
| Benchmark rationale | Segment matching changes evidence selection and derived index structure, so the frozen retrieval gate verified that parent rankings and provenance did not regress. |
| Last audited | 2026-09-15 |

## In one sentence

TESSERA now derives deterministic, addressable segments from long structured
sources while returning the complete parent document as the canonical memory.

## What problem existed?

A long document was indexed only as one unit. Retrieval could find the document,
but evidence selection had no stable structural address for the relevant
section. Treating every paragraph as an independent memory would have improved
addressability by destroying document context and inflating the candidate pool.

## How did TESSERA behave before?

```text
long source -> one canonical document -> paragraph-level evidence heuristic
```

Short memory cards and long reference documents had the same indexing shape.
There were no derived segment identities or parent/segment graph links.

## What changed or is being tested?

A deterministic local segmenter derives heading-based spans for structured
Markdown and bounded paragraph/line windows for long unstructured Markdown or
plain text. Each segment records its parent, document identity, source version,
heading, ordinal, and exact line span. Segment nodes remain derived index state,
outside the three semantic drawers and outside the parent ranking pool.

## How does it work now?

**VALIDATED ON `main`.** Short atomic cards remain whole. Long eligible sources
produce `source_segment` nodes connected with `has_segment` and `segment_of`
edges. A segment match can select a precise evidence span, but retrieval returns
the complete ranked parent document. Incremental edit, move, and delete handling
retracts stale segments and preserves stable identity when content and spans do
not change.

## Concrete example

```text
3,075-character structured document
-> 3 derived addressable segments
-> query matches the middle segment
-> parent document remains the returned memory
-> evidence points to the exact 1,047-character source span
```

The controlled evidence span is 0.3405 of the full body while the full source
remains available on the parent result.

## How was it validated?

- focused acceptance coverage exercises atomic cards, Markdown and plain-text
  segmentation, exact spans, parent-only retrieval, source-version evidence,
  deterministic rebuild/cache reuse, cache invalidation, move stability, edit
  retraction, deletion cleanup, graph serialization, and source-byte
  preservation;
- exact-head CI on `e14ef92e` passed the full test and distribution jobs on
  Python 3.9 and 3.12, smoke, and sanity evaluation;
- the required LongMemEval V1 dev-50 run passed against immediate parent
  `b4137120` with identical aggregate and per-query parent rankings, full
  provenance coverage, and deterministic repeated-run hashes;
- the Maintainer Audit recorded `KEEP` with no P0/P1 findings for `e14ef92e`;
- the Merge Governor authorized that exact head before canonical merge.

## What improved?

- long-document evidence is structurally addressable and source-version linked;
- segment count cannot increase a document's TF-IDF/PageRank candidate weight;
- source edits, moves, and deletions maintain derived segment integrity;
- source files remain authoritative and byte-for-byte unchanged.

## What remains unimplemented?

- conversational or role-aware episode segmentation;
- durable source revision history (#73);
- learned or corpus-specific segmentation thresholds;
- semantic embeddings and adapter-specific instruction interpretation;
- claims about reader answer quality or semantic entailment.

## What is unlocked next?

[#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) and
[#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) had their final hard
blocker satisfied and move to `READY`. Queue order selects #13, the read-only
Corpus Doctor, as the next implementation. #71 remains later at Queue 31.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) |
| Pull request | [#270](https://github.com/LuigiFerronatto/TESSERA/pull/270) |
| Merge commit | [`8ca854f14f8f57443784e6cf3524419a953c2ce6`](https://github.com/LuigiFerronatto/TESSERA/commit/8ca854f14f8f57443784e6cf3524419a953c2ce6) |
| Evidence/Learnings/Decision | Maintainer Audit `KEEP` on final candidate `e14ef92e`; PR #270 Evaluation Card |
| Benchmark record | `REQUIRED`; LongMemEval V1 dev-50 passed on `e14ef92e` against parent `b4137120` |
| PR Evolution Audit | Recorded in the [PR #270 body](https://github.com/LuigiFerronatto/TESSERA/pull/270) |

## Evolution

```text
whole-document indexing only
-> #70 derived addressable segments with parent/source linkage
-> current state: precise segment evidence with canonical parent retrieval
-> next validated dependency: #13 Corpus Doctor
```
