# TESSERA — Research & Competitive References

> **Purpose:** auditable bibliography for ideas that influence TESSERA.
>
> **Last primary-source verification:** 2026-08-30.
>
> A source appearing here does **not** mean TESSERA implements or validates its claims.

## Source policy

Keep five layers separate:

```text
external source
→ what the paper/product actually says

TESSERA interpretation
→ what we think the signal means for our architecture

Test Card
→ how we plan to measure that interpretation

implementation
→ what code actually exists

TESSERA result
→ what this repository/CI/benchmark actually measured
```

Never rewrite a paper claim as a TESSERA result. Prefer primary/official sources. Revalidate fast-moving product docs before using them externally.

---

# Core memory research

## QUMem

**Paper:** *QUMem: Personalized Memory for Query-Conditioned User-State Inference in LLM Agents*  
ArXiv: https://arxiv.org/abs/2608.16168  
Published: 2026-08-17

Relevant signal:
- independent handling of facts, preferences and transferable insights;
- query-conditioned user-state inference;
- temporal/source evidence.

TESSERA interpretation:
- exactly three semantic drawers: `facts`, `preferences`, `insights`;
- do not make QUMem's full inference pipeline mandatory for basic retrieval.

Related: #9, #17, #20.

---

## A-MEM

**Paper:** *A-MEM: Agentic Memory for LLM Agents*  
ArXiv: https://arxiv.org/abs/2502.12110  
Published: 2025-02-17

Relevant signal:
- atomic structured notes;
- Zettelkasten-inspired links;
- adaptive memory evolution.

TESSERA interpretation:
- atomic/interconnected memory is useful;
- automatic memory evolution must remain auditable and must not silently rewrite historical evidence.

Related: #14, #19, #21.

---

## LongMemEval

**Paper:** *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory*  
ArXiv: https://arxiv.org/abs/2410.10813  
Published: 2024-10-14

Core abilities:
1. Information Extraction
2. Multi-Session Reasoning
3. Knowledge Updates
4. Temporal Reasoning
5. Abstention

TESSERA use:
- external benchmark backbone in #18;
- internal sanity Hit@k/MRR must never be presented as LongMemEval performance.

---

## LongMemEval V2

Repository / project source:
- https://github.com/xiaowu0162/LongMemEval-V2

TESSERA use:
- later-stage evaluation once Foundation/ablation adapter is reliable;
- not part of basic CI.

---

# Additional long-term memory research

## LiveMem

**Paper:** *LiveMem: Maintaining Memory State Continuity in Long-Running LLM Inference*  
ArXiv: https://arxiv.org/abs/2608.02515  
Published: 2026-08-03

Source signal:
- treats state continuity under context turnover as distinct from retrieving selected history;
- maintains a fixed-capacity recurrent memory state while the active KV context remains bounded;
- combines context turnover, memory-oriented post-training and state-aware serving.

TESSERA interpretation:
- distinguishes intrinsic model-state continuity from TESSERA's external, text-first evidence layer;
- motivates lifecycle tests in which supporting evidence leaves the active context but must remain recoverable;
- does not justify coupling TESSERA to one model architecture or serving stack.

Status: reference for future continuity evaluation; not an implemented intrinsic-memory capability.

---

## FinPerMA

**Paper:** *FinPerMA: A Theory-Informed, Event-Grounded Personalized-Memory Benchmark for LLM Agents*  
ArXiv: https://arxiv.org/abs/2608.04095  
Published: 2026-08-04

Source signal:
- event-grounded evaluation over frozen longitudinal investor trajectories;
- a Post-Shock checkpoint tests whether a material event updates the persistent user model;
- 2,994 questions from 276 personas;
- reported results show factual summaries can preserve details while losing preference signals needed after shocks.

TESSERA interpretation:
- personalized memory must be evaluated on state transitions, not only fact recall;
- preference updates need temporal evidence, explicit supersession/conflict handling and before/after checkpoints;
- the financial domain is a benchmark setting, not a claim that TESSERA is a financial-advice system.

