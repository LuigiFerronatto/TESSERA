# Source history lifecycle experiment (#73)

## Reproduce

```bash
python -m pip install -e '.[dev]'
python benchmarks/revisions/lifecycle.py --documents 8 --versions 4 --output /tmp/revisions.json
python -m pytest -q tests/test_issue_73_revision_history.py
```

`results.json` is the committed synthetic measurement. Every mode evolves eight
logical browser preferences through four distinct source versions. It records
24 old document-evidence IDs, deletes the entire derived index, restarts and
attempts reconstruction from the surviving durable materials. A no-op index
pass is measured separately. Latency is reported for context, not gated.

- **R0:** overwrite the same source, no history
- **R1:** create independent memories with explicit `supersedes` relations; use
  current Foundation retrieval without future temporal filtering
- **R2:** same current-source corpus as R0, opt-in durable revision history
- **R3:** R2 plus a benchmark-only mapping from memory IDs to current document
  hashes. Query checks pointer agreement; no validity/authority inference and
  no extra live memories. This is **not** an implementation/evaluation of a
  complete temporal model

## Results (Python 3.12.14, Linux)

| Metric | R0 | R1 | R2 | R3 pointer |
|---|---:|---:|---:|---:|
| Old source reconstructability | 0/24 | 24/24 | 24/24 | 24/24 |
| Old canonical evidence completeness | 0/24 | 24/24 | 24/24 | 24/24 |
| Explicit supersedes edges | 0 | 24 | 0 | 0 |
| Live documents for eight logical memories | 8 | 32 | 8 | 8 |
| Duplicate live memory rate | 0% | 75% | 0% | 0% |
| Current-version Top-1 accuracy | 8/8 | 0/8 | 8/8 | 8/8 |
| Durable bytes (source + history/pointer) | 11,592 | 48,672 | 146,760 | 147,464 |
| Storage/current-only source bytes | 1.00x | 4.20x | 12.66x | 12.72x |
| Total sources parsed over four index passes | 32 | 32 | 32 | 32 |
| No-op sources parsed | 0 | 0 | 0 | 0 |

Duplicate rate is `(live documents - logical documents) / live documents`.
Current accuracy is a query's top hit containing the final recorder value for
its unique topic token. The historical-evidence metric uses canonical document
records; separate contract tests cover actually issued paragraph evidence IDs,
source deletion, metadata-only changes, moves, reverts, archive failure,
corruption, opt-out/re-enable and index deletion.

## Interpretation and decision

**Propose KEEP opt-in R2**, with costs visible. It passes this card's durability,
inspectability, no-duplicate and version/independent-memory distinction gates.
R0 loses all tested old versions. R1 preserves sources but its independent live
memories require the downstream supersession/temporal model to avoid stale
retrieval. The R2 archive adds no live ranking candidates. Its SQLite fixed
pages, full copies and provenance cause material overhead (12.66x for this
small 11.6 KB current corpus); this is a measured tradeoff, not a claim that
archiving is free or universally faster. Capture/index/query latency is in the
JSON; environment and SQLite/filesystem overhead make it nondeterministic.

The pointer-only R3 adds 704 bytes here with no measured benefit. Defer its
production integration and **full temporal-validity evaluation** to #15. A
pointer alone cannot tell whether a source is true, authoritative or valid.

This fixture is intentionally simple, deterministic and public. It is not a
LongMemEval, production scalability or competitive-quality claim. Opt-in/off
result-parity tests and the existing sanity suite guard unchanged retrieval.
No external source is rewritten by the experiment's Engine; fixture changes
are made explicitly by the benchmark itself. Unit tests rerun the smaller
2x3 experiment twice and compare all non-latency metrics.
