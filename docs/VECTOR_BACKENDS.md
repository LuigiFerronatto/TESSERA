# Experimental vector backend boundary (#265)

This opt-in Python contract accepts **already computed vectors**. It never
loads a model, contacts a provider, adds an Engine/CLI setting, changes the
lexical candidate set, or rewrites a source. It is an experimental candidate;
no production backend has been selected. #157 resolves model profiles; #158
owns embedding generation, compatibility fingerprints and candidate fusion.

## Components

- `tessera.vector_backend.VectorBackend`: library-independent protocol and
  immutable typed records, filters, requests, capabilities and results
- `ExactFlatBackend`: non-persistent correctness reference with exact search
- `tessera.vector_sqlite.SQLiteVectorBackend`: explicitly imported stdlib
  SQLite persistence with exact scanning, atomic transactions and recovery
- `tessera.vector_ckdtree.CKDTreeVectorBackend`: explicitly imported in-memory
  exact/approximate SciPy tree candidate with lazily constructed filtered trees

The flat/SQLite candidates use the same exact scoring kernel. Analytic tests independently
check cosine, dot product and squared L2. Backend comparison measures storage,
filtering and lifecycle parity, not independent ANN algorithms. SQLite is a
practical dependency-free **small local candidate**, not a claim that exact
scanning is competitive at production scale. There are no new installation
requirements; neither module is imported by deterministic Engine/CLI paths.

## Explicit usage

```python
from tessera.vector_backend import (
    SemanticIndexSpec, VectorFilters, VectorRecord, VectorSearchRequest,
)
from tessera.vector_sqlite import SQLiteVectorBackend

# Supplied by a validated embedding/representation pipeline, not a model name.
profile = "sha256:" + "a" * 64
spec = SemanticIndexSpec(profile, dimensions=3)
backend = SQLiteVectorBackend(configuration.index_dir)
backend.open(spec)
try:
    backend.replace_source("doc-guide", [VectorRecord(
        canonical_id="guide", source_document_id="doc-guide",
        source_version_hash="sha256:" + "b" * 64,
        embedding_profile_fingerprint=profile,
        representation="source", representation_version="1",
        vector=(1.0, 0.0, 0.0), source_path="docs/guide.md",
        document_type="guide",
    )])
    result = backend.search(VectorSearchRequest(
        query_vector=(1.0, 0.0, 0.0),
        embedding_profile_fingerprint=profile, top_k=10,
        filters=VectorFilters(representations=("source",)),
    ))
finally:
    backend.close()
```

`configuration` is an already resolved #153 configuration. The caller must
supply its owned **derived** `index_dir`, never its source/store path. The
backend writes only to `semantic/<profile-sha256>/sqlite-exact/vectors.sqlite3`
and SQLite's adjacent transaction journal. Existing symlink components are
rejected. This is not a sandbox against an adversary concurrently replacing
filesystem paths; the derived directory must be application-owned and trusted.
No deletion operation removes source files, identity manifests or evidence
ledgers. Index deletion/recovery is an explicit caller operation after closing
all backend handles; there is no recursive deletion helper in this API.

## Identity and compatibility

A deterministic `vec_` ID hashes canonical ID, stable source document ID,
source version, profile fingerprint, lane, representation version and
representation ID. Path, facets and evidence references do not determine
identity. A move or metadata-only update can therefore keep the same vector
ID. Distinct canonical identities and distinct lanes never collapse because
text/vectors happen to match. Segment siblings use different representation
IDs. Every hit retains the complete canonical/source/version/evidence linkage.

Each logical index admits one embedding profile, dimensionality, normalization,
metric and representation configuration. The query carries its profile
fingerprint to reject same-dimensional but incompatible vector spaces.
Dimensions, finite numeric values, nonzero cosine norms and optional unit norms
are validated before mutation. Components are stored as canonical floats.

The SQLite manifest is stored **inside the same transaction** as vector records,
not in a separately committed JSON sidecar. It records contract version, full
index spec, backend/storage version, SQLite runtime version, build/update times
and a deterministic corpus manifest hash. The spec can include selected-source,
ignore-rule and configuration hashes. A mismatch raises
`VectorIndexIncompatible` with a rebuild/namespace diagnostic. No automatic
migration or silent profile mixing takes place. A changed profile uses a
separate namespace. For backend/config/representation changes, rebuild from
canonical inputs and the matching frozen vectors in a new derived root; close
and retain/remove the old derived root separately according to caller policy.

## Lifecycle and concurrency

- `upsert(records)` adds/replaces the exact record identities supplied; it is
  **not** a source synchronization operation and intentionally retains unrelated
  versions/lanes. Use the authoritative source operation below to remove ghosts
- `replace_source(source_id, records)` atomically replaces **all** lanes and
  versions for one source. Pass its complete current representations; an empty
  batch deletes the source's vectors. Other sources are untouched
- `delete(record_ids)` is idempotent exact-identity deletion
- `rebuild(records)` atomically replaces the entire compatible logical index
- Duplicate IDs within one batch, wrong-source batches and invalid vectors
  fail before committing. Interrupted generators cannot leave partial writes
- Unchanged records are counted as reused. Corpus hashes cover vectors and
  retrieval metadata, so clean-rebuild/incremental equivalence is testable
- Flat access is serialized in-process. SQLite serializes writes across
  instances/processes, waits at most five seconds for a lock, and uses a
  transactional read snapshot. Reads do not see partially replaced sources
- Same-source concurrent writes are **last committed writer wins**. The caller
  must serialize source ingestion/order versions; no temporal authority or
  compare-and-swap source-version policy is inferred by this layer
