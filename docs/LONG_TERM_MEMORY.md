# Long-Term Memory: durable records and ephemeral views

Status: **PROPOSED contract candidate**, owned by
[#168](https://github.com/LuigiFerronatto/TESSERA/issues/168).
Audited current baseline: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`.
This document names an architecture boundary; it does not accept an ADR, activate
new behavior, or promote any unmerged capability.

## The boundary

Long-Term Memory (LTM) is TESSERA's durable, scoped record layer. Generated
memories enter it through the canonical persistence contract. Separately
selected external source documents remain source evidence under their original
ownership; indexing them does not mean TESSERA authored or admitted every claim.

```text
canonical source / durable memory
    != disposable index or Evidence Ledger summary
    != query-conditioned state
    != Working Context packet
    != final answer
```

Exactly three semantic drawers remain `facts`, `preferences`, `insights`.
Documents, instructions, source episodes, relations and revisions are not extra
drawers. A factual record may describe a changing state; factual does not mean
immutable or permanently true. A source hash proves a content version, not truth.

## What exists on the audited main

| Responsibility | Current executable contract | Limitation / future owner |
|---|---|---|
| Canonical persistence | Markdown + normalized metadata; public writers run the #92 gate | The gate is narrow safety/admission, not semantic usefulness (#19) |
| Identity and scope | Stable canonical IDs, explicit source/store/index boundaries | Cross-repository reach/exposure policy remains #257 |
| Three typed drawers | Existing typed writers and source classification | Typed extraction fidelity remains #136 |
| Provenance | Source identity, version hashes, exact-or-null evidence spans | Durable supporting-turn lineage remains #137 |
| Index lifecycle | Rebuildable graph/lexical index and derived Evidence Ledger summary | Source overwrite can lose old bodies until #73 is validated |
| Read operations | Deterministic retrieval and optional free-text consolidation | Structured state #141, Context Compiler #169 and Working Context #167 are not implemented |
| Conflict handling | P0 containment preserves all ranked candidates | No complete supersession/temporal arbitration (#15/#16) |
| Explicit task hooks | Caller-invoked library methods | No universal runtime lifecycle installation (#196/#177/#190) |

Candidate PRs from later work do not change this baseline table until a canonical
merge, review decision and lifecycle reconciliation establish delivery.

## Persistence policy: answers and reserved ownership

1. **Durable versus ephemeral:** only a successful explicit canonical write
   changes generated memory. Query plans, scratch reasoning, context packets and
   final answers stay ephemeral unless a separately authorized admission/write
   operation selects supported content. Returning or serializing a view does not
   admit it automatically.
2. **Generated insights:** the current writer can persist an explicitly supplied
   insight through the existing gate; it does not establish later usefulness or
   semantic truth. #19 owns evidence-aware admission, #21 measured utility, and
   #136 decomposition fidelity. This contract does not invent a usefulness score.
3. **Revision, append or supersede:** a new independent claim needs its own
   identity. Evolution of the same source is a revision responsibility (#73),
   while temporal validity and supersession are #15/#16. Current overwrite
   behavior must be disclosed; stable IDs alone are not a history guarantee.
4. **Lineage before durable derivation:** retain real source/evidence references
   and never fabricate turns or time precision. #137 owns validated episode/turn
   requirements; manual records cannot be relabeled as automatically verified
   derivations. Absence of lineage must stay visible.
5. **Stale/invalid observations:** a hash mismatch marks evidence stale, not false.
   Current containment does not silently remove older candidates. Claims of
   preserved historical bodies require #73; temporal invalidation requires
   #15/#16, not a generic recency rule.
6. **Source truth versus cache metadata:** canonical source text and explicit
   fields are authoritative records; parser defaults must retain origin labels.
   Retrieval scores, selected spans, embeddings, query plans and context views
   remain derived. Rebuilding a cache cannot rewrite canonical records.
7. **Run-end candidates:** an explicit caller may invoke existing task methods;
   one provider's Stop/SessionEnd is not a universal persistence instruction.
   The target #196/#177 boundary captures ordered events, #138 constructs
   episodes, #135/#136 decompose, #137 attaches lineage, #19 admits, #92 gates
   writes. Capture, candidacy, admission and persistence are distinct outcomes.
8. **Dependent context invalidation:** current source-version freshness checks
   can detect that prior evidence no longer matches. Target #169/#167 packets
   must carry their scope and evidence-version dependencies; a changed/missing
   dependency makes the packet stale and eligible for recomputation. Invalidation
   must never write the old packet back as a competing source of truth. The
   invalidation/recompile service itself is not implemented by this contract.

These answers compose existing owners rather than replace their Test Cards.

## Consumer-facing flow

CURRENT:

```text
explicit write request -> canonical gate -> persisted outcome
selected sources -> rebuildable index/evidence -> retrieval -> consuming agent
optional assistance -> free-text view -> consuming agent (no automatic save)
```

TARGET, conditional on the linked child contracts:

```text
run events -> candidate episode/memories -> lineage -> admission -> canonical write
canonical versions -> evidence/state -> Context Compiler -> Working Context -> agent
new durable version -> invalidate dependent views -> recompute within original scope
```

Consumers should use public Python, CLI or discovered MCP operations instead of
editing indexes. The stable semantic intent API is #171; this document does not
invent a `remember` or `context` tool that the installed version lacks. Check
actual write outcomes and MCP errors. A saved source is not proof every derived
projection succeeded; #263 owns truthful post-write receipts and repair.

## Failure boundaries and validation

The proposed architecture rejects:
- persisting every generated plan/answer by default
- treating index loss as source loss or deleting sources to rebuild an index
- treating remembered content as an instruction with automatic authority
- introducing a fourth drawer for transient state
- calling old hashes an immutable revision archive
- using relevance, recency or model confidence as validity/admission authority

`tests/test_ltm_boundary_contract.py` exercises the existing baseline: successful
explicit writes, rejection without a file, retrieval/consolidation without new
canonical writes, source reconstruction after derived-index loss, and stale
version detection. It does not pretend that #169/#167 invalidation, semantic
admission precision, usefulness, duplicate-policy or temporal supersession has
been implemented.

Behavioral variants require their owning frozen corpora, precision/contamination,
missed-memory, history/revision, lineage, utility, invalidation and storage-growth
metrics. This documentation-only boundary candidate claims none of those results.
Benchmark applicability: NOT_APPLICABLE; runtime behavior is unchanged.

## Review and evolution

A maintainer may KEEP or ITERATE this explicit LTM boundary. Acceptance records
a canonical contract decision, not delivery of all children. Runtime defaults,
security/exposure policy, automatic persistence and irreversible retention changes
still need their own validated decisions. The pending child scopes stay visible
in [ROADMAP](ROADMAP.md), and [ADR 0001](adr/0001-core-vs-optional-llm-boundary.md)
continues to govern deterministic core versus assisted/consuming-agent cognition.
