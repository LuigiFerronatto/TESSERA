# TESSERA — Research & Competitive References

> **Purpose:** keep an auditable bibliography for ideas that influence TESSERA. A source appearing here does **not** mean TESSERA implements or validates its claims.

## Source policy

Each reference should be read as one of these categories:

- **Paper** — research claim from the cited publication.
- **Official docs** — product/framework behavior described by its maintainers.
- **Official repository** — implementation/readme/benchmark claim from the project's own repo.
- **TESSERA interpretation** — our architectural reading of that source.
- **TESSERA result** — only something measured in this repository/CI/benchmark.

Do not rewrite a paper claim as a TESSERA result.

When a source influences an experiment, link the corresponding Issue/Test Card.

---

# Core memory research

## QUMem

**Paper:** *QUMem: Personalized Memory for Query-Conditioned User-State Inference in LLM Agents*  
ArXiv: https://arxiv.org/abs/2608.16168  
Published: 2026-08-17

Why it matters to TESSERA:

- motivates independent retrieval of facts, preferences and transferable insights;
- preserves temporal positions and source evidence;
- emphasizes query-conditioned state inference rather than a single flat Top-K query.

TESSERA relationship:

- the exactly-three semantic drawers (`facts`, `preferences`, `insights`) are strongly influenced by this framing;
- TESSERA deliberately does **not** copy QUMem's full multi-agent inference pipeline as a mandatory retrieval path.

Related: #9, #17, #20.

---

## A-MEM

**Paper:** *A-MEM: Agentic Memory for LLM Agents*  
ArXiv: https://arxiv.org/abs/2502.12110  
Published: 2025-02-17

Source claim:

- uses Zettelkasten-inspired structured notes;
- dynamically links memories;
- allows new memories to update contextual representations/attributes of existing memories.

Why it matters:

- useful reference for atomic/interconnected memory and memory evolution;
- also a warning for TESSERA: adaptive evolution should remain auditable and should not silently rewrite historical truth.

Related: #14, #19, #21.

---

## LongMemEval

**Paper:** *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory*  
ArXiv: https://arxiv.org/abs/2410.10813  
Published: 2024-10-14

Core benchmark abilities:

1. information extraction;
2. multi-session reasoning;
3. temporal reasoning;
4. knowledge updates;
5. abstention.

Why it matters:

- provides a shared evaluation target rather than only internal examples;
- explicitly separates design choices across indexing, retrieval and reading.

TESSERA relationship:

- benchmark adapter/ablations are tracked in #18;
- internal sanity metrics are not to be presented as LongMemEval performance.

---

# Recent research signals

## GraphMemix

**Paper:** *GraphMemix: Query-Aware Evidence Forests for Long-Term Multimodal Agent Memory*  
ArXiv: https://arxiv.org/abs/2608.26983  
Published: 2026-08-27

Source claim:

- constructs query-aware candidate graphs/evidence forests;
- separates direct memory utility from relation activation/reliability cost;
- selects evidence under a maximum budget;
- reports a quality/cost Pareto improvement across four multimodal long-term-memory benchmarks.

TESSERA interpretation:

> relation existence is not enough; traversal should be query-conditioned and budgeted.

Derived Test Card:

- #25 Query-aware graph expansion with evidence budget;
- parent #14 Typed Relations / Controlled Expansion.

Not implemented yet.

---

## CaSKG

**Paper:** *Counterfactual-Causal Skill Graphs for Scalable Agent Skill Retrieval*  
ArXiv: https://arxiv.org/abs/2608.25500  
Published: 2026-08-26

Project research note summary:

- candidate relations are generated from multiple signals;
- relation quality is calibrated/validated before graph expansion;
- the central lesson for TESSERA is that unreliable edges can make graph retrieval actively harmful.

TESSERA interpretation:

```text
relation type
≠ relation origin
≠ relation confidence
≠ query relevance
```

Derived Test Card:

- #26 Relation confidence and edge validation.

Important boundary:

- TESSERA should not add `relation_confidence` directly to the default final retrieval score without an explicit ablation.

---

## MemToC

**Paper:** *MemToC: Benchmarking Memory-Tool Conflict Resolution in Large Language Models*  
ArXiv: https://arxiv.org/abs/2608.26295  
Published: 2026-08-26

Source claim:

- 6,504 controlled episodes from 542 factual questions;
- instruction-tuned models often over-follow tools even when the tool is wrong;
- improvements to arbitration can reduce abstention in undesirable ways.

Why it matters:

- conflict is broader than memory-vs-memory;
- tools, memory and current documents can disagree;
- source preference must be evaluated together with correctness and abstention.

Derived Test Cards:

- #27 Evidence / Source Arbitration;
- #20 Evidence Sufficiency / Abstention;
- #32 Source Authority / Scope / Instruction Precedence.

Not implemented yet.

---

## RENDER

**Paper:** *RENDER: Controlling Reader-Facing Evidence in LLM Memory Evaluation*  
ArXiv: https://arxiv.org/abs/2608.23568  
Original submission: 2026-06-05

Source claim:

