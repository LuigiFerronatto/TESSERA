# TESSERA

**Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories**

TESSERA is a **text-first, agent-agnostic memory and evidence layer** for long-running AI agents.

Its job is not to answer for the agent. Its job is to hide memory-system complexity — storage, indexing, relations, source tracking and retrieval — while returning enough **structured evidence, provenance and navigation** for the consuming agent to reason safely.

> **TESSERA abstracts memory architecture away from the agent. It does not replace the cognition of the agent; it hides memory complexity so the agent can focus on cognition.**

---

## Executive takeaway

The current Foundation already provides:

```text
text documents
→ canonical understanding
→ stable memory + source identity
→ graph/index
→ explainable multi-signal retrieval
→ query-aware relevant evidence
→ Evidence Ledger / provenance
→ structured retrieval result
```

TESSERA deliberately does **not** claim that temporal reasoning, confidence-aware graph traversal, source arbitration, abstention or adaptive retrieval are solved. Those capabilities live in Test Cards and must earn their way into the architecture through measurable experiments.

---

# In plain language

An agent may have hundreds or thousands of Markdown notes, instructions and learnings spread across a project:

```text
memories/
research/
CLAUDE.md
AGENTS.md
*.SKILL.md
project notes
```

The agent should not need to understand:

```text
where every memory is stored
how files are normalized
how identity survives a rename
how the graph is built
how evidence is traced to a source version
which retrieval signals are combined
```

It should be able to ask something like:

```text
"qual é o propósito deste projeto?"
```

and receive an evidence-rich result containing roughly:

```text
memory identity
relevance score + explanation
relevant evidence for this query
full original memory
source path
stable source-document identity
source version hashes
exact evidence span when provable
direct related memories
```

Then **the agent decides what that evidence means**.

---

# Why TESSERA exists

Long-term agent memory is not only a retrieval problem.

A useful memory layer eventually needs to deal with questions such as:

```text
Is this the same memory after a file moves?
Which version of the source supports this evidence?
Is this paragraph actually relevant to this query?
Why did this memory rank above another one?
Are these two memories related?
Is a relation trustworthy?
Which source is authoritative for this scope?
Do two sources conflict?
Is there enough evidence to continue?
```

The current Foundation focuses on making the first group of those questions **auditable and deterministic** before adding more intelligence.

---

# Current capabilities

## Canonical text understanding

TESSERA can index heterogeneous Markdown with complete, partial or absent frontmatter and normalize it into Canonical Metadata.

It distinguishes semantic memories from other useful text documents.

```yaml
# semantic memory
classification:
  document_type: memory
  kind: factual
  drawer: facts
```

```yaml
# harness instruction
classification:
  document_type: harness_instructions
  kind: instruction
  drawer: null
```

TESSERA keeps exactly three semantic drawers:

```text
facts
preferences
insights
```

Harness instructions, scope, confidence, authority, temporal state and relations are metadata/facets — not new drawers.

## Stable identity

TESSERA separates:

```text
identity.id
→ persistent knowledge identity

source.document_id
→ persistent source-document identity

source.path
→ current location

document_hash / content_hash
→ current version
```

A rename/move can therefore preserve identity while changing only location.

## Explainable retrieval

The current ranker combines inspectable signals such as:

```text
TF-IDF lexical similarity
direct token overlap
title / ID relevance
metadata relevance
normalized graph/PageRank signal
deterministic type/intent boost
```

PageRank is a **structural signal**, not the final answer.

Recency is disabled by default because “newer” is not equivalent to “currently true”.

## Query-aware evidence

TESSERA can foreground the paragraph most relevant to the current query while preserving the original full memory:

```text
retrieved memory
├─ relevant_evidence
└─ full body
```

If no paragraph has enough support, `relevant_evidence` is `None` rather than an arbitrary paragraph.

## Evidence Ledger / provenance

Every canonical result can be traced to its source version.

```yaml
evidence_id: ev_...
memory_id: project/charter
source:
  document_id: doc_...
  path: project/charter.md
  document_hash: ...
  content_hash: ...
span:
  start_line: 31
  end_line: 37
```

If an exact evidence occurrence cannot be proven — for example the same text appears multiple times — TESSERA returns a null span instead of fabricating precision.

## Basic write-side sanitization

`write_memory_note()` currently runs a small deterministic `WriteGatingEngine` that checks known hostile-instruction patterns and suspicious tags before persistence.

This is **not** the full future memory-admission layer. The broader #19 experiment will test whether a candidate is new, duplicated, stable, useful and sufficiently evidence-backed before becoming durable memory.

## CI and sanity evaluation

Every meaningful change is expected to pass:

```text
Python 3.9 tests
Python 3.12 tests
CLI smoke
sanity retrieval evaluation
```

The sanity suite is a small synthetic **regression alarm**, not a competitive benchmark. Its exact baseline is versioned with the fixture and should only move with an explicit behavioral explanation.

---

# Quickstart

Requires Python **3.9+**.

## Install for development

```bash
git clone https://github.com/LuigiFerronatto/TESSERA.git
cd TESSERA
pip install -e ".[dev]"
```

Or use the repository installer:

```bash
./install.sh --venv --dev
```

## Create and query memory

