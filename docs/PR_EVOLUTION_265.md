# PR evolution audit — vector backend mechanics (#265)

The audit is scoped to the contract this candidate changes. It does not infer
that every open model/retrieval experiment is implemented.

| Delivery | Canonical evidence | Relevant surface | Interpretation |
|---|---|---|---|
| #153 configuration-v2 ownership | Merged; [stage record](test-cards/153-configuration-v2-store-sources-index.md) | Resolved `store`, read-only `sources`, derived `index` | This candidate consumes explicit `index_dir`; it does not rediscover configuration |
| #12 incremental indexing | #246, `971801cd89b6ce7b890df9ceb43b6afff9fa0964` | Stable source identity and source lifecycle | Authoritative source versions remain supplied by the canonical layer |
| #70 structural segments | Present in base `20814a47ec0f72d7bea0639e0b057df1ecf5cded` | Canonical parent/source/span linkage | Segment vectors have a separate representation ID; no source parsing is copied |
| This #265 candidate | Not merged | `vector_backend.py`, `vector_sqlite.py`, tests/evaluator/docs | First optional vector storage contract; experimental `ITERATE` |

No prior vector backend is replaced. The #157 typed-model-profile draft is not
merged or imported by this work. A fingerprint is explicit caller input so the
storage boundary remains independent from model/provider configuration.

The exact-flat reference and SQLite candidate use the same score kernel; the
analytic metric tests independently establish small-fixture correctness.
Measured synthetic parity does not establish a preferred semantic encoder,
ANN backend or real-corpus quality outcome. No claim closes #265 or unlocks
unmerged downstream work. Human review and canonical post-merge reconciliation
remain required.