Status: candidate benchmark pattern for temporal preference-update tests; no FinPerMA adapter implemented.

---

## Persistent Memory and User Profiles

**Paper:** *Enabling Personalized Long-term Interactions in LLM-based Agents through Persistent Memory and User Profiles*  
ArXiv: https://arxiv.org/abs/2510.07925  
Published: 2025-10-09

Source signal:
- derives technical requirements from a unified personalization definition;
- combines persistent memory, evolving user profiles, multi-source retrieval, dynamic coordination and self-validation;
- evaluates the framework on three public datasets and a five-day pilot user study.

TESSERA interpretation:
- a user profile is a derived, evolving view over evidence rather than a replacement for source memories;
- profile updates should preserve provenance, validation state and the evidence that caused the change;
- response personalization remains the consuming agent's responsibility.

Status: architecture reference for future user-state/profile synthesis; not implemented as a profile engine.

---

## State Contamination

**Paper:** *State Contamination in Memory-Augmented LLM Agents*  
ArXiv: https://arxiv.org/abs/2605.16746  
Published: 2026-05-16

Source signal:
- persistent transcripts, summaries, retrieved context and memory buffers create a state-control safety surface;
- unsafe influence can survive compression in a less visibly toxic summary, described as memory laundering;
- sanitizing state before summarization is reported as more effective than cleaning only the completed summary.

TESSERA interpretation:
- provenance alone is insufficient if contaminated content is normalized into trusted persistent state;
- ingestion, derivation and retrieval need separate safety assessments and lineage;
- derived summaries must not silently gain more authority than their source evidence.

Status: safety reference for future contamination and derivation-lineage Test Cards; no complete sanitization policy implemented.

---

## MemORAI

**Paper:** *MemORAI: Memory Organization and Retrieval via Adaptive Graph Intelligence for LLM Conversational Agents*  
ACL Anthology: https://aclanthology.org/2026.findings-acl.1408/  
ArXiv: https://arxiv.org/abs/2605.01386  
Published: Findings of ACL 2026

Source signal:
- selective memory filtering with dual-layer compression;
- provenance-enriched multi-relational graphs with turn-level factual origins;
- query-adaptive subgraph retrieval using dynamically weighted PageRank;
- evaluation on LOCOMO and LongMemEval.

TESSERA interpretation:
- selective storage, evidence provenance and query-conditioned traversal are separable controls;
- turn-level origin supports the Evidence Ledger direction;
- adaptive graph weighting should be compared against lexical, no-expansion and bounded-expansion baselines before adoption.

Status: research reference for #25/#26 and future storage-gating experiments; adaptive PageRank is not implemented.

---

# Recent research signals mapped to Test Cards

## GraphMemix

**Paper:** *GraphMemix: Query-Aware Evidence Forests for Long-Term Multimodal Agent Memory*  
ArXiv: https://arxiv.org/abs/2608.26983  
Published: 2026-08-27

Source signal:
```text
query-aware candidate graph
+ direct evidence utility
+ relation activation/reliability cost
+ maximum evidence budget
+ forest optimization
```

Paper reports a new quality/lifecycle-cost Pareto frontier across four long-term multimodal memory benchmarks.

TESSERA interpretation:
> relation existence does not imply that the relation should be traversed for the current query.

Derived Test Card:
- #25 Query-aware graph expansion / Evidence Budget
- parent #14 Typed Relations / Controlled Expansion

Status: planned experiment, not implemented capability.

---

## CaSKG

**Paper:** *CaSKG: Counterfactual-Causal Skill Graphs for Scalable Agent Skill Retrieval*  
ArXiv: https://arxiv.org/abs/2608.25500  
Published: 2026-08-26  
Code: https://github.com/ZhiyuanLi218/Caskg

