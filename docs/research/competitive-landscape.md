# TESSERA — Competitive Landscape

> **Scope:** compare memory-system design choices, not marketing claims.
>
> **Primary-source verification date:** 2026-08-30.
>
> Product/framework behavior changes quickly. Revalidate primary sources before publishing this document outside the project.

## Executive takeaway

The agent-memory ecosystem is not converging on one winning architecture. It contains several control models:

```text
extracted memories + hybrid search           Mem0
managed/open temporal context graphs         Zep / Graphiti
agent-visible state / memory management      Letta
application-defined stores + memory patterns LangGraph / LangMem
memory operating-system abstraction          MemOS
verbatim local-first recall                   MemPalace
```

TESSERA's current thesis is different:

```text
text-first source of truth
+ stable memory/source identity
+ source-version-aware provenance
+ explainable retrieval
+ query-specific evidence
+ memory architecture hidden from the agent
+ strict separation of relevance / trust / authority / time
+ experiments before adding intelligence
```

This is an **architectural position**, not proof of benchmark superiority. LongMemEval #18 is required before making quality claims against competitors.

---

# How to read this document

We compare systems using the following dimensions:

| Dimension | Question |
|---|---|
| Representation | What becomes memory: verbatim source, extracted facts, blocks, JSON records, graph facts? |
| Source preservation | Is original evidence retained or does extracted memory become primary? |
| Retrieval | Semantic, lexical, hybrid, graph, tool-driven? |
| Relations | Are edges first-class? What do they influence? |
| Temporal state | Can facts evolve/invalidate while preserving history? |
| Provenance | Can a returned item trace back to source/version/span? |
| Write lifecycle | How are memories added, changed, consolidated or rejected? |
| Scope | How are user/agent/session/project boundaries represented? |
| Agent control | Does the agent explicitly manage memory or receive an abstraction? |
| Rendering | What artifact is ultimately sent to the consuming model? |
| Evaluation | What benchmarks/controls does the system publish? |

A blank or cautious cell does **not** mean a competitor lacks a capability. It means we do not want to infer beyond the primary material reviewed for this project.

---

# Product / framework systems

## Mem0

### Primary sources verified

- https://docs.mem0.ai/open-source/features/graph-memory
- https://docs.mem0.ai/migration/oss-v2-to-v3
- https://docs.mem0.ai/platform/cli
- https://arxiv.org/abs/2504.19413

### Current architecture signal

Mem0 focuses on extracting salient memories and retrieving them through production-oriented search infrastructure.

A current OSS migration guide describes a newer algorithm with:

```text
single-pass ADD-only extraction
+ semantic search
+ BM25 keyword search
+ entity matching/linking
```

The same guide explicitly says external graph-store support was removed from the newer open-source path and replaced by built-in entity linking.

A separate Graph Memory documentation page still describes the older/alternate graph architecture where an extraction LLM creates entities/relations, vector search orders hits and graph context is returned alongside them.

### Documentation-version caution

For TESSERA comparisons, do **not** write simply:

```text
Mem0 = vector + graph
```

without identifying version/product path. Current Mem0 documentation contains materially different graph behavior across pages/migration generations.

### Especially relevant to TESSERA

- pragmatic memory extraction;
- strong hybrid retrieval direction;
- user/agent/run scoping;
- entity linking;
- structured CLI/agent output;
- production-oriented latency/cost posture.

### TESSERA difference / hypothesis

TESSERA starts with source-backed text and stable document/evidence identity rather than making extracted memory the only visible truth substrate.

TESSERA's basic retrieval path can operate without a generative extraction call.

Unproven questions for #18:

```text
Does atomic/source-backed representation preserve evidence better?
Does it cost more context?
Does Mem0-style extraction produce better downstream QA?
Does TESSERA provenance materially improve reliability?
```

---

## Zep / Graphiti

### Primary sources verified

- https://help.getzep.com/v3/overview
- https://help.getzep.com/graph-overview
- https://help.getzep.com/graphiti/getting-started/overview
- https://help.getzep.com/graphiti/getting-started/welcome
- https://help.getzep.com/zep-vs-graphiti
- https://arxiv.org/abs/2501.13956

### How they approach memory

