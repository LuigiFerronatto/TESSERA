# #138 — Compare episode membership without losing source turns

| Field | Value |
|---|---|
| Issue | [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) |
| Record status | `IN_PROGRESS` preparation; reviewed-fixture readiness remains `BLOCKED` |
| Capability type | `benchmark` |
| Pull request | Publication pending |
| Head commit | Candidate source hashes in local evidence; exact remote head pending |
| Merge commit | Not merged |
| Decision | `PENDING`; no new default selected |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

Prepare a fair, inspectable experiment before deciding whether user-aware episode
boundaries should replace the current heuristic.

## What problem existed?

Assistant/tool vocabulary can cause boundaries unrelated to the user's task.

## How did TESSERA behave before?

The current tracker compares every untyped text turn with accumulated episode
text and also splits after a timeout. Assistant/tool vocabulary can therefore
start new episodes even while the user continues a task. Its B/M/E output is
TESSERA-specific rendering, not QUMem's semantic membership decision.

## What changed or is being tested?

An opt-in repository-only harness runs unchanged E0 against E1 (adjacent-user
lexical continuity) and E3 (the same signal plus a separately visible user-gap
timeout). Source role/order/content/IDs are explicit. All context survives in
the grouped source records. No installed runtime, persistence, CLI/MCP or typed
decomposition behavior changes.

## How does it work now?

**TARGET — NOT YET ON MAIN:** run the opt-in harness from the source checkout;
the installed tracker remains E0. Membership is decided before optional B/M/E.

## Concrete example

For example, a user asks about garden irrigation, the assistant mentions
unrelated physics, and the user follows up on irrigation. E1/E3 keep all three
turns together. A 121-minute pause on the same task stays together in E1 but
splits operationally in E3. This distinction is observable in decision traces.

## How was it validated?

The [frozen experiment and protocol](../../benchmarks/episodes/README.md) contain
13 synthetic dialogues / 52 turns, including short acknowledgements, tool calls,
shared-vocabulary changes and paraphrases. The fixture hash is
`c3ac0e48f95fd41af259dc25441dc7d563a5a14b97e7fa5e555786d3562e8a87`.
These are synthetic author-draft labels, not independently human-reviewed labels.

A label-blinded packet generator preserves source records, leaves reviewer
fields/ballots blank and refuses to overwrite existing review work. The review
required CLI gate fails closed. Unit tests cover source conservation, explicit
roles, short-turn and topic-switch handling, timeout separation, invalid inputs,
metric denominators, repeatability, review blinding and the unchanged E0 API.

Draft-only diagnostic results are recorded in [local evidence](../evidence/138/local-diagnostics.json):

| Draft diagnostic | E0 | E1 | E3 |
|---|---:|---:|---:|
| Boundary precision | 0.1154 | 0.8000 | 0.6667 |
| Boundary recall | 0.5000 | 0.6667 | 0.6667 |
| Boundary F1 | 0.1875 | 0.7273 | 0.6667 |
| False split rate | 0.6970 | 0.0303 | 0.0606 |
| False merge rate | 0.5000 | 0.3333 | 0.3333 |
| Macro WindowDiff | 0.6923 | 0.1346 | 0.2115 |
| Identical repeated output | yes | yes | yes |
| Human boundary quality / downstream delta | unmeasured | unmeasured | unmeasured |

These numbers demonstrate executable measurement only; they are not a quality
win or a KEEP decision. Known E1/E3 failures are retained: shared vocabulary can
hide a topic shift, a short acknowledgement can obscure the next topic change,
and a paraphrase can falsely split. E3 adds a false split for a long pause.

## What improved?

The preparation now makes source membership and independent timeout reasons
inspectable and provides a reproducible comparison with a real E0 baseline.
No empirical downstream improvement has been established.

## What remains unimplemented?

Independent human annotation/adjudication, reviewed-label scoring, representative
holdout and downstream decomposition-quality evaluation remain unimplemented.
The #297 future projection is documented precisely, including the missing
source-ID/session/task binding and empty-content incompatibility; no competing
canonical turn model or durable adapter is introduced here. E2 is not selected.

## What is unlocked next?

No canonical dependency is unlocked: #74 is satisfied, but #138 still lacks
independent human-reviewed boundaries. #136/#137/#177 integration remains separate.


See the candidate PR for exact-head CI; local command results are reported there.
The REQUIRED dev-50 retrieval gate is separate and cannot prove episode quality.
After human review, score reviewed boundaries and holdout cases, then compare
fixed downstream decomposition. Only a reviewed decision can select a runtime
variant. No merges or issue closures are part of this preparation. After a future
merge, record its canonical SHA and reconcile the roadmap/lifecycle explicitly.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Canonical baseline | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Issue/Test Card | [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) |
| Pull request | Publication pending |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | [Draft diagnostics](../evidence/138/local-diagnostics.json); human metrics null; `PENDING` |
| Benchmark record | REQUIRED exact-head dev-50 pending; distinct from human segmentation quality |
| PR Evolution Audit | Current E0 baseline; this benchmark-only candidate; [#297](https://github.com/LuigiFerronatto/TESSERA/pull/297) remains an unmerged independent lineage draft |

## Evolution

Untyped E0 on canonical main → opt-in E1/E3 and unreviewed synthetic preparation
→ independent human annotation and downstream comparison → later reviewed
runtime decision. No stage is presented as merged or empirically validated.
