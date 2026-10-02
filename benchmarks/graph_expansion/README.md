# Query-aware, budgeted one-hop expansion (#25)

This is a frozen synthetic **mechanism ablation**, not an estimate of real-world
QA quality. The current runtime default remains indiscriminate one-hop (A1).
The proposed decision is **ITERATE**, retaining A2 only as an opt-in experiment.

## Run

```bash
python -m benchmarks.graph_expansion.run --output-dir /tmp/graph-ablation
```

The runner checks the fixture SHA-256, builds the same 121-document corpus once,
and evaluates 15 queries with the unchanged top-30 TF-IDF seed generator,
DWPR/multi-signal ranking, top-5 output, conflict containment and no reader.
One warm-up is followed by seven interleaved measured repetitions per variant:

- A0: no expansion; retain the seed-induced graph and existing ranking
- A1: existing indiscriminate incoming/outgoing one-hop expansion
- A2: query-aware, budgeted incoming/outgoing one-hop selection
- A3: **not implemented**; confidence-aware traversal remains conditional on #26

Queries cover four domains' current state and neutral controls, four
multi-evidence cause cases, an unmodeled relation, a two-hop limitation and an
unmatched query. The entire fixture and policy were fixed before the first
measurement. Gold IDs enter only the evaluator; source files contain the notes
and relations, never expected answers or query labels. No per-question tuning,
provider call, model download, synthetic reader answer, or QA accuracy is used.

For an exact older baseline, run this same script from its clean worktree with
that worktree first on PYTHONPATH and `--baseline`. This runs the unmodified
runtime default; it does not backport A2 to the baseline:

```bash
cd /path/to/clean/base
PYTHONPATH="$PWD" /path/to/venv/bin/python \
  /path/to/candidate/benchmarks/graph_expansion/run.py \
  --fixture /path/to/candidate/benchmarks/graph_expansion/fixture.json \
  --baseline --output-dir /tmp/graph-base
```

`summary.json` records the runtime commit/dirty state, environment, fixture
checksum, policy, aggregate and per-kind metrics. `results.json` contains
per-query IDs/scores, repeated timings and complete inspectable decisions.
Debug collection is outside latency measurement, and its result IDs/scores
must exactly match the ordinary path. Every variant must have identical seeds;
every repetition must have identical IDs/scores. Failed invariants abort.

## Fixed policy and budget meaning

A2 allows one hop, five added nodes, 128 incident edge slots and 1,500 added
whitespace tokens, with minimum utility 0.45. The score is:

```text
0.55 * relation/query relevance prior
+ 0.35 * neighbor TF-IDF cosine
+ 0.10 * seed TF-IDF cosine
```

The fixed bilingual intent lexicon prioritizes directed supersession for
current/previous queries, causal relations for why queries, dependency relations
for prerequisites and existing procedural relation types for how/deploy queries.
A `new --supersedes--> old` edge is preferred incoming for current-state queries
and outgoing for previous-state queries. This is an expansion heuristic, **not**
edge confidence, truth, authority or temporal-state resolution. Untyped/unknown
relations receive a small generic prior. No relation is automatically trusted.

Stable incident lists are derived at index build/load, including cache loads;
this adds O(V+E) derived storage and index-time adjacency ordering work. Query
traversal examines a bounded prefix round-robin across the original seeds,
ordered by seed similarity then ID. A high-degree seed cannot consume more than
128 slots, and duplicate edge slots also consume the budget. Truncation is
explicit. The deterministic prefix may omit a useful edge; this is a deliberate
coverage tradeoff. Newly selected nodes are never traversed. Segment nodes are
excluded. Selection tie-breaks use utility, candidate ID and edge IDs. Duplicate
selected nodes consume context once; an oversized candidate is skipped so a
later smaller candidate can fit. Seed-to-seed edges remain unchanged; among
expanded nodes only selected seed-incident edges enter A2 PageRank.

Budgets constrain **added evidence**, not the existing seed context or total
result body size. Visit counts describe expansion only. Full-corpus TF-IDF,
segment evidence extraction, PageRank, conflict handling and related-ID
navigation retain their existing costs. Thus this is not a total CPU/runtime or
model-token hard limit. End-to-end retrieval latency is measured separately;
the frozen budget is A2 p95 no more than A1 p95 + 10 ms on the same run.

## Metric definitions and decision

Recall@5, binary nDCG@5, MRR and hit rate use evaluator-owned relevant IDs.
Evidence density is the fraction of returned whitespace tokens belonging to
relevant documents; document precision is also reported. Density is not
sentence-level evidence validity. Context is summed per query. Node/edge/slot
visits and selected-subgraph sizes quantify expansion costs separately.
Unmatched queries are excluded from relevance means and retained in context,
latency and empty-result counts. Reader and downstream QA accuracy are null.

The first frozen run finds A2 better than A1 but tied with A0 on aggregate
Recall@5/nDCG@5; its density remains below A0. Selected graph evidence can still
rank below lexical distractors, and weak lexical seeds can trigger irrelevant
relation expansions. This does **not** meet the quality-over-both gate. It is
reason to retain the existing default and iterate, not claim a production gain.
See [the Test Card record](../../docs/test-cards/25-budgeted-graph-expansion.md).

The existing `REQUIRED` Benchmark Ledger remains the independent exact-head
LongMemEval V1 dev-50 regression gate against immediate parent and #96. Its
session adapter has no active relation edges; a green default dev-50 result
protects compatibility but cannot establish A2's relational-quality benefit.
