# PR Evolution Audit — Issue #70 structural segmentation

## Canonical lifecycle

- **Issue:** [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70)
- **Implementation PR:** [#270](https://github.com/LuigiFerronatto/TESSERA/pull/270)
- **Final candidate SHA:** `e14ef92e2891d8429539ec4a47174c76ab241839`
- **Canonical merge SHA:** `8ca854f14f8f57443784e6cf3524419a953c2ce6`
- **Lifecycle status:** `VALIDATED`
- **Decision:** `KEEP`, recorded by the
  [final exact-head Maintainer Audit](https://github.com/LuigiFerronatto/TESSERA/pull/270#issuecomment-5684680369)
- **Implementation benchmark applicability:** `REQUIRED`
- **Lifecycle correction applicability:** `NOT_APPLICABLE`; documentation only

The candidate and canonical merge represent one runtime delivery. This record
restores the missing audit requested by lifecycle issue
[#275](https://github.com/LuigiFerronatto/TESSERA/issues/275); it does not make a
new implementation decision or imply that this documentation PR is merged.

## Capability lineage and superseded attempts

| Delivery / candidate | Contribution or outcome | Current interpretation |
|---|---|---|
| #12 / PR #246 / `971801cd89b6ce7b890df9ceb43b6afff9fa0964` | Incremental source lifecycle | Existing dependency reused by derived segments |
| #69 / PR #264 / `c815a684e4c8cbd426a0d717e243a7dfb0f04395` | Body-only plain-text ingestion | Existing source-format boundary reused by segmentation |
| PR #270 candidate `cad8ce5b212baa426a91a75de756c9a50a3a9c92` | Required retrieval benchmark failed; audit `ITERATE` | Superseded candidate, not a validated delivery |
| PR #270 candidate `6f493ad239504999242128a3b02fba6775f4bc73` | Benchmark passed; audit `KEEP` on that head | Intermediate evidence, superseded by the final candidate |
| PR #270 final candidate `e14ef92e2891d8429539ec4a47174c76ab241839` | Final exact-head gates and audit passed | Merged as `8ca854f14f8f57443784e6cf3524419a953c2ce6` |

The earlier [ITERATE audit](https://github.com/LuigiFerronatto/TESSERA/pull/270#issuecomment-5674600893)
and [intermediate KEEP audit](https://github.com/LuigiFerronatto/TESSERA/pull/270#issuecomment-5674760378)
remain historical evidence. Neither substitutes for the final candidate's audit.

## Before and after

```text
Before: long source -> one canonical document -> paragraph evidence heuristic

After:  long eligible source -> canonical parent + derived addressable segments
        segment match -> precise source-version-linked evidence span
        retrieval result -> complete canonical parent document
```

The [canonical delivery diff](https://github.com/LuigiFerronatto/TESSERA/pull/270/files)
adds deterministic segmentation in `tessera/segmentation.py` and integrates
parent/segment identity, graph persistence, source lifecycle, and evidence
selection. Short atomic cards remain whole. `source_segment` nodes stay outside
the canonical parent TF-IDF/PageRank candidate pool and the three semantic
drawers. A segment match does not become an independent pseudo-memory.

## Validation evidence

For exact final candidate `e14ef92e2891d8429539ec4a47174c76ab241839`:

- [TESSERA CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34998832088)
  completed successfully with Python 3.9/3.12 tests/distribution, smoke, and
  sanity evaluation.
- [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34998832109)
  completed successfully. The required LongMemEval V1 dev-50 comparison
  against parent `b4137120286488ab274bf9e5989441c1ea710fea` retained identical
  aggregate/per-query parent rankings, as recorded in #70 and its final audit.
- The final Maintainer Audit recorded `KEEP` with no supported P0/P1 findings.
- [Merge Governor](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34998832080)
  completed successfully before canonical merge.

[`tests/test_issue_70_structural_segmentation.py`](../tests/test_issue_70_structural_segmentation.py)
and the [stage record](test-cards/70-structural-segmentation.md) cover exact spans,
parent-only retrieval, atomic-card preservation, cache/rebuild behavior,
edit/move/delete cleanup, serialization, and source-byte preservation. Historical
benchmark results are not claims about reader answer quality or entailment.

## Routing and remaining scope

At #70's merge, #13 and #71 had their hard dependencies satisfied. Being READY
for #71 means its own implementation may be selected; it does not mean its
adapter registry was delivered. The generated #275 fallback text incorrectly
kept #71 BLOCKED merely because implementation remained unfinished. The
canonical roadmap correctly separates readiness from delivery.

#13 subsequently merged in PR #277. Current selection and WIP belong to
[ROADMAP.md](ROADMAP.md); this audit selects no new work. Conversation/role-aware
episodes, source revision history (#73), semantic embeddings, and
adapter-specific instruction interpretation remain outside #70.

No new changelog entry is needed: PR #270 already recorded the public
segmentation/evidence change. This audit adds no runtime behavior.
