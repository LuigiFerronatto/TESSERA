# TESSERA — Architecture

> Current architecture reference for the Foundation on `main`.
>
> - Product overview: [OVERVIEW.md](OVERVIEW.md)
> - Implemented capabilities: [FEATURES.md](FEATURES.md)
> - Core vocabulary: [CONCEPTS.md](CONCEPTS.md)
> - Query examples: [QUERY_EXAMPLES.md](QUERY_EXAMPLES.md)
> - Experimental roadmap: [ROADMAP.md](ROADMAP.md)
> - Research / competitors: [research/](research/)

## Executive takeaway

TESSERA is not a final-answer engine and it is not “GraphRAG with a different name”. It is a **text-first, agent-agnostic memory and evidence layer**.

The current Foundation does four things especially deliberately:

1. understands heterogeneous text through a canonical model;
2. keeps memory identity separate from file location and source version;
3. retrieves with inspectable multi-signal ranking and query-specific evidence;
4. can prove where retrieved evidence came from through the Evidence Ledger.

Advanced graph expansion, temporal state, authority, conflict arbitration, abstention and adaptive retrieval remain Test Cards — they are not represented here as implemented capabilities.

---

# Product contract

```text
AGENT
  │ natural-language information need
  ▼
TESSERA
  │ hides storage/index/graph/provenance mechanics
  ▼
STRUCTURED EVIDENCE
  │ evidence + source + relations + score/provenance
  ▼
AGENT
  └─ reasons / acts / answers
```

TESSERA abstracts memory architecture away from the consuming agent while preserving enough evidence and provenance for the agent to audit and navigate what was retrieved.

---

# Architectural invariants

- Source text remains the source of truth.
- Indexes, manifests, graph snapshots and evidence ledgers are derived/rebuildable state.
- Exactly three semantic drawers exist: `facts`, `preferences`, `insights`.
- Non-memory documents may be indexed with `drawer: null`.
- `document_type`, scope, authority, confidence, temporal state, relations, quality and utility are facets — not new drawers.
- Retrieval relevance is not semantic confidence, authority or utility.
- A file path is location, not identity.
- A hash represents a version/fingerprint, not identity.
- No generative LLM is mandatory for the basic Foundation path.
- TESSERA does not silently rewrite user source files during indexing.

---

# Current data pipeline

```text
TEXT FILES
   │
   ▼
DISCOVER
   │
   ▼
PARSE + CANONICAL NORMALIZATION
   ├─ complete / partial / absent frontmatter
   ├─ document classification
   ├─ semantic drawer when applicable
   ├─ metadata_origin
   ├─ scope
   └─ explicit/local relations
   │
   ▼
STABLE IDENTITY
   ├─ identity.id
   ├─ source.document_id
   ├─ source.path
   ├─ document_hash
   └─ content_hash
   │
   ▼
GRAPH / INDEX
   ├─ memory/document nodes
   ├─ tag/entity structure
   ├─ explicit relations
   └─ lexical corpus / TF-IDF
   │
   ▼
RETRIEVAL
   ├─ lexical TF-IDF
   ├─ token overlap
   ├─ title / ID relevance
   ├─ metadata relevance
   ├─ graph/PageRank structural signal
   └─ deterministic intent/type boost
   │
   ▼
QUERY-AWARE EVIDENCE
   ├─ relevant paragraph when supported
   └─ None instead of arbitrary evidence when unsupported
   │
   ▼
EVIDENCE LEDGER / PROVENANCE
   ├─ evidence_id
   ├─ source document identity
   ├─ source version hashes
   ├─ exact span when uniquely provable
   └─ freshness state
   │
   ▼
STRUCTURED RETRIEVAL RESULT
```

---

# 1. Canonical Metadata Layer

**Tracking:** Issue #9 / PR #3

Projects contain heterogeneous text: normal Markdown, notes without frontmatter, harness instructions, project context and other reference documents. TESSERA normalizes these into one canonical representation before indexing.

Conceptually:

```yaml
identity:
  id: lao/charter

classification:
  document_type: memory
  kind: factual
  drawer: facts

source:
  document_id: doc_...
  path: lao/charter.md
  format: markdown

metadata_origin:
  drawer: inferred
  document_type: inferred
```

For harness instructions:

```yaml
classification:
  document_type: harness_instructions
  kind: instruction
  drawer: null
```

This lets `CLAUDE.md`, `AGENTS.md` and `*.SKILL.md` participate in the knowledge layer without being forced into a semantic memory drawer.

---

# 2. Stable identity model

The architecture separates four axes:

```text
identity.id
→ persistent knowledge/memory identity

source.document_id
→ persistent source-document identity

source.path
→ current source location

document_hash / content_hash
→ current source/content version
```

Expected lifecycle:

```text
MOVE / RENAME
identity.id        SAME
source.document_id SAME
source.path        CHANGED
content_hash       SAME
```

```text
CONTENT EDIT
identity.id        SAME
source.document_id SAME
source.path        SAME
content_hash       CHANGED
```

This separation is the substrate for provenance today and for incremental/temporal lifecycle later.

---

# 3. Graph representation

TESSERA already represents explicit relations and graph structure, but the graph is **not the final relevance engine**.

Current role:

```text
explicit/local relations
        ↓
knowledge graph
        ↓
PageRank / structural signal
        ↓
one component of retrieval ranking
```

Not implemented yet:

```text
query-aware graph expansion      #25
relation confidence/validation   #26
controlled evidence budget       #25
typed-relation ablations          #14
```

