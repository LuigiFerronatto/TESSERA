# #168 — Name the durable-memory boundary without promoting future behavior

| Field | Value |
|---|---|
| Issue | [#168](https://github.com/LuigiFerronatto/TESSERA/issues/168) |
| Record status | `IN_PROGRESS` |
| Capability type | `documentation` |
| Pull request | Candidate branch `docs/168-durable-memory-boundary` |
| Merge commit | Not merged |
| Decision | `PENDING` contract review |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-10-02 |

## In one sentence
Document the distinction between durable source records, rebuildable evidence/indexes and ephemeral generated context.

## What problem existed?
Existing primitives did not have one explicit LTM boundary, making it easy to
confuse generated state with admitted durable memory or hashes with history.

## How did TESSERA behave before?
Explicit canonical writes persisted source records, while retrieval and optional
consolidation returned views. Current source overwrite could lose older bodies;
full context invalidation and temporal/admission contracts were not implemented.

## What changed or is being tested?
A proposed contract inventories current behavior and answers eight ownership
questions without absorbing downstream Test Cards. Six regression tests exercise
the already-existing durable/ephemeral separation. One misleading immutable-fact
docstring is corrected; executable runtime code is unchanged.

## How does it work now?
TARGET — NOT YET ON MAIN: readers use [LONG_TERM_MEMORY](../LONG_TERM_MEMORY.md)
to distinguish current operations from future lineage, revision, admission,
utility, event-lifecycle and context-invalidation responsibilities. The document
is a proposed contract candidate, not an accepted ADR or activated runtime.

## Concrete example
A query-conditioned summary may say what an agent should do now; returning that
summary does not create a canonical memory. A later successful explicit write
changes source truth; a stale derived context must be recomputed rather than
saved back as a competing source.

## How was it validated?
`tests/test_ltm_boundary_contract.py` proves rejection without a source file,
no auto-persistence by successful/failed assistance, retrieval source integrity,
reconstruction after index deletion and source-version freshness detection.
Documentation checks verify explicit current/target boundaries and owning cards.
Full-suite and exact-head CI evidence are recorded in the PR.

## What improved?
One document defines source ownership, three drawers, safe consumer flow and
where incomplete mechanisms belong. It explicitly discloses current overwrite
limits instead of claiming full revision history.

## What remains unimplemented?
All child runtime work remains separately gated: #73 history, #15/#16 temporal
supersession, #137 lineage, #19 admission, #21 utility, #196/#177 lifecycle,
#169/#167 context and #171 semantic API. No empirical usefulness or contamination
improvement is claimed from documentation tests.

## What is unlocked next?
Maintainer review may KEEP or ITERATE the boundary. Canonical contract acceptance
does not itself implement or validate the dependent runtime capabilities.

## Technical provenance
- Baseline:`20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Contract:[LONG_TERM_MEMORY](../LONG_TERM_MEMORY.md)
- Governing boundary:[ADR0001](../adr/0001-core-vs-optional-llm-boundary.md)
- Tests:`tests/test_ltm_boundary_contract.py`
- Decision: pending, no new default policy accepted

## Evolution
Separate validated primitives → explicit proposed durable/ephemeral contract →
review/canonical decision → separately measured child implementations.
