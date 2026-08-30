# TESSERA — Project Overview

> **Status:** current project overview. This document describes what TESSERA is, what is implemented today, and which capabilities are still experiments or roadmap items.

## Executive takeaway

TESSERA is an **auditable memory and evidence layer for AI agents**.

Its job is not to answer on behalf of the agent. Its job is to hide the operational complexity of memory — files, normalization, identity, indexing, relations, retrieval and provenance — while returning enough **structured evidence** for the consuming agent to reason safely.

In one sentence:

> **TESSERA abstracts memory architecture away from the agent without abstracting away the evidence.**

That distinction drives the project. A consuming agent should not need to understand frontmatter schemas, cache files, graph construction or source hashes. But it should still be able to inspect **what was retrieved, why it ranked, where it came from, what source version supports it and how it is related to other evidence**.

---

# In plain language

Saving information is easy.

The hard part is answering questions such as:

- Which memory is actually relevant now?
- Is this memory still current?
- Did it come from a human-authored instruction, a learning note or an inferred insight?
- If two memories disagree, should one replace the other or should the disagreement remain visible?
- If a file is renamed, is it still the same source document?
- Can the agent inspect the exact source span that supports a retrieved memory?
- When there is not enough evidence, can the memory layer say so instead of returning arbitrary context?

TESSERA is being built around those questions.

Today the project already solves part of this problem: it can normalize heterogeneous text documents, preserve stable identity, rank memories with multiple explainable signals, select query-relevant evidence and return source provenance through an Evidence Ledger.

The remaining intelligence — temporal state, confidence-aware relations, source arbitration, abstention and adaptive retrieval — is intentionally being developed as **Test Cards**, not assumed features.

---

# Product contract

TESSERA follows five core rules.

## 1. Source text remains the source of truth

Auditable text files are primary sources. Generated indexes, graphs, manifests and ledgers are derived artifacts and should be rebuildable.

TESSERA should not silently rewrite user source files merely to make indexing easier.

## 2. TESSERA returns evidence, not the final answer

Conceptually:

```text
USER / AGENT QUERY
        │
        ▼
     TESSERA
        │
        ├── retrieve
        ├── rank
        ├── trace
        └── structure evidence
        │
        ▼
STRUCTURED EVIDENCE
        │
        ▼
CONSUMING AGENT
        │
        └── reason / decide / answer
```

TESSERA may eventually expose deterministic state/conflict information, but it should not become an opaque answer-generation layer.

## 3. Exactly three semantic drawers

Semantic memories belong to exactly three drawers, inspired by QUMem:

```text
facts
preferences
insights
```

These drawers are not the entire ontology.

Other dimensions are orthogonal metadata/facets:

```text
document_type
kind
scope
harness
temporal validity
authority
confidence
relations
quality
utility
provenance
```

A non-memory document such as `CLAUDE.md`, `AGENTS.md` or `*.SKILL.md` can therefore be indexed with:

```yaml
document_type: harness_instructions
kind: instruction
drawer: null
```

This does **not** create a fourth drawer.

## 4. Important scores remain separate

TESSERA should not collapse every dimension into a single “truth score”.

```text
retrieval relevance
≠ memory confidence
≠ source authority
≠ relation confidence
≠ temporal validity
≠ utility
```

The current retriever has a final ranking score because ranking requires ordering candidates. Future trust, authority and relation policies are being designed as inspectable dimensions rather than hidden additions to that score.

## 5. Basic memory operation should not require a generative LLM

The Foundation is designed to work locally and deterministically for indexing, retrieval, provenance and diagnostics.

Optional generative components may exist for higher-level workflows, but the basic memory path should not depend on a remote model call.

---

# What is implemented today

