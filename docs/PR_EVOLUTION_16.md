# PR Evolution Audit — Issue #16 P0 conflict-resolver containment

## Candidate lifecycle state

- **Issue:** [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16)
- **Slice:** P0 containment only
- **Decision:** `PENDING`
- **Lifecycle status:** `IN_PROGRESS`
- **Candidate branch:** `fix/16-conflict-resolver-containment`
- **Starting canonical main:** `700b5ada9be059ced1c9f0d3d369b9824f4baaa5`
- **Final candidate SHA:** pending exact-head audit
- **Canonical merge SHA:** not merged
- **Benchmark applicability:** `REQUIRED`

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

## Expected lifecycle routing

Only after canonical merge and lifecycle reconciliation may the P0 slice be
recorded as `VALIDATED`. The conceptual full #16 issue remains split and its
P1 supersession work stays later/blocked on #15/#73/#96. No downstream card is
promoted automatically; #118 remains Queue #4.