Graphiti is the open-source temporal Context Graph framework. Its documented architecture includes:

```text
episodic ingestion
→ entity + edge extraction
→ bi-temporal / validity metadata
→ fact invalidation
→ hybrid time + full-text + semantic + graph retrieval
→ incremental graph updates
```

Zep builds managed agent memory on top of that model and describes a governed Context Lake containing many Context Graphs, with prompt-ready context served to agents.

### Especially relevant to TESSERA

Zep/Graphiti is one of the strongest existing references for:

```text
changing facts
temporal validity
fact invalidation
incremental graph updates
source episodes / provenance
hybrid graph retrieval
```

### TESSERA difference / hypothesis

Graphiti makes the temporal graph a central representation.

TESSERA currently makes **source documents + canonical identities + evidence ledger** the stable substrate and treats graph intelligence as a layer that must prove value through ablation.

The important comparison is therefore not:

```text
who has a graph?
```

It is:

```text
Graphiti temporal Context Graph
vs
TESSERA source-backed atomic/evidence substrate
```

on:

```text
temporal update correctness
historical traceability
retrieval quality
context tokens
index/update cost
```

Related Test Cards: #12, #14, #15, #16, #25, #26, #27.

---

## Letta / MemGPT lineage

### Primary source verified

- https://docs.letta.com/

### How it approaches memory

Letta positions itself as a platform/runtime for **stateful agents**. Memory is closely integrated with persistent agent state and agent operation rather than exposed only as an external retrieval service.

Its memory model and broader harness let agents maintain persistent state across interactions and use memory as part of an agent runtime.

### Especially relevant to TESSERA

The main contrast is **control model**:

```text
Letta
→ memory is part of the agent/runtime model
→ agent state and memory management are closely coupled

TESSERA
→ memory architecture is abstracted behind a layer
→ evidence/provenance remain visible to the consuming agent
```

Neither is automatically better.

Future evaluation should ask whether hiding memory mechanics reduces failure modes or removes useful agent control.

---

## LangGraph / LangMem / LangChain memory patterns

### Primary sources verified

- https://docs.langchain.com/oss/python/langchain/long-term-memory
- https://docs.langchain.com/oss/python/concepts/memory

### How it approaches memory

Current LangChain/LangGraph documentation describes long-term memory as JSON documents stored by namespace/key in LangGraph stores and recalled across threads.

The conceptual framework separates:

```text
semantic memory
→ facts

episodic memory
→ experiences

procedural memory
→ instructions/rules
```

It also distinguishes write timing such as hot-path vs background updates.

### TESSERA difference

TESSERA's semantic drawers are **not the same taxonomy**:

```text
TESSERA
facts / preferences / insights

≠

semantic / episodic / procedural
```

TESSERA treats harness instructions as document/instruction semantics with `drawer: null`, rather than turning all instructions into a fourth semantic memory drawer.

LangGraph provides a broad application/runtime substrate; TESSERA aims to be a narrower memory/evidence subsystem that can plug into different runtimes.

---

## MemOS

### Primary sources verified

- https://github.com/MemTensor/MemOS
- https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/memos_intro.md
- https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/core_concepts.md

### How it approaches memory

MemOS explicitly describes itself as a **Memory Operating System**. Memory is treated as a first-class orchestrated resource with unified lifecycle/scheduling concepts.

Its architecture includes concepts such as:

```text
MOS orchestration layer
MemCubes
multiple memory types
user/session management
memory scheduling
retrieval / governance
```

### Especially relevant to TESSERA

MemOS is a strong reference for the broad “memory operating layer” positioning.

### TESSERA difference / hypothesis

TESSERA is intentionally narrower today:

```text
text-first
local deterministic Foundation
source identity
provenance
structured evidence
```

It does not yet try to orchestrate all parametric/activation/textual forms of memory.

The research question is whether a narrower auditable substrate produces a stronger base before adding OS-like orchestration.

---

## MemPalace

### Primary source verified

- https://github.com/bassemhalawani/memorypalace

> Previous TESSERA documentation referenced `MemPalace/mempalace`. The verified public repository identifies `bassemhalawani/memorypalace` as an official source; this document corrects that reference.