```python
from tessera import TesseraEngine, Entity

engine = TesseraEngine(storage_dir="./memories")

engine.write_memory_note(
    mem_id="project/postgres-replication",
    mem_type="factual",
    episode_id="ep_001",
    content="Maria configured PostgreSQL read replication.",
    tags=["postgresql", "infra"],
    entities=[Entity("Maria", "Data engineer")],
)

engine.build_index()

results = engine.retrieve_context(
    "quem configurou a replicação do PostgreSQL?",
    top_n=3,
)

for result in results:
    print(result["id"], result["score"])
    print(result["relevant_evidence"])
    print(result["provenance"])
```

## CLI

```bash
tessera init ./memories

tessera write ./memories \
  --id project/postgres-replication \
  --type factual \
  --episode ep_001 \
  --content "Maria configured PostgreSQL read replication." \
  --tags postgresql,infra

tessera index ./memories

tessera query ./memories "quem configurou a replicação do PostgreSQL?"

tessera query ./memories "como o projeto funciona?" --debug
```

The source Markdown files remain the source of truth. Derived index artifacts live under `.tessera_index/` and can be rebuilt.

---

# What TESSERA returns

The semantic retrieval contract is the structured result returned by:

```python
engine.retrieve_context(...)
```

Typical fields include:

```text
id
type
score
score_explain
filepath / filename
relevant_evidence
evidence_info
body
frontmatter
related_ids
provenance
evidence
```

See [`docs/OUTPUT_CONTRACT.md`](docs/OUTPUT_CONTRACT.md) for field semantics and nullability.

Important:

```text
retrieval score
≠ confidence
≠ authority
≠ truth
```

---

# Architecture

Current read path:

```text
TEXT
  ↓
Canonical Metadata
  ↓
Stable Identity
  ↓
Graph / Index
  ↓
Explainable Retrieval
  ↓
Relevant Evidence
  ↓
Evidence Ledger / Provenance
  ↓
Structured Evidence
  ↓
AGENT
```

Future architecture is intentionally conditional on experiments.

```text
Query-aware Graph Expansion
Relation Confidence
Temporal State / State Keys
Authority / Scope / Precedence
Conflict Detection
Evidence Arbitration
Evidence Sufficiency
Adaptive Retrieval
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

# Research-driven development

TESSERA uses papers as **research signals**, not as implementation instructions.

Examples:

```text
GraphMemix
→ query-aware evidence graph / budget
→ Test Card #25

CaSKG
→ edge reliability / validation
→ Test Card #26

MemToC
→ source conflict / arbitration / abstention
→ Test Cards #27 / #20 / #32

RENDER
→ reader-facing format as evaluation variable
→ Test Card #28
```

The rule is:

```text
paper
→ insight
→ hypothesis
→ Test Card
→ controlled experiment
→ evidence
→ KEEP | ITERATE | REVERT | DROP | DEFER
```

See [`docs/research/`](docs/research/).

---

# Competitive landscape

TESSERA is evaluated against architectural ideas from systems/frameworks such as:

```text
Mem0
Zep / Graphiti
Letta
LangGraph / LangMem
MemOS
MemPalace
```

The current differentiating thesis is not “TESSERA has a graph”. It is the combination of:

```text
text-first source of truth
+ stable memory/source identity
+ source-version-aware provenance
+ explainable retrieval
+ query-specific evidence
+ strict separation of relevance / confidence / authority / utility
+ experimental governance before adding intelligence
```

Those are architectural characteristics, **not proof that TESSERA is better**. Competitive quality claims wait for controlled benchmarks such as LongMemEval (#18).

See [`docs/research/COMPETITIVE_LANDSCAPE.md`](docs/research/COMPETITIVE_LANDSCAPE.md).

---

# Roadmap

The living roadmap intentionally separates what exists from what is still being tested. Current near-term order:

```text
PUBLIC / GOVERNANCE HARDENING
→ project-agnostic public surface
→ README + visual docs
→ changelog / PR contract / CI v2

FOUNDATION CONTRACT
→ Engine / CLI / MCP parity
→ incremental indexing
→ text ingestion / segmentation
→ diagnostics

MEASURE EARLY
→ LongMemEval + renderer controls

THEN
→ relations
→ temporal state
→ authority / conflict
→ adaptive retrieval
→ state / abstention
→ learning
```

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the living experimental roadmap.

---

# Test Card development model

Every meaningful task should follow:

```text
1 Issue
  ↓
1 Test Card
  ↓
linked PR
  ↓
CI / benchmark / real outputs
  ↓
Evidence + Learnings
  ↓
KEEP | ITERATE | REVERT | DROP | DEFER
```

A technically correct feature can still end in **DROP** if it does not improve measurable outcomes.

This is intentional.

---

# Documentation

Start with [`docs/README.md`](docs/README.md).

Recommended path:

```text
OVERVIEW.md
  ↓
FEATURES.md + CONCEPTS.md
  ↓
ARCHITECTURE.md
  ↓
QUERY_EXAMPLES.md + OUTPUT_CONTRACT.md
  ↓
ROADMAP.md
```

Research and competitors live under [`docs/research/`](docs/research/).

Historical/demo documents are not the current architecture source of truth; the documentation map explains their role and precedence.

---

# Project status

TESSERA is currently an evolving Foundation, not a finished long-term-memory product.

What is already strong enough to build on:

```text
identity
canonical metadata
explainable retrieval
query-aware evidence
provenance
CI / Test Card discipline
```

What we still need to prove:

```text
incremental state correctness
external benchmark quality
graph expansion value
relation reliability
temporal state accuracy
source arbitration
authority / precedence
abstention semantics
adaptive retrieval
learning / utility feedback
```

That distinction — **implemented vs hypothesized** — is part of the product design, not just project management.
