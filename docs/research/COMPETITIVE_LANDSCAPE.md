# TESSERA — Competitive Landscape

> **Scope:** compare memory-system design choices, not marketing claims. Products/frameworks and research architectures are listed separately.

## Executive takeaway

The agent-memory landscape is converging around several recurring ideas:

- persistent memory outside the model context;
- extraction or structured representation;
- vector/hybrid retrieval;
- graph-based relations;
- temporal state;
- prompt/context assembly;
- lifecycle/write management.

TESSERA's current differentiation is not “we have a graph” or “we store memories”. It is the combination of:

```text
text-first source of truth
+ stable memory/source identity
+ explicit provenance/evidence ledger
+ explainable multi-signal retrieval
+ query-specific evidence
+ strict separation of relevance / confidence / authority / utility
+ experimental governance before adding intelligence
```

Several important differentiators are still **hypotheses**, not proven advantages. LongMemEval/ablations (#18) must determine whether they actually improve downstream outcomes.

---

# Comparison dimensions

We compare systems using these questions:

| Dimension | Question |
|---|---|
| Representation | What is stored: raw text, extracted facts, blocks, graph facts, atomic notes? |
| Source preservation | Is original source/verbatim history retained or is extracted memory primary? |
| Retrieval | Vector, keyword, hybrid, graph, agentic search? |
| Graph | Are relations first-class? How do they affect retrieval? |
| Temporal | Can facts/relations change and preserve history? |
| Provenance | Can a result trace back to source/version/span? |
| Conflict/update | How are old/new/conflicting facts handled? |
| Scope/governance | How are user/agent/project boundaries represented? |
| Rendering/context | What artifact is handed to the consuming model? |
| Agent responsibility | Does the agent manage memory explicitly or is memory hidden behind a layer? |
| Local/offline path | Can core operation work without a generative API call? |
| Benchmark posture | What evaluation does the project publish/use? |

---

# Product / framework systems

## Mem0

Sources:

- https://docs.mem0.ai/platform/overview
- https://docs.mem0.ai/open-source/features/graph-memory
- https://arxiv.org/abs/2504.19413

### How it approaches memory

Mem0 is a production-oriented memory layer that extracts salient information from conversations and stores/retrieves memories through vector/hybrid infrastructure, with optional graph memory.

Current graph-memory documentation describes entity/relationship extraction alongside embeddings. Vector search remains the primary result ordering, while graph context is returned as related information; current open-source material also describes semantic + BM25 + entity hybrid retrieval.

### What is especially relevant

- pragmatic extraction pipeline;
- hybrid retrieval;
- entity-scoped memory (`user_id`, `agent_id`, etc.);
- graph augmentation without necessarily letting graph signals replace vector ranking;
- strong emphasis on production latency/cost.

### TESSERA difference / hypothesis

TESSERA currently emphasizes **source-backed auditability** more strongly: source document identity, version hashes, spans and Evidence Ledger are explicit Foundation contracts.

TESSERA also keeps its base path generative-LLM optional, whereas extraction-centric workflows commonly use LLM extraction.

What remains unproven:

- whether TESSERA atomic/source-backed representation beats Mem0-style extraction on downstream benchmarks;
- whether TESSERA relation/temporal plans outperform Mem0 graph memory.

Benchmark requirement: #18.

---

## Zep / Graphiti

Sources:

- https://help.getzep.com/overview
- https://help.getzep.com/graphiti/getting-started/overview
- https://arxiv.org/abs/2501.13956

### How it approaches memory

Zep builds temporal Context Graphs from conversations, documents and business data. Graphiti is its open-source temporal knowledge-graph framework.

Graphiti documents:

- episodic ingestion;
- entities + fact/relationship edges;
- temporal fact lifecycles/invalidation;
- incremental graph updates;
- hybrid time/full-text/semantic/graph search.

Zep adds a managed Context Lake and serves prompt-ready context blocks.

### What is especially relevant

This is one of the strongest references for:

```text
temporal graph
changing facts
historical validity
incremental graph updates
hybrid retrieval
```

### TESSERA difference / hypothesis

TESSERA starts from **auditable source documents + atomic knowledge records + evidence spans**, and treats graph intelligence as an experiment layered on top.

Zep/Graphiti starts more directly from temporal graph construction as the central memory representation.

The key comparison later should be:

```text
Graphiti-style temporal graph
vs
TESSERA source-backed evidence graph / atomic state
```

on temporal updates, provenance correctness, retrieval quality and context cost.

Related TESSERA cards: #14, #15, #16, #25, #26.

---

## Letta / MemGPT lineage

Sources:

- https://docs.letta.com/tutorials/attaching-detaching-blocks/
- https://docs.letta.com/api/resources/agents

### How it approaches memory

Letta exposes persistent **memory blocks** that occupy reserved sections of an agent's context and archival/passages memory searchable outside core context.

Memory can be attached/detached across agents, and persisted agent state is a core abstraction.

### What is especially relevant

- explicit separation between always-visible core memory and searchable archival memory;
- memory is closely integrated with agent state;
- dynamic memory attachment supports sharing/context switching.

### TESSERA difference / hypothesis

TESSERA's default product contract is almost the inverse at the agent interface:

> hide memory architecture from the agent, but expose evidence/provenance.

A consuming TESSERA agent should not need to manually manage “memory blocks” to benefit from retrieval.

That does not mean Letta's approach is inferior. It represents a different control model:

```text
Letta: agent/runtime-visible memory management
TESSERA: memory-layer abstraction + evidence-visible output
```

Future benchmark/control-flow tests should measure whether hiding architecture improves reliability or simply reduces useful agent control.

---

## LangGraph / LangMem

Sources:

- https://docs.langchain.com/oss/python/langchain/long-term-memory
- https://docs.langchain.com/oss/python/concepts/memory
- https://langchain-ai.github.io/langmem/concepts/conceptual_guide/

### How it approaches memory

LangGraph stores long-term memories as JSON documents in namespace/key stores and leaves significant memory-design choices to application developers.

Its conceptual material distinguishes:

```text
semantic memory
episodic memory
procedural memory
```

LangMem provides LLM-assisted extraction/consolidation patterns for memory state.

### What is especially relevant

- flexible application-level memory storage;
- clear memory-type taxonomy;
- hot-path vs background memory writes;
- composability with agent workflows.

### TESSERA difference / hypothesis

TESSERA's three semantic drawers are **not** the same taxonomy:

```text
TESSERA facts/preferences/insights
≠
semantic/episodic/procedural memory categories
```

TESSERA also treats harness instructions as document/instruction semantics (`drawer: null`) rather than forcing them into a procedural semantic drawer.

LangGraph is a broad application/runtime framework; TESSERA is intended to be a narrower memory/evidence subsystem that can plug into different runtimes.

---

## MemOS

Sources:

- https://github.com/MemTensor/MemOS
- https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/memos_intro.md

### How it approaches memory

MemOS explicitly positions memory as an operating-system-like first-class resource with unified management, scheduling and multiple memory types.

Its project documentation describes support spanning textual/tree/preference/skill and other memory forms, plus lifecycle/scheduling abstractions.

### What is especially relevant

MemOS is a useful reference for the **memory operating layer** positioning:

```text
model/agent
↕
memory operating layer
↕
stores / knowledge / lifecycle
```

### TESSERA difference / hypothesis

TESSERA is intentionally much narrower today:

```text
text-first
local/deterministic Foundation
source-backed provenance
explicit evidence contract
```

rather than trying to orchestrate many memory modalities/types immediately.

The strategic question is whether this narrower auditable substrate produces a better foundation before expanding into broader Memory-OS behavior.

---

## MemPalace

Source:

- https://github.com/MemPalace/mempalace

### How it approaches memory

MemPalace describes itself as local-first and keeps conversation/project content **verbatim** rather than extracting/summarizing it by default. It uses pluggable semantic retrieval and publishes LongMemEval retrieval-recall artifacts. It also documents a local temporal entity/relationship graph.

### What is especially relevant

MemPalace is a critical baseline because it challenges the assumption that “more structured extraction = better memory”.

Its published benchmark progression argues that raw verbatim content with strong retrieval can retain evidence that extraction may discard.

### TESSERA difference / hypothesis

TESSERA uses atomic/canonical representations but deliberately preserves original source/body and provenance.

The fair test is not:

```text
TESSERA Top-5 atomic IDs
vs
MemPalace Top-5 whole sessions
```

Instead #18 should evaluate:

```text
same source histories
same encoder where isolating representation
session-normalized recall
token-budget evidence recall
same downstream reader
```

This is one of the most important competitive controls for TESSERA.

---

# Research architectures / benchmarks

These are not direct products, but they shape the design space.

## QUMem

Focus:

```text
variable episodes
facts/preferences/insights
query-conditioned user state
temporal/source evidence
```

TESSERA takes the three-drawer semantic split but aims for a more agent/runtime-agnostic evidence layer.

---

## A-MEM

Focus:

```text
atomic structured notes
Zettelkasten links
memory evolution
agentic updates
```

TESSERA shares atomic/interconnected-memory interests but is more conservative about automatic rewriting/evolution.

---

## GraphMemix

Focus:

```text
query-aware evidence graph/forest
relation activation reliability/cost
evidence budget
```

TESSERA response:

- #25 turns this into controlled 1-hop/budget ablations instead of immediately replacing retrieval.

---

## CaSKG

Focus:

```text
edge reliability / validation before expansion
```

TESSERA response:

- #26 separates relation type, origin, confidence, evidence/validation and query relevance.

---

## MemToC

Focus:

```text
memory vs tool conflict
source correctness
abstention side effects
```

TESSERA response:

- #27 Evidence Arbitration;
- #20 four-state evidence status;
- #32 authority/scope precedence.

---

## RENDER

Focus:

```text
reader-facing evidence representation as an evaluation variable
```

TESSERA response:

- #28 RAW vs EVIDENCE vs STRUCTURED rendering under fixed retrieval/reader controls.

---

# Capability matrix

Legend:

```text
✓ documented/core capability
~ partial/optional/architecture-specific
? future/unproven for TESSERA
— not a central documented focus
```

| System | Raw/source preservation | Extracted/structured memory | Graph | Temporal | Explicit provenance/span | Query-aware evidence | Conflict/arbitration | Local basic path |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **TESSERA (current)** | ✓ | ✓ | ~ | — | ✓ | ✓ | — | ✓ |
| Mem0 | ~ | ✓ | ✓ optional | ~ timestamps/graph context | ~ | ~ | ~ memory updates | ~ configurable |
| Zep/Graphiti | ✓ episodic source | ✓ graph facts/entities | ✓ | ✓ | ✓ episodic provenance | ✓ context/search | ✓ fact invalidation | Graphiti self-hostable |
| Letta | ✓ messages/archive | ✓ memory blocks | — | ~ timestamps/state | ~ | ~ archival search | ~ agent-managed | ✓ self-host options |
| LangGraph/LangMem | app-defined | app-defined/✓ | app-defined | app-defined | app-defined | app-defined | app-defined | ✓ possible |
| MemOS | ✓/multi-source | ✓ multi-type | ✓ supported | ~ lifecycle/versioning | ~ | ✓ retrieval layer | ~ lifecycle | ✓ open source |
| MemPalace | ✓ strong/verbatim | ~ structured palace metadata | ✓ temporal graph | ✓ graph validity | ✓ source retained | ~ semantic/hybrid search | ~ invalidation | ✓ |

**Important:** this table summarizes documented architectural emphasis, not benchmark superiority. Several cells depend on configuration/version and should be revalidated before publication outside the project.

---

# Where TESSERA currently appears differentiated

## 1. Provenance as a Foundation feature

TESSERA makes source document identity, source version hashes and evidence span first-class before implementing advanced temporal/arbitration behavior.

## 2. Separation of ranking from trust

Roadmap invariant:

```text
relevance
≠ confidence
≠ authority
≠ relation confidence
≠ temporal validity
≠ utility
```

Several systems may expose equivalent concepts, but TESSERA treats avoiding a unified magic score as an explicit architectural constraint.

## 3. Non-memory text as first-class knowledge without extra drawers

Harness/project/reference documents can be indexed without pretending they are user preferences or factual memories.

## 4. Experimental graph posture

TESSERA does not assume graph expansion is beneficial. #14/#25/#26 require ablations against no-graph/simple retrieval baselines.

## 5. Evidence interface as a benchmark target

RENDER-inspired #28 explicitly asks whether the structured evidence interface itself improves downstream behavior.

---

# Where competitors are ahead / TESSERA is not complete

A useful competitive document must also state this clearly.

## Temporal state

Zep/Graphiti already has a mature documented temporal graph/fact invalidation model. TESSERA temporal state is still #15/#16.

## Production scale / managed infrastructure

Mem0 and Zep provide managed production platforms, governance and scalable services. TESSERA is currently an early local/open Foundation.

## Mature agent-context orchestration

Letta has a mature agent-state/memory-block model; LangGraph has broad workflow/store integration; MemOS targets a broader OS abstraction. TESSERA is intentionally narrower today.

## External benchmark evidence

MemPalace, Mem0, Zep and multiple research systems publish benchmark results. TESSERA does not yet have a clean LongMemEval result; #18 is required before making competitive quality claims.

---

# Competitive hypotheses to test

Instead of a marketing comparison, TESSERA should turn differences into experiments:

1. **Raw vs Atomic representation** — does atomic/source-backed representation improve evidence density without losing recall? (#18)
2. **No graph vs graph** — when do relations improve distributed evidence retrieval? (#14/#25)
3. **Edge confidence** — does confidence-aware expansion reduce harmful context? (#26)
4. **Temporal graph vs state-key approach** — how much temporal complexity is necessary? (#15/#16)
5. **Evidence rendering** — does Structured Evidence improve reader outcomes at the same retrieval set? (#28)
6. **Arbitration** — does explicit conflict representation improve source choice/abstention? (#27/#20)
7. **Memory architecture visibility** — should the agent manage memory explicitly or receive an abstracted evidence interface? future evaluation.

---

# Positioning draft

A defensible current positioning is:

> **TESSERA is a text-first, agent-agnostic memory and evidence layer focused on stable identity, provenance, explainable retrieval and auditable evolution. It keeps source evidence visible while hiding storage/indexing complexity from the consuming agent.**

A stronger future claim such as “better long-term memory than Mem0/Zep/MemPalace” is **not justified** until #18 produces controlled results.
