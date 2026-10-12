# Frozen vector mechanics (#265)

Run from a repository checkout with the base package installed. No provider
credentials or embedding models are needed:

```bash
python -m benchmarks.vector_backends.evaluate --output /tmp/vector-mechanics.json
```

`frozen.json` contains synthetic numeric vectors generated once with seed 265,
then committed as the immutable input. Both backends receive exactly the same
records, query vectors, filters and Top-10 budget. No semantic corpus or model
quality is represented. The script asserts 100% exact score/order agreement,
Recall@10, filter correctness, no ghosts and clean/incremental equivalence;
performance measurements are descriptive and environment-dependent.

[Contract and limitations](../../docs/VECTOR_BACKENDS.md).
[Recorded candidate measurement](../../docs/evidence/265-vectors/synthetic-mechanics.json).
The dedicated `Frozen vector mechanics` CI workflow uploads a fresh exact-head
report; standard TESSERA CI separately covers the base suite and packaging.

## Preregistered scale and native RSS

```bash
python -m benchmarks.vector_backends.scale_sweep --output /tmp/vector-scale-rss.json
```

The immutable `sweep-plan.json` was recorded before measurements. All 24
backend/size/dimension cells run in fresh child processes using the same frozen
synthetic inputs and Top-10 budget. Flat, SQLite, cKDTree exact and cKDTree
approximate (`epsilon=0.5`) variants are compared; recall misses remain visible.
The report includes native high-water/current RSS, cold/filter-tree build
costs, warm timings, incremental changes and fresh clean-rebuild equivalence.
See the contract for memory/timing interpretation and remaining real-corpus
gates. Run on Linux or macOS for defined native RSS units; each child has the
preregistered ten-minute safety timeout. No model data is fetched.