### How it approaches memory

MemPalace describes itself as local-first AI memory with **verbatim storage**. It explicitly says it does not summarize, extract or paraphrase stored conversation history by default.

Its documented architecture includes:

```text
verbatim source retention
structured palace organization
pluggable semantic retrieval
local operation
Temporal Knowledge Graph
MCP tooling
```

Its repository publishes reproducible benchmark artifacts and reports raw LongMemEval retrieval recall such as 96.6% R@5 for a zero-API-call path.

### Why it is an especially important TESSERA control

MemPalace directly challenges a core assumption in structured memory systems:

> Does extraction/atomicization actually improve memory, or can verbatim storage plus strong retrieval retain more useful evidence?

### Fair TESSERA comparison

Do **not** compare:

```text
TESSERA top-5 atomic memory IDs
vs
MemPalace top-5 source sessions
```

Instead #18 should control:

```text
same source histories
same encoder when isolating representation
session-normalized recall
token-budget evidence recall
same downstream reader
same rendering controls
```

This comparison is strategically more useful than claiming TESSERA is “more advanced” because it has richer metadata.

---

# Research architectures / benchmark signals

These are not necessarily direct competitors; they influence TESSERA experiments.

## QUMem

TESSERA inherits the useful semantic separation around facts/preferences/insights while adapting it into an agent/runtime-agnostic text/evidence layer.

## A-MEM

Relevant concepts:

```text
atomic structured notes
memory links
memory evolution
```

TESSERA is deliberately more conservative about autonomous rewriting/evolution until provenance and write admission are measured.

## GraphMemix — 2026-08-27

Primary source:
- https://arxiv.org/abs/2608.26983

Paper focus:

```text
query-aware evidence forest
candidate graph expansion
direct evidence utility
relation activation/reliability cost
maximum evidence budget
quality/cost Pareto optimization
```

TESSERA response:
- #25 Query-aware Graph Expansion / Evidence Budget.

## CaSKG — 2026-08-26

Primary source:
- https://arxiv.org/abs/2608.25500

Paper focus:

```text
candidate skill graph
edge reliability calibration
counterfactual remove/substitute/reorder probes
state-filtered weighted graph
task-conditioned expansion
```

TESSERA response:
- #26 Relation Confidence / Edge Validation.

Core distinction:

```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

## MemToC — 2026-08-26

Primary source:
- https://arxiv.org/abs/2608.26295

Paper focus:

```text
memory/parametric answer vs tool return
independently controlled source correctness
source arbitration
abstention side effects
```

TESSERA response:
- #27 Evidence Arbitration;
- #20 `sufficient | insufficient | conflicting | ambiguous`;
- #32 Authority / Scope / Instruction Precedence.

## RENDER — 2026-06-05

Primary source:
- https://arxiv.org/abs/2608.23568

Paper focus:

```text
same underlying information
+ different reader-facing artifact
→ materially different downstream memory scores
```

TESSERA response:
- #28 RAW vs EVIDENCE vs STRUCTURED renderer ablation, starting with #18.

---

# Relation model comparison lens

One of the most important TESSERA distinctions for future competitor/research comparisons is that “having a graph” is not enough.

We want to ask four separate questions:

```text
relation_type
→ what does this edge mean?

relation_origin
→ where did the edge come from?

relation_confidence
→ how strongly do we believe the edge is correct?