- reader-facing representation alone can materially change downstream memory/QA scores;
- on LongMemEval, matched-budget resolved packets outperform recency-truncated raw dialogue by large margins;
- formal/ledger-like representations can be difficult for some readers even when they contain the same facts.

TESSERA interpretation:

> retrieval quality and rendering quality are different experimental variables.

Derived Test Cards:

- #28 Structured Evidence rendering ablation;
- #18 LongMemEval adapter/benchmark controls.

---

# Product / framework references

## Mem0

Official docs:

- Overview: https://docs.mem0.ai/platform/overview
- Graph Memory: https://docs.mem0.ai/open-source/features/graph-memory
- New memory algorithm / hybrid retrieval: https://docs.mem0.ai/platform/features/graph-memory

Paper:

- *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory*  
  https://arxiv.org/abs/2504.19413

Relevant documented behaviors:

- extracts salient facts/preferences from messages;
- uses vector storage and optional graph memory;
- current graph-memory docs describe graph retrieval running alongside vector search and returning relations without automatically reordering vector hits;
- current open-source docs describe hybrid retrieval using semantic + BM25 + entity matching.

Use in competitive analysis:

- strong production-oriented reference for extraction + hybrid retrieval + graph augmentation;
- TESSERA should compare representation/provenance/auditability, not only headline QA metrics.

---

## Zep / Graphiti

Official docs:

- Zep overview: https://help.getzep.com/overview
- Graph overview: https://help.getzep.com/graph-overview
- Graphiti overview: https://help.getzep.com/graphiti/getting-started/overview

Paper:

- *Zep: A Temporal Knowledge Graph Architecture for Agent Memory*  
  https://arxiv.org/abs/2501.13956

Relevant documented behaviors:

- builds temporal knowledge/context graphs;
- represents entities, relationships/facts and episodic nodes;
- supports changing facts with temporal invalidation/history;
- Graphiti supports incremental updates and hybrid full-text/semantic/graph search;
- Zep serves prompt-ready context blocks as a managed product.

Use in competitive analysis:

- strongest direct reference for temporal graph memory;
- important comparison for #15/#16 and later graph experiments.

---

## Letta / MemGPT lineage

Official docs:

- Memory blocks: https://docs.letta.com/tutorials/attaching-detaching-blocks/
- Agent archival memory/passages API: https://docs.letta.com/api/resources/agents

Relevant documented behaviors:

- persistent in-context memory blocks can be attached/detached from agents;
- archival memory stores passages searchable outside core context;
- agent state persists enough information to recreate the agent.

Use in competitive analysis:

- important reference for agent-managed memory/context tiers;
- differs from TESSERA's default goal of hiding memory architecture from the agent while preserving evidence.

---

## LangGraph / LangMem

Official docs:

- LangChain/LangGraph long-term memory: https://docs.langchain.com/oss/python/langchain/long-term-memory
- Memory concepts: https://docs.langchain.com/oss/python/concepts/memory
- LangMem conceptual guide: https://langchain-ai.github.io/langmem/concepts/conceptual_guide/

Relevant documented behaviors:

- long-term memories stored as JSON documents organized by namespace/key;
- conceptual split among semantic, episodic and procedural memory;
- LangMem commonly uses LLM-driven extraction/consolidation to update memory state.

Use in competitive analysis:

- useful application-framework baseline;
- TESSERA's three drawers and text-first provenance model are different abstractions from LangGraph's semantic/episodic/procedural taxonomy.

---

## MemOS

Official/open-source references:

- Repository: https://github.com/MemTensor/MemOS
- Intro: https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/memos_intro.md

Relevant documented behaviors:

- positions memory as a first-class operating-system-like resource;
- supports multiple memory types and scheduling/lifecycle management;
- aims to unify storing, retrieval and management behind a memory OS abstraction.

Use in competitive analysis:

- relevant at the product-positioning layer because TESSERA is also an abstraction layer;
- TESSERA is intentionally narrower today: text-first, auditable evidence and deterministic Foundation before broad multimodal/multi-memory orchestration.

---

## MemPalace

Official repository:

- https://github.com/MemPalace/mempalace

Repository claims / documented behavior:

- local-first;
- stores conversation/project content verbatim rather than summarizing/extracting by default;
- default retrieval uses semantic search with a pluggable backend;
- publishes LongMemEval retrieval-recall benchmark artifacts;
- also includes a local temporal entity/relationship graph.

Why it matters:

- provides an important **verbatim-memory baseline** against atomic extraction/representation;
- its published raw retrieval result is a reminder that representation ablations must compare against strong simple baselines.

TESSERA relationship:

- #18 should compare Raw/Verbatim vs Atomic under controlled encoders/readers/token budgets;
- do not compare MemPalace R@5 directly to TESSERA sanity Hit@k.

---

# Reference hygiene rules

When adding a new source:

1. Prefer primary source / official docs / official repository.
2. Record publication/update date when relevant.
3. Write the external claim separately from TESSERA interpretation.
4. Link a Test Card if the source changes the roadmap.
5. Mark implementation status:

```text
implemented
experimental
planned
rejected/deferred
```

6. Never write “TESSERA outperforms X” without a controlled benchmark in this repository.
