# TESSERA and QUMem: source-to-implementation audit

Audit baseline: canonical `main` at
`20814a47ec0f72d7bea0639e0b057df1ecf5cded`; reviewed 2026-10-02.
Owner: [#146](https://github.com/LuigiFerronatto/TESSERA/issues/146).

This is the canonical paper-fidelity map. It supersedes the implementation
claims in the 2026-08-26 narrative without discarding its design history.
**TESSERA is QUMem-inspired; full QUMem fidelity is not validated.** A working
heuristic, a successful provider call, and a faithful reproduction are different
claims. Current product contracts remain in [ARCHITECTURE](ARCHITECTURE.md),
[OUTPUT_CONTRACT](OUTPUT_CONTRACT.md) and [ADR 0001](adr/0001-core-vs-optional-llm-boundary.md).

## Paper, implementation, extension and validation

Primary source: [QUMem v1, sections 3.2–3.4](https://arxiv.org/html/2608.16168v1).
The paper column below summarizes that source; the implementation column is a
separate audit of this repository, not a result reported by the paper.

| Concept | Paper behavior | TESSERA main at the audited commit | Status | Validation owner |
|---|---|---|---|---|
| Dynamic episode construction | Classify adjacent user utterances; retain assistant replies as context | `EpisodeBoundaryTracker` compares new text with accumulated TF-IDF text and checks timeout; it accepts no role field | Implemented heuristic baseline; partial fidelity | [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) |
| Typed decomposition | Three type-conditioned extraction calls per episode | `decompose_episode_result` makes one mixed-type call or uses local end-line classification | Implemented one-pass baseline; semantic fidelity unvalidated | [#136](https://github.com/LuigiFerronatto/TESSERA/issues/136) |
| Memory lineage | Keep source episode, supporting turns and latest supporting position | Candidate objects contain type/content; metadata fields do not establish end-to-end turn lineage | Partial schema; population and inspection gap | [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) |
| Information need | Identify task-relevant historical questions before retrieval | `identify_information_need` returns one free-text sentence | Implemented single-need simplification | [#139](https://github.com/LuigiFerronatto/TESSERA/issues/139) |
| Retrieval planning | Rewrite multiple queries and select typed stores for each | `plan_retrieval` returns one query; `plan_target_stores` selects stores with keywords | Multi-query contract absent | [#140](https://github.com/LuigiFerronatto/TESSERA/issues/140) |
| User state | Produce chronological facts, preference evolution and applicable insights | `infer_user_state` returns a free-text consolidated context, without a structured state schema | Structured `Fq/Tq/Iq` absent | [#141](https://github.com/LuigiFerronatto/TESSERA/issues/141) |
| Preference trajectory | Interpret changes with temporal and contextual evidence | `ConflictResolver` preserves all ranked candidates after the P0 containment; it does not prove supersession | Safe containment implemented; full experiment pending | [#15](https://github.com/LuigiFerronatto/TESSERA/issues/15), [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16) |

Factual memories describe observed experiences or states, not an immutable truth
class. Preferences can be contextual; insights must remain grounded in evidence.
The legacy decomposer prompt still uses an overly strong immutability phrase.
That is a known semantic defect owned by #136, not a scientific definition and
not changed by this documentation-only repair.

## TESSERA-specific representation and boundaries

`Episode(beginning, middle, end)` is a **TESSERA-specific extension** for
representing a task narrative. Semantic episode membership is not the same as
Beginning/Middle/End internal representation. B/M/E neither implements nor
validates the paper's boundary classifier. The current tracker is programmatic;
it does not install runtime hooks or expose a dedicated CLI/MCP boundary tool.

The three semantic drawers remain `facts`, `preferences`, `insights`.
`procedural_anchor` is the existing compatibility type routed to `insights`;
sharing a taxonomy does not prove decomposition accuracy. Deterministic
retrieval remains usable without any generative model. The optional
orchestrator is not the final answering agent.

TESSERA's source hashes, exact-or-null evidence spans and derived Evidence Ledger
are its own provenance mechanisms. They do not substitute for supporting-turn
lineage, immutable historical revisions (#73), or evidence-sufficiency judgments.

## What the completed safety repairs actually established

- **#135:** canonical merge `c324ac2f46d48f7b49769b2fea9df0a2a93b42de`
  repaired decomposition fallback. A valid JSON list, including `[]`, is assisted
  success. Expected provider failures or invalid output select deterministic
  fallback with diagnostics. Programming errors propagate. See the
  [validated stage record](test-cards/135-decomposition-fallback.md).
- **#16 P0:** canonical merge `708c973e23d5c4eb8a52d359a2cadc153e161a90`
  removed destructive newest-only filtering. Candidate identity, evidence and
  ranking order survive. This is not full temporal conflict resolution. See the
  [containment record](test-cards/16-conflict-resolver-containment.md).
- **MCP boundary:** pure decomposition occurs before the commit phase. MCP
  reports failed assistance before any fallback write; it must not be described
  as silently persisting offline fallback after a provider failure. The Python,
  Hook and CLI paths share candidate construction but have their own documented
  execution/error boundaries. See [MCP_RUNTIME](MCP_RUNTIME.md).

## Ownership of the remaining experiments

- #135 owns fallback integrity; #136 owns type semantics and one-pass versus
  three-pass validation; #137 owns episode/turn lineage; #138 owns boundaries
- #139 owns information needs; #140 owns **WHAT** queries/stores retrieve
  evidence; #17 separately owns **HOW** retrieval strategies are selected
- #141 owns structured query-conditioned state; #20 separately owns evidence
  sufficiency, conflict/ambiguity status and abstention control flow
- #142 owns the frozen end-to-end fidelity suite; #143 owns the personalized
  memory benchmark; #144 owns exposure of validated contracts across surfaces
- #145 coordinates these cards; #146 corrects documentation. #78 separately
  owns project-neutral cleanup of remaining historical/deep-dive material

[ROADMAP](ROADMAP.md) and the linked issues carry dependencies. An open card or
an unmerged PR never promotes a capability to `IMPLEMENTED` or `VALIDATED`.
Future status updates require canonical merge evidence plus the relevant tests,
review decision and benchmark, rather than issue creation or unit coverage alone.

## Historical evolution retained

The August narrative recorded three useful engineering lessons: writes need
explicit path handling; a timeout/lexical heuristic can be useful without being
a learned continuity model; and typed extraction must pass through the same
write gate as manual candidates. The later #135 and #16 repairs made failure
and conflict handling more truthful.

The old narrative also reported small live-provider demonstrations. Their
latencies, memory counts and corpus-specific node/edge totals are anecdotal
historical observations, not a frozen benchmark or evidence of QUMem fidelity.
They do not justify a claim that the current simplifications are sufficient.
No current TESSERA accuracy or cost result is inferred from the paper's results.

## Reproducible audit

Inspect `tessera/models.py`, `episode_boundary.py`, `decomposer.py`,
`orchestrator.py`, `conflict.py`, and their matching tests at the baseline SHA.
Run:

```bash
python -m pytest tests/test_decomposer.py tests/test_conflict_containment.py -q
```

Dedicated documentation regression checks are carried by [PR #284](https://github.com/LuigiFerronatto/TESSERA/pull/284). This cleanup does not assume that candidate is merged. They do not measure semantic boundary quality, extraction fidelity,
preference reconstruction, or the unimplemented full regression suite.

Benchmark applicability: NOT_APPLICABLE. This change corrects prose and
non-executable docstrings only; no prompt, algorithm or benchmark result changes.
