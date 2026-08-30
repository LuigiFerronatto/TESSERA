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

TESSERA is a **text-first, agent-agnostic memory and evidence layer**, not a final-answer engine and not merely GraphRAG.

The current Foundation provides:

1. canonical understanding of heterogeneous text;
2. stable knowledge and source-document identity;
3. explicit graph structure as one retrieval signal;
4. explainable multi-signal ranking;
5. query-aware relevant evidence;
6. source-version-aware Evidence Ledger / provenance;
7. a basic heuristic write-side sanitization gate for memories written through `write_memory_note()`;
8. CI + Test Card governance.

More ambitious memory admission, graph expansion, temporal state, authority, arbitration and abstention remain experiments.

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

TESSERA hides memory-system mechanics while preserving enough evidence and provenance for the consuming agent to audit what was retrieved.

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
- No generative LLM is mandatory for the basic Foundation retrieval path.
- TESSERA does not silently rewrite user source files during indexing.

---

# Current read / retrieval pipeline

```text
TEXT FILES
   ↓
DISCOVER
   ↓
PARSE + CANONICAL NORMALIZATION
   ├─ complete / partial / absent frontmatter
   ├─ document classification
   ├─ semantic drawer when applicable
   ├─ metadata_origin
   ├─ scope
   └─ explicit/local relations
   ↓
STABLE IDENTITY
   ├─ identity.id
   ├─ source.document_id
   ├─ source.path
   ├─ document_hash
   └─ content_hash
   ↓
GRAPH / INDEX
   ├─ memory/document nodes
   ├─ tag/entity structure
   ├─ explicit relations
   └─ lexical corpus / TF-IDF
   ↓
RETRIEVAL
   ├─ lexical TF-IDF
   ├─ token overlap
   ├─ title / ID relevance
   ├─ metadata relevance
   ├─ graph/PageRank structural signal
   └─ deterministic intent/type boost
   ↓
QUERY-AWARE EVIDENCE
   ├─ relevant paragraph when supported
   └─ None instead of arbitrary evidence when unsupported
   ↓
EVIDENCE LEDGER / PROVENANCE
   ├─ evidence_id
   ├─ source document identity
   ├─ source version hashes
   ├─ exact span when uniquely provable
   └─ freshness state
   ↓
STRUCTURED RETRIEVAL RESULT
```

---

# Current write path

The existing `write_memory_note()` path already contains a **basic heuristic security gate**:

```text
candidate memory content
   ↓
WriteGatingEngine.audit_and_sanitize()
   ├─ known injection-pattern checks
   ├─ suspicious-tag signal
   └─ deterministic redaction for matched patterns
   ↓
MemoryFrontmatter
   ↓
Markdown source file
```

This capability must not be confused with roadmap #19.

Current gating answers roughly:

> Does this content match a small set of known hostile-instruction patterns before persistence?

Roadmap #19 is broader **memory admission** and asks:

> Is this candidate new, useful, stable, non-duplicate and supported by evidence — and should it become durable memory at all?

So:

```text
basic heuristic sanitization       IMPLEMENTED
full evidence-aware write admission PLANNED (#19)
```

---

# 1. Canonical Metadata Layer

**Tracking:** Issue #9 / PR #3

TESSERA normalizes heterogeneous project text into one canonical representation before indexing.

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
metadata_origin:
  drawer: inferred
```

Harness knowledge remains orthogonal to semantic drawers:

```yaml
classification:
  document_type: harness_instructions
  kind: instruction
  drawer: null
```

This permits `CLAUDE.md`, `AGENTS.md` and `*.SKILL.md` to participate in the knowledge layer without becoming preferences/facts merely to fit a taxonomy.

---

# 2. Stable identity model

```text
identity.id
→ persistent knowledge/memory identity

source.document_id
→ persistent source-document identity

source.path
→ current location

document_hash / content_hash
→ current version/fingerprint
```

Lifecycle guarantee:

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

This is the substrate for provenance today and incremental/temporal lifecycle later.

---

# 3. Graph representation

TESSERA preserves explicit/local relations and graph structure, but the graph is **not the final relevance engine**.

```text
explicit relations
   ↓
graph
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

Future relation intelligence must keep these separate:

```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

---

# 4. Explainable retrieval

**Tracking:** Issue #8 / PR #2

The current ranker combines inspectable signals rather than letting PageRank alone determine relevance:

```text
ranking
  ← lexical TF-IDF
  ← direct overlap
  ← title / ID
  ← metadata
  ← normalized relation/PageRank signal
  ← deterministic type/intent behavior
```

Recency is disabled by default because recent information is not necessarily current truth.

Known baseline limitation:

```text
pq o LAO existe?
→ intended charter memory can still appear at #2
```

That is preserved as benchmark evidence rather than tuned away per-query.

---

# 5. Query-aware Relevant Evidence

TESSERA foregrounds a query-specific paragraph when lexical support exists while preserving the full memory body.

```text
retrieved memory
├─ relevant_evidence
└─ full body
```

If evidence cannot be supported, `relevant_evidence` remains `None`.

This is not yet the future four-state #20 contract:

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

It does not decide authority, truth, arbitration winner, query relevance or temporal validity.

If evidence text occurs multiple times and the exact occurrence cannot be proven, the span is null rather than guessed.

---

# 7. Derived state and source of truth

```text
SOURCE FILES
   ├─ canonical metadata
   ├─ identity manifest
   ├─ graph/index cache
   └─ evidence ledger
```

Derived state must be reconstructible from source files.

Current indexing still uses coarse cache/rebuild semantics. **Incremental and idempotent indexing remains #12.**

---

# 8. CI and experimental governance

**Tracking:** Issue #10 / PR #4 and Issue #22 / PR #24

```text
Issue / Test Card
→ implementation PR
→ unit / contract tests
→ CLI smoke
→ sanity retrieval evaluation
→ evidence + learnings
→ KEEP | ITERATE | REVERT | DROP | DEFER
```

Current sanity regression baseline:

```text
Hit@1          75%
Hit@3         100%
Hit@5         100%
MRR           0.875
Evidence hit  100%
```

These are regression metrics, not competitive benchmark claims.

---

# Current module map

| Module | Current role |
|---|---|
| `tessera/canonical.py` | Canonical parsing, classification and stable metadata semantics |
| `tessera/engine_core.py` | Write path, indexing, graph construction and core retrieval |
| `tessera/engine.py` | Evidence-aware facade integrating retrieval with provenance |
| `tessera/evidence.py` | Evidence records, ledger, freshness and span/provenance helpers |
| `tessera/security.py` | Basic deterministic write-side hostile-pattern audit/sanitization |
| `tessera/conflict.py` | Existing compatibility conflict logic; future state/arbitration redesign remains experimental |
| `tessera/models.py` | Domain models for memory/write paths |
| `tessera/cli.py` | Human CLI surface |
| `benchmarks/sanity/` | Deterministic regression evaluation |

---

# Implemented vs planned

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
basic heuristic write-side sanitization
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
#19 evidence-aware memory admission / advanced write gating
#21 experience learning / utility feedback
```

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

This is roadmap architecture, not current runtime behavior. Individual layers may be simplified or dropped if their Test Cards do not show measurable value.