Source signal:
- high-recall directed candidate graph;
- semantic, lexical, I/O and structural signals;
- counterfactual remove/substitute/reorder probes;
- calibrated weighted graph before task-conditioned expansion.

Reported comparison against Graph-of-Skills:
- ScienceWorld six-model macro-average: 72.62 → 80.50;
- ALFWorld success: 80.01% → 86.79%.

TESSERA interpretation:
```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

Derived Test Card:
- #26 Relation Confidence / Edge Validation

Important boundary:
- relation confidence must not silently become another default `FINAL_SCORE` weight.

---

## MemToC

**Paper:** *MemToC: Benchmarking Memory-Tool Conflict Resolution in Large Language Models*  
ArXiv: https://arxiv.org/abs/2608.26295  
Published: 2026-08-26

Source signal:
- 6,504 controlled episodes from 542 factual questions;
- independently controlled correctness of model-memory answer and tool return;
- strong tool-following bias even when tools are wrong;
- many attempted improvements reduce abstention in undesirable ways.

Reported observations include:
- instruction-tuned models retain a verified-correct answer against a wrong tool only 6.5–17.1% of eligible cases;
- when both sources are wrong, tool output is repeated in 78.4–86.0% of cases.

TESSERA interpretation:
```text
memory-vs-memory conflict
≠
source arbitration across memory / tool / document
```

Derived Test Cards:
- #27 Evidence / Source Arbitration
- #20 four-state Evidence Sufficiency / Abstention
- #32 Source Authority / Scope / Instruction Precedence

---

## RENDER

**Paper:** *RENDER: Controlling Reader-Facing Evidence in LLM Memory Evaluation*  
ArXiv: https://arxiv.org/abs/2608.23568  
Original submission: 2026-06-05

Source signal:
- reader-facing artifact is itself an evaluation variable;
- same underlying information can produce materially different downstream memory/QA results;
- reported matched-budget resolved packets outperform recency-truncated raw dialogue by 42.4–72.6 points depending on model/setup.

TESSERA interpretation:
```text
retrieval quality
≠ rendering quality
```

Derived Test Cards:
- #28 RAW vs EVIDENCE vs STRUCTURED renderer ablation
- parent #18 LongMemEval controls

---

# Product / framework references

## Mem0

Primary docs verified:
- Graph Memory: https://docs.mem0.ai/open-source/features/graph-memory
- OSS v2 → v3 migration: https://docs.mem0.ai/migration/oss-v2-to-v3
- Long-term memory CLI: https://docs.mem0.ai/platform/cli
- Paper: https://arxiv.org/abs/2504.19413

Current-source caution:

Mem0 documentation reflects more than one architectural generation. A Graph Memory page describes entity/relationship extraction into an external graph backend beside vector retrieval. The newer OSS migration guide says external graph-store support was removed from the newer open-source algorithm and replaced with built-in entity linking, alongside semantic + BM25 + entity hybrid retrieval.

Therefore do not summarize Mem0 as simply:

```text
"vector + graph"
```

without specifying version/product path.

Relevant TESSERA comparison:
- extracted memory vs source-backed atomic representation;
- hybrid retrieval quality;
- scope/user/agent boundaries;
- provenance and source preservation;
- latency/context cost.

---

## Zep / Graphiti

Primary docs verified:
- Zep v3: https://help.getzep.com/v3/overview
- Graph overview: https://help.getzep.com/graph-overview
- Graphiti overview: https://help.getzep.com/graphiti/getting-started/overview
- Graphiti welcome: https://help.getzep.com/graphiti/getting-started/welcome
- Zep vs Graphiti: https://help.getzep.com/zep-vs-graphiti
- Paper: https://arxiv.org/abs/2501.13956

Documented signals:
- Graphiti = open-source temporal Context Graph framework;
- entity/relationship/fact graph;
- episodic ingestion/provenance;
- bi-temporal validity/fact invalidation;
- incremental updates;
- time/full-text/semantic/graph hybrid retrieval;
- Zep = managed enterprise-scale Context Lake on top of Context Graph infrastructure.

TESSERA comparison:
- Graphiti makes temporal graph structure central;
- TESSERA currently makes source documents + canonical identity + Evidence Ledger the stable substrate and treats advanced graph behavior as an ablation.

Related: #12, #14, #15, #16, #25, #26, #27.

---

## Letta / MemGPT lineage

Primary docs verified:
- https://docs.letta.com/

Current positioning:
- platform for stateful agents;
- persistent memory/state is tightly integrated with the agent runtime/harness.

TESSERA comparison:
```text
Letta
→ memory/state integrated with agent runtime

