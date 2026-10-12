# Source-episode lineage structural audit (#137)

This frozen synthetic experiment measures inspectability and reference retention,
not extraction quality. The fixture contains a one-turn fact, assistant rationale
plus later user confirmation, disjoint same-episode spans, an out-of-bounds
candidate, and old/new preference expressions across episodes. The unsupported
candidate is exercised by `tests/test_episode_lineage.py`, which expects rejection.

The provider response is a fixed test double in both versions. Its source IDs
are fixture inputs, never model predictions or independently reviewed labels.
Supporting-turn semantic precision/recall and downstream preference-trajectory
accuracy are `null` and explicitly not measured. Valid IDs alone do not prove
that a candidate is supported. No provider calls, credentials, downloads or paid
services are used.

```bash
python benchmarks/lineage/run.py --implementation-root . --output artifacts/lineage/candidate.json
# Run against a clean canonical-base checkout using the SAME fixture/runner:
python benchmarks/lineage/run.py --implementation-root ../canonical-base --output artifacts/lineage/baseline.json
python -m pytest tests/test_episode_lineage.py
```

The legacy API receives all source text in its existing section representation.
Its real canonical decomposer ignores the additional candidate supporting-turn
fields, rather than this runner emulating the old implementation. The candidate
receives actual `EpisodeTurn` records. Both runs write the same five candidate
texts and types, rebuild from the persisted sources, and query the same terms.

Reports include the fixture checksum, aggregate runtime-Python checksum, checkout
revision, source/memory byte counts, actual decomposition-prompt UTF-8 bytes, linked-source completeness, structural
support retention, provable-span retention, and write/index/rebuild/result parity.
The runtime checksum identifies working-tree code independently of the checkout
revision; an uncommitted candidate must not be called an exact-head CI result.
Byte counts are fixture-specific storage overhead, not a scalability or latency
claim. See `docs/evidence/137/` and the Test Card stage record.

Benchmark applicability remains REQUIRED. This audit supplements the repository's
exact-head deterministic LongMemEval dev-50 gate; it does not replace that gate
or validate QUMem semantic extraction or state reconstruction.
