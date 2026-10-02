# #25 — Follow useful connections within an explicit budget

| Field | Value |
|---|---|
| Issue | [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime / benchmark experiment` |
| Pull request | Draft publication pending |
| Head commit | See exact-head PR checks |
| Merge commit | Not merged |
| Decision | `ITERATE` proposed; default remains A1 |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

The candidate can choose a small set of query-relevant connections and explain
every choice, but the frozen experiment does not justify changing the default.

## What problem existed?

Following every connection can enlarge the ranking graph and inject irrelevant
context. Relation type alone does not establish usefulness for this question.

## How did TESSERA behave before?

The current main baseline selects up to 30 lexical seeds, adds all direct
incoming/outgoing neighbors except segments, then runs DWPR and the existing
multi-signal ranker. It has no separate query-conditioned expansion budget.

## What changed or is being tested?

A new opt-in `GraphExpansionPolicy` compares no expansion (A0), the current
indiscriminate one-hop (A1), and bounded query-aware one-hop (A2). The default,
candidate generator, corpus, ranking, conflict containment and reader remain
fixed. A3 edge-confidence scoring is deferred to #26, not a prerequisite here.

## How does it work now?

**TARGET — NOT YET ON MAIN.** A2 follows only original seeds, evaluates at most
128 incident edge slots, adds at most five nodes and 1,500 whitespace tokens,
and rejects weak utility. Stable adjacency is prepared at index build/load;
no deep traversal runs. Caller-owned debug output records seeds, scores,
directions, selected/rejected edges, reason codes, truncation and budgets.
The shared hit schema and source files are unchanged.

## Concrete example

For a current-state query, an incoming `new --supersedes--> old` connection can
beat a generic `related_to` link. In the frozen Atlas case the new revision is
indeed selected, but existing ranking still puts it below five lexical hits.
Selection alone does not prove useful top-K evidence improved.

## How was it validated?

- Thirty-three boundary/invariance tests in `tests/test_issue_25_graph_expansion.py`
  cover invalid budgets, direction, cycles/two-hop exclusion, duplicate costs,
  high-degree truncation, insertion ordering, cache refresh and default parity.
- Frozen 121-note/15-query ablation with seven measured repetitions and one
  warm-up per variant; checksum and reproduction instructions are in
  [the benchmark README](../../benchmarks/graph_expansion/README.md).
  [Local aggregate evidence](../evidence/25-graph-expansion/local-ablation.json)
  records clean candidate/base commits, exact source hashes and A1 parity.
- Exact base A1 comparison uses canonical `20814a47ec0f72d7bea0639e0b057df1ecf5cded`.
- Full suite, sanity, built-package and exact-head REQUIRED dev-50 status are
  reported in the draft PR; pending remote checks are not treated as passes.

## What improved?

Initial frozen-run Recall@5 is A0 0.6429, A1 0.5357, A2 0.6429; nDCG@5 is
0.6345, 0.5761, 0.6345. Evidence density is 0.2153, 0.1512, 0.1677.
A2 improves over indiscriminate expansion but ties no expansion on quality and
has lower density than A0. The quality-over-both success gate is **not met**.
Mean returned context is A0 65.60, A1 67.87, A2 66.00 whitespace tokens.
Mean expanded context is 0, 9,251.60 and 3.87 tokens; selected graphs average
12.47/4.33, 105.00/103.20 and 13.27/5.13 nodes/edges respectively.
A1 and A2 both visit 105.00 nodes/100.47 unique edges on average in this small
fixture; no traversal-reduction claim is made here. Measured p95 retrieval is
4.12, 13.89 and 5.13 ms on the recorded local environment. A2 satisfies the
fixed A1+10 ms latency budget and its node/edge/context limits.

The candidate adds inspectable limits and a repeatable way to measure this
tradeoff. These synthetic results are not an external quality or QA claim.

## What remains unimplemented?

A production policy promotion, edge confidence, A3, total seed-context limits,
model-token accounting, deep traversal, reader/QA evaluation and a demonstrated
external relational-quality win remain unimplemented. The deterministic edge
prefix can miss a useful edge, and weak lexical seeds can select irrelevant
neighbors. Budgets limit expansion; full retrieval has other costs.

## What is unlocked next?

The evidence informs #14's graph decision. A3 still depends on #26. No new
work is declared unblocked or merged by this candidate.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) |
| Pull request | Draft publication pending |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Frozen fixture and benchmark runner; proposed `ITERATE` |
| Benchmark record | [Local ablation aggregates](../evidence/25-graph-expansion/local-ablation.json); PR exact-head Benchmark Ledger artifacts |
| PR Evolution Audit | #96/#99 established measurement; canonical base `20814a4` retains existing A1 |

## Evolution

```text
indiscriminate one-hop baseline
→ frozen A0/A1/A2 measurement with inspectable budgets
→ proposed ITERATE, default unchanged
→ confidence-aware A3 only after #26 and further evidence
```
