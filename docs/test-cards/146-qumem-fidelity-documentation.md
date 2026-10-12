# #146 — Distinguish QUMem research from current TESSERA behavior

| Field | Value |
|---|---|
| Issue | [#146](https://github.com/LuigiFerronatto/TESSERA/issues/146) |
| Record status | `IN_PROGRESS` |
| Capability type | `documentation` |
| Pull request | Candidate branch `docs/146-qumem-fidelity` |
| Merge commit | Not merged |
| Decision | `PENDING` independent review |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-10-02 |

## In one sentence
Explain which research ideas TESSERA implements, approximates, or has not yet validated.

## What problem existed?
The old deep dive called heuristic episode construction and one-pass extraction
implemented QUMem behavior, mixed current and historical results, and understated
planning/state gaps.

## How did TESSERA behave before?
The runtime already had optional assistance, safe decomposition fallback and
non-destructive conflict containment. The prose implied stronger fidelity than
those mechanisms establish.

## What changed or is being tested?
One dated source-to-runtime table assigns each gap to its owning Test Card;
references and non-executable docstrings use the same distinctions.

## How does it work now?
TARGET — NOT YET ON MAIN: the candidate explains the current heuristic,
one-pass, single-query and free-text baseline. It preserves historical lessons
without promoting experiments or changing runtime behavior.

## Concrete example
Previously: a section headed implemented dynamic episode construction.
Candidate: implemented timeout/TF-IDF heuristic, with role-aware continuity
validation still owned by #138. Beginning/Middle/End is TESSERA-specific.

## How was it validated?
`tests/test_qumem_fidelity_docs.py` checks the paper/code/owner table, lifecycle
boundaries and docstring language. Existing decomposer and conflict tests check
the unchanged contracts. Executable ASTs are compared against the canonical
baseline after removing only module/class/function docstrings. Exact counts and
remote gates are recorded in the PR, not inferred from this stage status.

## What improved?
Readers can distinguish implemented safety repairs from still-unvalidated
scientific claims and find each remaining experiment.

## What remains unimplemented?
#136–#144 scientific/runtime work remains independently gated. In particular,
the legacy factual-immutability prompt is acknowledged and remains #136's
semantic defect; this prose-only repair does not change prompts. #78 remains
owner of other historical/private-project cleanup.

## What is unlocked next?
No runtime dependency is unlocked by a documentation candidate.

## Technical provenance
- Baseline: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Primary source: [QUMem v1](https://arxiv.org/html/2608.16168v1), sections 3.2–3.4
- Canonical audit: [QUMEM-GAP-ANALYSIS](../QUMEM-GAP-ANALYSIS.md)
- Existing repairs: [#135](135-decomposition-fallback.md), [#16 P0](16-conflict-resolver-containment.md)
- Decision: pending independent review; no runtime benchmark claimed

## Evolution
Historical simplified implementation claims → dated source/runtime separation
→ independent documentation review → future child experiments with their own
canonical merge and validation evidence.