TESSERA
→ memory mechanics abstracted behind a layer
→ evidence/provenance remains visible
```

Future evaluation should test whether hiding memory mechanics reduces failure modes or removes useful agent control.

---

## LangGraph / LangChain memory patterns

Primary docs verified:
- https://docs.langchain.com/oss/python/langchain/long-term-memory
- https://docs.langchain.com/oss/python/concepts/memory

Documented signals:
- long-term memory persists across threads;
- LangGraph stores JSON documents by namespace/key;
- conceptual taxonomy includes semantic, episodic and procedural memory;
- write timing can be hot-path or background.

TESSERA distinction:
```text
facts / preferences / insights
≠
semantic / episodic / procedural
```

TESSERA also keeps harness instructions as instruction/document semantics with `drawer: null` rather than treating them as another semantic drawer.

---

## MemOS

Primary/open-source sources verified:
- Repository: https://github.com/MemTensor/MemOS
- Intro: https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/memos_intro.md
- Core concepts: https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/core_concepts.md

Documented signals:
- Memory Operating System positioning;
- memory as a first-class orchestrated resource;
- MOS orchestration layer;
- MemCubes;
- multiple memory forms/types;
- lifecycle/scheduling/governance abstractions.

TESSERA distinction:
- intentionally narrower current Foundation;
- text-first source truth, stable identity, provenance and structured evidence before broader memory-OS orchestration.

---

## MemPalace

**Verified official public repository:**
- https://github.com/bassemhalawani/memorypalace

Repository warning states the official sources are that repository, the PyPI package, and `mempalaceofficial.com` documentation.

Documented signals:
- local-first;
- verbatim storage rather than summarize/extract/paraphrase by default;
- pluggable retrieval backend;
- structured palace organization;
- local temporal entity/relationship graph;
- reproducible benchmark artifacts.

Repository reports:
- 96.6% raw R@5 on LongMemEval for its stated zero-API-call retrieval path.

TESSERA use:
- important raw/verbatim baseline for #18;
- do not compare this R@5 directly to TESSERA's internal four-query sanity Hit@5;
- fair comparison requires same source histories, encoder controls where relevant, session normalization, token budgets and same reader/rendering policy.

---

# Research-to-roadmap rule

When a source changes architecture thinking:

```text
SOURCE
  ↓
SOURCE CLAIM
  ↓
TESSERA INTERPRETATION
  ↓
ISSUE / TEST CARD
  ↓
CONTROLLED EXPERIMENT
  ↓
TESSERA EVIDENCE
  ↓
KEEP | ITERATE | REVERT | DROP | DEFER
```

The research bibliography should make that path auditable rather than functioning as a list of fashionable papers.

---

# Reference hygiene checklist

When adding/updating a source:

1. Prefer the paper, official docs or official repository.
2. Record publication/update/verification date when useful.
3. Separate source claim from TESSERA interpretation.
4. Link the corresponding Test Card.
5. Mark implementation status: `implemented`, `experimental`, `planned`, `dropped/deferred`.
6. Revalidate fast-moving product behavior before external publication.
7. Never write “TESSERA outperforms X” without a controlled TESSERA benchmark result.