| Capability | Status | Tracking |
|---|---|---|
| Output contract | Implemented | Issue #7 / PR #1 |
| Explainable multi-signal ranking | Implemented | Issue #8 / PR #2 |
| Query-aware relevant evidence | Implemented | Issue #8 / PR #2 |
| Canonical metadata | Implemented | Issue #9 / PR #3 |
| Document classification | Implemented | Issue #9 / PR #3 |
| Stable memory/knowledge identity | Implemented | Issue #9 / PR #3 |
| Stable source document identity | Implemented | Issue #9 / PR #3 |
| Explicit/local relation parsing | Implemented foundation | Issue #9 / PR #3 |
| CI + deterministic sanity evaluation | Implemented | Issue #10 / PR #4 |
| Evidence Ledger + provenance | Implemented | Issue #11 / PR #6 |
| Engine/CLI/MCP contract parity | Planned Foundation hardening | Issue #68 |
| Incremental/idempotent indexing | Planned Foundation experiment | Issue #12 |
| Plain-text ingestion beyond Markdown | Planned experiment | Issue #69 |
| Structural segmentation | Planned experiment | Issue #70 |
| Metadata Doctor | Planned | Issue #13 |
| Temporal state / state keys | Planned experiment | Issue #15 |
| Evidence Arbitration | Planned experiment | Issues #16 / #27 |
| Query-aware graph expansion | Planned experiment | Issues #14 / #25 |
| Relation confidence | Planned experiment | Issue #26 |
| Four-state evidence sufficiency | Planned experiment | Issue #20 |
| Harness adapters / instruction resolver | Planned experiment | Issues #71 / #72 / #32 |
| LongMemEval adapters/ablations | Planned benchmark | Issue #18 |
| Rendering ablations | Planned benchmark experiment | Issue #28 |

The project roadmap is maintained in [`ROADMAP.md`](ROADMAP.md) and the corresponding GitHub Test Cards.

---

# Current Foundation pipeline

```text
TEXT FILES
   │
   ▼
DISCOVER
   │
   ▼
PARSE + NORMALIZE
   ├── frontmatter / no-frontmatter
   ├── document classification
   ├── semantic drawer when applicable
   ├── scope
   └── metadata origin
   │
   ▼
IDENTITY
   ├── stable knowledge/memory identity
   ├── stable source document identity
   ├── current path
   └── content/document hashes
   │
   ▼
CONNECT
   ├── explicit links
   ├── local Markdown links
   └── graph representation
   │
   ▼
INDEX
   ├── graph
   ├── lexical index
   └── derived cache
   │
   ▼
RETRIEVE
   ├── candidate generation
   ├── explainable multi-signal ranking
   └── query-aware evidence selection
   │
   ▼
TRACE
   ├── evidence_id
   ├── source document
   ├── version hashes
   └── source span when uniquely provable
   │
   ▼
STRUCTURED RESULT
   │
   ▼
AGENT
```

This is the **implemented Foundation**. Query-aware graph traversal, temporal-state reconstruction, evidence arbitration and sufficiency classification belong to future experimental layers and should not be read as current capabilities.

---

# Retrieval today

TESSERA currently uses multiple explainable signals rather than a single PageRank or vector similarity score.

The implemented ranking includes signals such as:

- TF-IDF lexical similarity;
- direct token overlap;
- title/ID relevance;
- metadata relevance;
- normalized relation/PageRank signal;
- deterministic type/intent boosts;
- optional recency behavior, disabled by default in the current Foundation.

The purpose of this design is not to claim semantic understanding. It is to make retrieval behavior observable enough to benchmark and improve.

The deterministic sanity suite deliberately contains both direct and colloquial purpose queries. A paraphrase may still rank the intended memory below another relevant candidate because the current candidate/ranking path remains strongly lexical. We keep that behavior visible instead of adding query-specific exceptions.

The sanity suite is a **regression baseline**, not a competitive benchmark.

---

# Evidence and provenance

A retrieved memory is not useful merely because it has a high score.

TESSERA also attempts to identify the query-relevant text span and trace it back to its source.

