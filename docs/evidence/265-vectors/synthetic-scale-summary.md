# Synthetic vector scale and native RSS (#265)

This is the complete preregistered mechanical sweep, not a semantic-quality
result. Frozen inputs, filters, Top-10 budget and epsilon stayed fixed.
Native peak RSS includes the scientific runtime, input records, native
allocations and lifecycle validation. Timings are local observations. Warm
API latency includes each adapter's different verification/cache policy;
cold filtered-tree build cost remains explicit.

| Records | Dimensions | Backend | Mean Recall@10 | Min query Recall@10 | Warm all-filter p50 (ms) | Cold all-filter (ms) | Native peak RSS (MiB) |
|---:|---:|---|---:|---:|---:|---:|---:|
| 256 | 16 | exact-flat | 1.000000 | 1.00 | 5.121 | 6.955 | 130.73 |
| 256 | 16 | sqlite-exact | 1.000000 | 1.00 | 15.295 | 15.731 | 132.96 |
| 256 | 16 | ckdtree-exact | 1.000000 | 1.00 | 0.244 | 5.674 | 131.25 |
| 256 | 16 | ckdtree-ann | 1.000000 | 1.00 | 0.264 | 6.080 | 131.39 |
| 256 | 64 | exact-flat | 1.000000 | 1.00 | 10.107 | 10.960 | 131.05 |
| 256 | 64 | sqlite-exact | 1.000000 | 1.00 | 29.901 | 31.124 | 134.07 |
| 256 | 64 | ckdtree-exact | 1.000000 | 1.00 | 0.460 | 11.000 | 133.25 |
| 256 | 64 | ckdtree-ann | 1.000000 | 1.00 | 0.470 | 10.758 | 132.46 |
| 2048 | 16 | exact-flat | 1.000000 | 1.00 | 42.664 | 43.892 | 136.97 |
| 2048 | 16 | sqlite-exact | 1.000000 | 1.00 | 125.719 | 122.814 | 142.00 |
| 2048 | 16 | ckdtree-exact | 1.000000 | 1.00 | 0.258 | 43.403 | 138.09 |
| 2048 | 16 | ckdtree-ann | 0.997222 | 0.90 | 0.249 | 42.580 | 137.19 |
| 2048 | 64 | exact-flat | 1.000000 | 1.00 | 85.922 | 87.528 | 145.02 |
| 2048 | 64 | sqlite-exact | 1.000000 | 1.00 | 252.007 | 238.975 | 152.41 |
| 2048 | 64 | ckdtree-exact | 1.000000 | 1.00 | 0.500 | 86.572 | 148.61 |
| 2048 | 64 | ckdtree-ann | 1.000000 | 1.00 | 0.496 | 89.115 | 147.07 |
| 8192 | 16 | exact-flat | 1.000000 | 1.00 | 204.339 | 197.550 | 158.00 |
| 8192 | 16 | sqlite-exact | 1.000000 | 1.00 | 596.694 | 571.096 | 172.36 |
| 8192 | 16 | ckdtree-exact | 1.000000 | 1.00 | 0.532 | 181.190 | 159.41 |
| 8192 | 16 | ckdtree-ann | 0.994444 | 0.90 | 0.317 | 220.791 | 158.15 |
| 8192 | 64 | exact-flat | 1.000000 | 1.00 | 397.936 | 367.304 | 188.88 |
| 8192 | 64 | sqlite-exact | 1.000000 | 1.00 | 1046.660 | 1084.100 | 214.16 |
| 8192 | 64 | ckdtree-exact | 1.000000 | 1.00 | 0.620 | 407.763 | 191.01 |
| 8192 | 64 | ckdtree-ann | 1.000000 | 1.00 | 0.640 | 365.330 | 190.70 |

All exact variants matched flat on every cell. Filter correctness and
repeatability were 1.0, deleted-source ghosts were zero, and fresh clean
rebuilds matched incremental final snapshots in all 24 cells.

The approximate candidate had 3 queries below the preregistered 0.95
recall review threshold across the sweep; minimum query Recall@10 was
0.90. Its maximum ranked unit-L2 distance ratio was 1.059916,
within the fixed 1.5 approximation bound. Those misses are retained.

Decision: **ITERATE**. Independent ANN mechanics and bounded synthetic
scale/native-memory measurement are now supplied. No default backend or
production-scale/semantic-quality claim follows. Real English, Portuguese and
mixed-corpus frozen model vectors and profile integration remain gated by #158.

[Full machine-readable report](synthetic-scale-rss.json) ·
[Preregistered plan](../../../benchmarks/vector_backends/sweep-plan.json) ·
[Contract and interpretation](../../VECTOR_BACKENDS.md)