- SQLite rollback journal and FULL synchronization recover a terminated write.
  Corrupt identity/payload/manifest state fails verification; rebuild from
  canonical input rather than accepting partial state

## Search

Filters are bounded immutable tuples of representations/source IDs plus exact
project scope, drawer or document type. Empty tuples and `None` mean no filter.
Only `facts`, `preferences` and `insights` are drawers; source/segment records
may use `drawer=None`. `None` as a filter is a wildcard, not an `IS NULL` query.
Top-K is an integer from 1 to 10,000. Results sort by descending score and then
ascending deterministic vector ID. Cosine returns cosine similarity, dot
returns dot product, and L2 returns **negative squared distance**. Larger is
better for all three. The score and its meaning remain explicit in every
result and are never named confidence, authority, validity or truth. The
returned corpus hash identifies the searched snapshot.

## Measured scope and next gates

Run `python -m benchmarks.vector_backends.evaluate --output /tmp/vectors.json`.
The committed [measurement](evidence/265-vectors/synthetic-mechanics.json) freezes
288 synthetic records (96 identities × three lanes), 12 dimensions, 24 queries
× four filter/lane settings, and a Top-10 budget. It records exact agreement,
Recall@10, repeatability, filter correctness, ghost count, incremental/rebuild
equivalence, timings, disk size and peak traced Python memory. Timings are
observations on the recorded environment, not acceptance thresholds. Python
traced memory excludes native SQLite allocation and is not process peak RSS.

Decision: **ITERATE**. Keep this slice as an opt-in correctness/lifecycle
boundary; do not select a public default. Still required before closing the
full #265 experiment: real English, Portuguese and mixed-corpus frozen vectors
from #158, model/profile integration and production-workload tradeoff evidence.
The separate preregistered sweep below adds independent cKDTree ANN selection
and bounded scale/native-RSS measurements.
Candidate fusion, semantic Engine activation, downloads and hosted databases
are not delivered here. Lexical retrieval continues unchanged even if this
entire semantic directory is absent, corrupt or unused.

## Independent cKDTree and native-memory experiment

`CKDTreeVectorBackend` is a separate explicit-import, in-memory adapter using
SciPy's compiled cKDTree neighbor selection. SciPy is already available through
TESSERA's existing scientific dependency chain; this candidate adds no package
requirement or model asset. Missing `scipy.spatial` produces an actionable error.
`epsilon=0` uses exact tree traversal; fixed `epsilon=0.5` enables approximate
nearest neighbors. Only cosine and L2 are supported. For cosine, vectors are
normalized for Euclidean tree lookup and original cosine scores are recomputed
for the returned candidates. The neighbor selector is independent of flat
scanning, although returned-score arithmetic is intentionally shared.

SciPy documents a `(1 + epsilon)` distance guarantee, not a recall guarantee;
its docs also warn that KD trees may offer little advantage in higher
dimensions (around 20 and above). These are reasons to measure, not to select a
default. See the official [query contract](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html)
and [dimensionality caveat](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html).

Typed filters are applied before tree construction. Up to four filtered trees
are cached; source mutations invalidate the cache. Initial and post-update
queries therefore pay the full filtered-tree construction cost. Selected
candidates are sorted by score and record ID, but a boundary tie can select a
different equally distant subset from flat search. Exact equality under ties
is not promised. Fixed-input repeated runs and explicit tie fixtures test
repeatability. There is no persistence or background rebuild thread.

The [preregistered sweep plan](../benchmarks/vector_backends/sweep-plan.json)
fixes all sizes, dimensions, seed, query/filter sets, Top-10 budget, epsilon,
repetitions and gates before measurement. Its [complete report](evidence/265-vectors/synthetic-scale-rss.json)
covers 256, 2,048 and 8,192 records at 16 and 64 dimensions, for flat, SQLite,
cKDTree exact and cKDTree approximate search. The swept metric is cosine;
the reported approximation bound is Euclidean distance on unit-normalized
coordinates. Deterministic synthetic inputs
are generated once per size/dimension and the same frozen bytes/checksum are
supplied to every adapter. Clustered and uniform vectors are mixed; no model
or semantic corpus is involved.

Each adapter/size/dimension cell runs in a fresh subprocess. Native high-water
RSS uses `resource.getrusage(RUSAGE_SELF).ru_maxrss`, converted to bytes for the
reported OS. Linux current RSS is sampled at baseline, materialization,
ingestion, cold queries and warm queries. This includes compiled/native
allocations, input records and the Python/scientific runtime. Absolute peak
and peak above baseline are both shown; subtracting baselines is not precise
allocation attribution. No Python-only `tracemalloc` is used in this sweep.

Measurements separate import/open, record ingestion, cold filtered queries,
warmed-query p50/p95, updates, post-update cold queries, clean rebuild and disk
footprint. Full API latency includes checksum/verification/caching policy, so
speed ratios cannot be attributed solely to the nearest-neighbor kernel.
SQLite verifies/scans full snapshots; tree warm queries reuse the unchanged
snapshot hash and filtered trees. Clean rebuild uses a fresh backend instance
and derived namespace. All cells, approximation misses and gate failures are
reported. Timing/RSS values are environment observations, not portability or
production-service guarantees.

This completes a bounded synthetic scale/native-memory and independent ANN
mechanics experiment. Real English/Portuguese/mixed frozen model-vector parity
and model/profile integration remain gated by #158. Larger/high-dimensional
production workloads require separate evidence; no default is selected.