Conceptually:

```text
retrieved memory
      │
      ├── relevant_evidence
      │
      └── evidence record
             │
             ├── evidence_id
             ├── memory_id
             ├── source_document_id
             ├── source_path
             ├── document_hash
             ├── content_hash
             └── source_span
```

This Evidence Ledger is a **derived, rebuildable provenance substrate**.

Future `authority`, `confidence`, temporal status and arbitration decisions should operate **on top of** provenance instead of mutating the historical evidence record into a query-time decision object.

---

# Why stable identity matters

TESSERA separates four concepts that are often accidentally treated as one:

```text
identity.id
→ persistent identity of the knowledge/memory object

source.document_id
→ persistent identity of the source document

source.path
→ current physical location

content/document hashes
→ version fingerprints
```

Therefore a file can move without becoming a new document, and a document can change content without losing its identity.

That separation is what makes reliable provenance, incremental indexing and later temporal reasoning possible.

---

# Where the project is going

The roadmap is intentionally experimental.

```text
PUBLIC FOUNDATION
agnostic docs + contract hygiene
        │
        ▼
FOUNDATION
identity + provenance + deterministic incremental indexing
        │
        ▼
MEASURE
LongMemEval + renderer controls
        │
        ▼
RELATIONS
query-aware graph expansion + relation reliability
        │
        ▼
TEMPORAL / INSTRUCTIONS
validity + state keys + instruction applicability/precedence
        │
        ▼
ARBITRATION
source authority + conflict representation
        │
        ▼
SUFFICIENCY
sufficient / insufficient / conflicting / ambiguous
        │
        ▼
ADAPTIVE MEMORY
query routing + write gating + experience learning
```

Each major capability should pass through a Test Card and may end in:

```text
KEEP
ITERATE
REVERT
DROP
DEFER
```

A technically correct implementation that does not improve quality, cost, auditability or agent behavior is allowed to be dropped.

---

# What TESSERA is not

TESSERA is not currently:

- a general-purpose vector database;
- a final-answer chatbot;
- an always-on autonomous self-modification system;
- a mandatory LLM-based memory extractor;
- a code knowledge graph;
- a claim that graph memory always outperforms flat retrieval;
- a claim that atomic memories always outperform verbatim history.

Those distinctions matter because several roadmap items exist specifically to **test** those assumptions.

---

# How development decisions are made

```text
Issue
  ↓
Test Card
  ↓
PR
  ↓
CI + benchmark/output evidence
  ↓
Learnings
  ↓
Decision
```

Every PR should explain the work at three levels:

1. **Executive takeaway** — why this matters;
2. **Em linguagem simples** — what changes in practical terms;
3. **Technical implementation** — contracts, algorithms and code behavior.

Research papers and competitor behavior are inputs to Test Cards, not automatic implementation instructions.

---

# Documentation map

- [`ROADMAP.md`](ROADMAP.md) — experimental roadmap and Test Card lifecycle;
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — deeper architecture notes;
- [`FEATURES.md`](FEATURES.md) — implemented capability catalog;
- [`QUERY_EXAMPLES.md`](QUERY_EXAMPLES.md) — practical retrieval examples;
- [`CONCEPTS.md`](CONCEPTS.md) — terminology and contracts;
- [`research/REFERENCES.md`](research/REFERENCES.md) — source bibliography;
- [`research/PAPER_NOTES.md`](research/PAPER_NOTES.md) — paper → insight → Test Card trace;
- [`research/COMPETITIVE_LANDSCAPE.md`](research/COMPETITIVE_LANDSCAPE.md) — version-aware comparison;
- [`research/DECISION_TRACE.md`](research/DECISION_TRACE.md) — external idea → TESSERA decision history.

---

## Short version

> **The goal is not to make the memory system think more. The goal is to make memory complexity disappear for the agent while keeping the evidence visible enough to inspect, navigate and challenge.**