query_relevance
→ how useful is traversing this edge for this query?
```

A system can have excellent graph extraction but poor query-time traversal, or weakly calibrated edges but a strong retriever. Competitive analysis should keep those dimensions separate.

---

# Capability / architecture matrix

Legend:

```text
✓ strongly documented / central
~ supported or architecture/config dependent
? TESSERA future/unproven
— not a central focus in the primary material reviewed
```

| System | Source/verbatim preservation | Structured/extracted memory | Graph / relations | Temporal model | Explicit source-version/span provenance | Agent/runtime control model | Local/core path |
|---|---:|---:|---:|---:|---:|---|---:|
| **TESSERA current** | ✓ | ✓ canonical/atomic | ~ explicit + structural signal | — future | ✓ | memory mechanics abstracted; evidence visible | ✓ |
| Mem0 current OSS direction | ~ | ✓ extraction | ~ entity linking; graph behavior version-dependent | ~ timestamps/metadata | ~ | memory service/SDK | ✓ configurable |
| Zep / Graphiti | ✓ episodic source | ✓ graph facts/entities | ✓ central | ✓ bi-temporal / invalidation | ✓ episodic provenance | Context Graph / managed Context Lake | Graphiti local; Zep managed |
| Letta | ✓ runtime/history dependent | ✓ persistent agent memory/state | ~ not central comparison axis here | ~ persistent state | ~ | agent/runtime-visible stateful memory | ✓ self-host/runtime options |
| LangGraph / LangChain | app-defined | app-defined JSON / memory patterns | app-defined | app-defined | app-defined | application/agent framework | ✓ |
| MemOS | ✓ multi-source/textual | ✓ multiple memory types | ✓ supported | ~ lifecycle-oriented | ~ explainable/governed | Memory OS / orchestration layer | ✓ open source |
| MemPalace | ✓ strong/verbatim | ~ structured organization | ✓ temporal KG | ✓ graph validity | ✓ source retained | local memory/MCP layer | ✓ |

This table represents **documented architectural emphasis as of the verification date**, not benchmark ranking.

---

# Where TESSERA currently appears differentiated

## 1. Provenance before advanced intelligence

Stable source document identity, source version hashes and evidence spans are Foundation contracts before temporal/arbitration features are added.

## 2. Trust dimensions remain separated

Roadmap invariant:

```text
retrieval relevance
≠ memory confidence
≠ source authority
≠ relation confidence
≠ temporal validity
≠ utility
```

TESSERA deliberately avoids a single opaque “truth score”.

## 3. Non-memory text is first-class without new drawers

Harness instructions and project/reference documents can be indexed with `drawer: null` instead of being mislabeled as preferences/facts simply to fit a memory taxonomy.

## 4. Graph intelligence must prove itself

TESSERA does not assume more graph traversal is better. #14/#25/#26 compare no graph / simple graph / typed / query-aware / confidence-aware variants.

## 5. The evidence interface itself is testable

RENDER-inspired #28 asks whether TESSERA's STRUCTURED Evidence interface improves downstream behavior under fixed retrieval.

---

# Where competitors are ahead / TESSERA is incomplete

## Temporal graph maturity

Graphiti already documents bi-temporal relationships, invalidation and incremental graph updates. TESSERA temporal/state behavior is still #15/#16.

## Managed production infrastructure

Zep and Mem0 offer mature production/service ecosystems. TESSERA is currently a Foundation-stage local/open architecture.

## Stateful agent runtime maturity

Letta has a broader persistent-agent runtime; LangGraph has broad workflow/store integration; MemOS targets a broader memory-OS layer.

## External benchmark evidence

TESSERA does not yet have a clean controlled LongMemEval result. #18 is required before competitive quality claims.

---

# Competitive hypotheses to test

Instead of turning the table into marketing, TESSERA converts differences into experiments:

1. **Raw vs Atomic** — atomic/source-backed representation vs verbatim source under same encoder and token budget (#18).
2. **Graph value** — no graph vs controlled graph expansion (#14/#25).
3. **Edge reliability** — whether confidence-aware relations reduce harmful context (#26).
4. **Temporal complexity** — state-key/evidence model vs mature temporal-graph approaches (#15/#16).
5. **Renderer effect** — RAW vs EVIDENCE vs STRUCTURED under frozen retrieval (#28).
6. **Evidence Arbitration** — explicit source conflict vs silent winner (#27/#20).
7. **Authority/scope** — deterministic instruction precedence vs relevance/newest wins (#32).
8. **Memory-control visibility** — agent-managed memory vs abstracted memory architecture, future evaluation.

---

# Current positioning

A defensible current positioning is:

> **TESSERA is a text-first, agent-agnostic memory and evidence layer focused on stable identity, source-version-aware provenance, explainable retrieval and auditable evolution. It hides storage/indexing complexity while keeping evidence visible to the consuming agent.**

A claim such as:

> “TESSERA is better than Mem0, Zep/Graphiti or MemPalace”

is not justified until controlled #18 results exist.
