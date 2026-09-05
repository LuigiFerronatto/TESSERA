# PR Evolution Audit — Issue #16 P0 conflict-resolver containment

## Candidate lifecycle state

- **Issue:** [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16)
- **Slice:** P0 containment only
- **Decision:** `KEEP`
- **Lifecycle status:** `VALIDATED` (P0 containment only; full #16 supersession remains `BLOCKED` on #15/#73/#96)
- **Implementation PR:** [#219](https://github.com/LuigiFerronatto/TESSERA/pull/219)
- **Candidate branch:** `fix/16-conflict-resolver-containment`
- **Starting canonical main:** `700b5ada9be059ced1c9f0d3d369b9824f4baaa5`
- **Final candidate SHA:** `2420bb5aa70e5d9663b92ae2785eda33f42f1cbe`
- **Canonical merge SHA:** `708c973e23d5c4eb8a52d359a2cadc153e161a90`
- **Benchmark applicability:** `REQUIRED` (met — LongMemEval V1 dev-50 passed at the candidate head with 0 gating/query regressions)

## Audited destructive baseline

The compatibility implementation built a conflict key from the lower-cased
first entity name and only the first lower-cased tag. For three chronological
preference candidates `P1, P2, P3`, all keyed as `user_reports`, it returned
only `P3`; `P1` and `P2` were lost. Two unrelated report preferences sharing
that key also collapsed to the newer one.

The baseline focused suite passed `26` existing tests, confirming this was the
established behavior. The new regression suite then failed `10` cases before
the fix, including direct and Engine retrieval paths.

## Candidate contract

Containment variant C1 keeps the existing compatibility method and list return
type but returns every input candidate in order. Candidate dict objects are not
cloned or rewritten, so IDs, scores, drawer/type, source/version metadata,
spans and relations remain intact. There is no legacy destructive mode.

```text
possible conflict
!= resolved conflict

newer
!= more true

ranked input candidates
→ shallow list copy
→ same candidate objects and ordering
```

Engine, CLI, MCP, Hook and assisted orchestration still delegate through the
same Engine retrieval path. No transport receives duplicated filtering logic.

## Regression evidence

The focused post-fix run passed `14` tests. It covers preference trajectory,
context-specific preference, unresolved contradiction, false coarse-key
collision, old-but-valid evidence, metadata-order instability, unchanged
candidate/provenance identity, zero source rewrite, score/order parity, default
Engine containment, no duplicates and offline/provider-independent execution.

Because the containment intentionally changes candidate-set membership, the
benchmark classification is `REQUIRED` even though ranking math is unchanged.
Exact-head Python 3.9/3.12, full suite, smoke, deterministic sanity,
LongMemEval dev-50, `compileall`, `git diff --check`, CI and Maintainer Audit
evidence are required before a `KEEP` decision.

## Scope boundary

- #15 retains temporal dimensions, validity and `state_key` ownership.
- The full #16 supersession/state-machine experiment remains blocked.
- #141 retains query-conditioned `Fq/Tq/Iq` state reconstruction.
- #20 retains evidence sufficiency/conflict/ambiguity status.
- #27 retains cross-source arbitration.
- Ranking, graph expansion, PageRank, embeddings and recency scoring are
  unchanged.

## Lifecycle routing (post-merge reconciliation)

PR #219 merged into `main` as `708c973e23d5c4eb8a52d359a2cadc153e161a90`. The
P0 containment slice of #16 is now recorded as `VALIDATED`. The conceptual
full #16 issue remains split: its P1 temporal supersession work stays
`LATER`/`BLOCKED` on #15/#73/#96, since none of those prerequisites changed as
part of this merge. No downstream card is promoted automatically; #118
remains Queue #4.