The architecture intentionally separates:

```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

---

# 4. Explainable retrieval

**Tracking:** Issue #8 / PR #2

The Foundation retrieval ranker combines inspectable signals instead of allowing PageRank alone to determine relevance.

Conceptually:

```text
FINAL RANKING
  ← lexical TF-IDF
  ← direct overlap
  ← title / ID
  ← metadata
  ← normalized relation/PageRank signal
  ← deterministic type/intent behavior
```

Recency is disabled by default because recent information is not necessarily current truth.

The debug path exposes individual scoring signals so changes can be measured rather than guessed.

### Known limitation

The paraphrase:

```text
pq o LAO existe?
```

can still rank the intended charter memory at #2 instead of #1. This is deliberately retained as a sanity-baseline limitation; semantic/adaptive retrieval must prove itself through later ablations rather than query-specific tuning.

---

# 5. Query-aware Relevant Evidence

Instead of forcing the consuming agent to treat an entire memory as equally relevant, TESSERA foregrounds a query-specific evidence span when lexical support exists.

```text
retrieved memory
├─ relevant_evidence
└─ full body
```

If evidence cannot be supported, the field remains `None`.

This is **not yet** full Evidence Sufficiency/Abstention. The future four-state contract is tracked in #20:

```text
sufficient
insufficient
conflicting
ambiguous
```

---

# 6. Evidence Ledger

**Tracking:** Issue #11 / PR #6

The Evidence Ledger is an immutable/rebuildable provenance substrate derived from source files and Canonical Metadata.

Example shape:

```yaml
evidence_id: ev_...
memory_id: lao/charter
source:
  document_id: doc_...
  path: lao/charter.md
  document_hash: sha256:...
  content_hash: sha256:...
span:
  start_line: 31
  end_line: 37
extraction:
  method: paragraph_lexical
```

It answers:

> Where did this evidence come from, and which source version supports it?

It does **not** decide:

- authority;
- truth;
- arbitration winner;
- query relevance;
- temporal validity.

Those belong to later assessment/arbitration layers if their Test Cards succeed.

### Precision rule

If the same evidence text appears multiple times and the exact occurrence cannot be proven uniquely, TESSERA returns a null span rather than inventing precision.

---

# 7. Derived state and source of truth

Conceptually:

```text
SOURCE FILES
   │
   ├─ canonical metadata
   ├─ identity manifest
   ├─ graph/index cache
   └─ evidence ledger
```

Everything under the derived indexing layer must be rebuildable from source files.

Current indexing still uses coarse rebuild/cache behavior. **Incremental and idempotent indexing is #12, not a current capability.**

---

# 8. CI and experimental governance

**Tracking:** Issue #10 / PR #4 and Issue #22 / PR #24

Every meaningful change is expected to go through:

```text
Issue / Test Card
→ implementation PR
→ unit / contract tests
→ CLI smoke
→ sanity retrieval evaluation
→ evidence + learnings
→ KEEP | ITERATE | REVERT | DROP | DEFER
```

Current deterministic sanity baseline:

```text
Hit@1          75%
Hit@3         100%
Hit@5         100%
MRR           0.875
Evidence hit  100%
```

These are regression metrics, not competitive quality claims.

---

# Current module map

| Module | Current architectural role |
|---|---|
| `tessera/canonical.py` | Canonical parsing, classification, normalization and stable metadata semantics |
| `tessera/engine_core.py` | Core indexing, graph construction and retrieval implementation |
| `tessera/engine.py` | Evidence-aware engine facade integrating core retrieval with provenance |
| `tessera/evidence.py` | Evidence records, ledger construction, freshness and span/provenance helpers |
| `tessera/conflict.py` | Existing conflict compatibility logic; future state/arbitration redesign remains experimental |
| `tessera/models.py` | Core domain models used by memory/write paths |
| `tessera/cli.py` | Human CLI surface |
| `benchmarks/sanity/` | Deterministic regression evaluation, not competitive benchmark |

---

# What is implemented vs planned

## Implemented Foundation

```text
canonical text normalization
stable memory identity
stable source-document identity
explicit relation parsing
graph representation
explainable multi-signal ranking
query-aware relevant evidence
Evidence Ledger / provenance
CI + sanity evaluation
Test Card governance
```

## Planned / experimental

```text
#12 incremental/idempotent indexing
#13 metadata doctor
#14/#25/#26 controlled relations/graph intelligence
#15 temporal model + state keys
#16 conflict/supersession
#27 Evidence Arbitration
#32 source authority + instruction precedence
#20 four-state evidence sufficiency/abstention
#18 LongMemEval
#28 rendering ablation
#17 adaptive retrieval
#19 write gating / memory admission
#21 experience learning / utility feedback
```

Historical documents may describe some of these ideas as older prototypes. The current source of truth for product status is `FEATURES.md` + `ROADMAP.md` + the linked Test Cards.

---

# Target architecture — only if experiments justify it

```text
QUERY
  ↓
Candidate Retrieval
  ↓
Seed Evidence
  ↓
Query-Aware Graph Expansion
  ↓
Relation Reliability
  ↓
Temporal Validity / State Keys
  ↓
Authority / Scope / Precedence
  ↓
Conflict Detection
  ↓
Evidence Arbitration
  ↓
Evidence Status
  ↓
Structured Renderer
  ↓
CONSUMING AGENT
```

This is a roadmap target, not current runtime behavior.

The point of the Test Card process is that individual layers may be simplified or dropped if they do not improve measurable outcomes.
