# 265 — Replaceable vector storage without changing canonical memory

| Field | Value |
|---|---|
| Issue | [#265](https://github.com/LuigiFerronatto/TESSERA/issues/265) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` and `benchmark` |
| Pull request | [Draft #293](https://github.com/LuigiFerronatto/TESSERA/pull/293) |
| Head commit | Exact candidate and CI are recorded on the draft PR |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

An optional vector-storage layer can keep atomic memories and source context
separate, recover interrupted writes and compare backends using identical
vectors, without modifying documents or making lexical retrieval depend on it.

## What problem existed?

TESSERA had source identity and derived-index ownership but no model-independent
vector storage/search boundary. Selecting an embedding model alone would not
establish how vectors are filtered, replaced, deleted, recovered or migrated.

## How did TESSERA behave before?

Canonical main `20814a47ec0f72d7bea0639e0b057df1ecf5cded` provides deterministic
lexical/graph retrieval and source lifecycle, but no `VectorBackend` contract,
persistent semantic records or same-frozen-vector backend-mechanics evaluator.

## What changed or is being tested?

The candidate adds immutable typed contracts, an exact-flat oracle, a stdlib
SQLite persistent exact-search candidate, a separate SciPy cKDTree exact/ANN
adapter, authoritative per-source replacement,
atomic/source/segment identities, filtered Top-K, compatibility manifests and
an offline frozen synthetic comparison. No embedding model, provider, Engine
semantic activation or default backend choice is introduced.

## How does it work now?

**TARGET — NOT YET ON MAIN.** An embedding producer supplies validated vectors
and a profile fingerprint. An explicit caller opens the selected backend under
its resolved derived-index directory, then atomically replaces a source's
current representations. A query supplies a matching profile and typed filters.
Hits preserve raw backend scores and canonical/source/evidence linkage. The
ordinary Engine/CLI never import these adapters.

## Concrete example

```text
source document A has atomic + source + segment vectors
→ move A: same source and vector IDs, updated path/facets
→ edit A: replace all A lanes atomically, old-version vectors disappear
→ delete A: replace A with an empty batch, no ghost vectors
→ rebuild from the same final inputs: identical corpus hash and ranking
```

## How was it validated?

- [Contract tests](../../tests/test_issue_265_vector_backends.py): analytic
  cosine/dot/L2 answers, ties, filters, profile/dimension/normalization checks,
  deterministic identity, reuse, edit/move/delete, atomic invalid/interrupted
  batches, real subprocess termination during a public rebuild, cross-thread
  and separate-instance concurrency, corruption diagnostics, symlink rejection,
  canonical/lexical isolation and base import isolation
- [Reproducible evaluator](../../benchmarks/vector_backends/evaluate.py) and
  [recorded measurement](../evidence/265-vectors/synthetic-mechanics.json):
  288 records, 12 dimensions, 96 filtered/lane query cases, frozen Top-10
- [Validation summary](../evidence/265-vectors/validation.json) records focused,
  full-suite, package and sanity evidence, including skips and local limits
- `.github/workflows/vector-backends.yml` reruns and uploads the same-vector
  comparison on the exact candidate; standard TESSERA CI runs aggregate and
  artifact gates. A preregistered 24-cell 256–8,192 record / 16–64 dimension
  sweep additionally measures independent cKDTree selection and native RSS
  in fresh processes; see the [complete report](../evidence/265-vectors/synthetic-scale-rss.json).
  CI status belongs to the exact head linked in the PR, not to
  this pre-merge record

## What improved?

The initial flat/SQLite fixture achieved 1.0 Recall@10 and exact score/order
agreement, 1.0 repeatability and filter correctness, zero deleted-source ghosts and identical
clean/incremental corpus hashes on the frozen synthetic fixture. This supports
storage/lifecycle parity. SQLite persistence and rollback survive reopening
and a terminated uncommitted write. Timing/memory observations in the report
are environment-specific and are not evidence of semantic-quality improvement.

The continued 24-cell size/dimension sweep found three approximate queries
below the fixed 0.95 recall review threshold (minimum query Recall@10 0.9),
while all ranked distance ratios stayed within the fixed 1.5 bound. Exact
variants matched the oracle throughout. Native process peak RSS, cold-build
and warm-query measurements are preserved in the
[complete results summary](../evidence/265-vectors/synthetic-scale-summary.md).

## What remains unimplemented?

Real English/Portuguese/mixed-corpus parity, embedding generation/profile
resolution integration and production-workload validation remain open. The
preregistered synthetic sweep supplies independent cKDTree ANN selection and
native RSS observations at bounded sizes; it does not establish semantic
quality or a production winner. Returned-score arithmetic is shared, while
cKDTree candidate selection is independent. SQLite scans and verifies the
complete snapshot; it is not an ANN competitor. Sources must
be supplied by the caller, with ordering serialized upstream for same-source
writes. There is no automatic semantic Engine/CLI activation or candidate
fusion. The full #265 card remains open with decision `ITERATE`.

## What is unlocked next?

No issue is declared unblocked by an unmerged draft. After review/merge, #158
can evaluate real frozen embedding vectors against this boundary; its other
model/data gates still apply. #157 remains independent and unmerged work is not
silently incorporated. #153/#12 are already satisfied by canonical main.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#265](https://github.com/LuigiFerronatto/TESSERA/issues/265) |
| Pull request | [Draft #293](https://github.com/LuigiFerronatto/TESSERA/pull/293) |
| Merge commit | None |
| Evidence/Learnings/Decision | [Contract](../VECTOR_BACKENDS.md), `ITERATE` |
| Benchmark record | [Synthetic mechanics](../evidence/265-vectors/synthetic-mechanics.json) |
| PR Evolution Audit | [Narrow audit](../PR_EVOLUTION_265.md) |

## Evolution

```text
canonical #153 derived ownership + #12 source lifecycle
→ this draft: replaceable vector contract and measured local mechanics
→ pending review/merge, full issue stays open
→ real frozen-model-vector evaluation coordinated with #158
```
