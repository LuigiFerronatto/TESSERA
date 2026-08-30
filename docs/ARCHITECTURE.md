# TESSERA — Architecture

> Current architecture reference for the Foundation on `main`.
>
> See also: [OVERVIEW.md](OVERVIEW.md), [FEATURES.md](FEATURES.md), [CONCEPTS.md](CONCEPTS.md), [QUERY_EXAMPLES.md](QUERY_EXAMPLES.md), [OUTPUT_CONTRACT.md](OUTPUT_CONTRACT.md), [ROADMAP.md](ROADMAP.md), and [research/](research/).

## Executive takeaway

TESSERA is a **text-first, agent-agnostic memory and evidence layer**. It is not a final-answer engine and it is not merely GraphRAG.

The current Foundation provides canonical understanding of heterogeneous text, stable knowledge/source identity, explicit graph structure, explainable multi-signal retrieval, query-aware evidence, source-version-aware provenance, a basic heuristic write-side sanitization gate, and CI/Test Card governance.

Advanced memory admission, query-aware graph expansion, relation confidence, temporal state, instruction resolution, authority, Evidence Arbitration and abstention remain experiments.

## Product contract

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

## Architectural invariants

- Source text remains the source of truth.
- Indexes, manifests, graph snapshots and evidence ledgers are derived/rebuildable.
- Exactly three semantic drawers exist: `facts`, `preferences`, `insights`.
- Non-memory documents may be indexed with `drawer: null`.
- `document_type`, scope, authority, confidence, temporal state, relations, quality and utility are facets, not new drawers.
- Retrieval relevance ≠ confidence ≠ authority ≠ relation confidence ≠ temporal validity ≠ utility.
- File path = location, not identity.
- Hash = version/fingerprint, not identity.
- No generative LLM is mandatory for the basic Foundation path.
- User source files are not silently rewritten during indexing.
- Public examples/fixtures are project-agnostic.

## Current read / retrieval pipeline

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

## Current write path

The existing `write_memory_note()` path already contains a **basic heuristic security gate**:

```text
candidate memory content
   ↓
WriteGatingEngine.audit_and_sanitize()
   ├─ known hostile-instruction patterns
   ├─ suspicious-tag signal
   └─ deterministic redaction for matched patterns
   ↓
MemoryFrontmatter
   ↓
Markdown source file
```

This is different from roadmap #19:

```text
basic heuristic sanitization          IMPLEMENTED
full evidence-aware memory admission  PLANNED (#19)
```

# 1. Canonical Metadata Layer

**Tracking:** Issue #9 / PR #3

TESSERA normalizes heterogeneous project text into one canonical representation before indexing.

```yaml
identity:
  id: project/charter
classification:
  document_type: memory
  kind: factual
  drawer: facts
source:
  document_id: doc_...
  path: project/charter.md
metadata_origin:
  drawer: inferred
```

Harness instructions remain orthogonal to semantic drawers:

```yaml
classification:
  document_type: harness_instructions
  kind: instruction
  drawer: null
```

This allows `CLAUDE.md`, `AGENTS.md` and `*.SKILL.md` to participate without being forced into facts/preferences/insights. Adapter/precedence behavior remains experimental (#71/#72/#32).

# 2. Stable identity model

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

Source revision history beyond the current version is a separate experiment (#73); stable hashes alone are not presented as a full immutable history.

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

Future relation intelligence must keep these separate:

```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

Planned Test Cards: #14, #25, #26.

# 4. Explainable retrieval

**Tracking:** Issue #8 / PR #2

Current ranking combines inspectable signals:

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

The sanity corpus intentionally contains a colloquial purpose paraphrase so lexical limitations remain visible. We do not add query-specific boosts to hide a bad ranking.

# 5. Query-aware Relevant Evidence

TESSERA foregrounds a query-specific paragraph when lexical support exists while preserving the full memory body.

```text
retrieved memory
├─ relevant_evidence
└─ full body
```

If evidence cannot be supported, `relevant_evidence` remains `None`.

The future four-state #20 contract is not implemented yet:

```text
sufficient
insufficient
conflicting
ambiguous
```

# 6. Evidence Ledger

**Tracking:** Issue #11 / PR #6

The Evidence Ledger is an immutable/rebuildable provenance substrate derived from source files and Canonical Metadata.

```yaml
evidence_id: ev_...
memory_id: project/charter
source:
  document_id: doc_...
  path: project/charter.md
  document_hash: sha256:...
  content_hash: sha256:...
span:
  start_line: 31
  end_line: 37
extraction:
  method: paragraph_lexical
```

It answers: **where did this evidence come from, and which source version supports it?**

It does not decide authority, truth, arbitration winner, query relevance or temporal validity. If evidence text occurs multiple times and the exact occurrence cannot be proven, the span is null rather than guessed.

# 7. Derived state and indexing

```text
SOURCE FILES
   ├─ canonical metadata
   ├─ identity manifest
   ├─ graph/index cache
   └─ evidence ledger
```

Derived state must be reconstructible from source files. Current indexing still uses coarse cache/rebuild semantics; **incremental/idempotent indexing remains #12**.

Two additional Foundation gaps are explicit rather than implied:

```text
#69 plain-text ingestion beyond Markdown
#70 structure-aware segmentation of long documents
```

# 8. Interface boundary

The Python engine is the semantic source of retrieval results. CLI and MCP are transports/renderers around that contract.

A currently audited gap is that the MCP adapter exposes a smaller subset than the engine's evidence-rich result. Contract parity is tracked in #68 rather than being silently treated as solved.

# 9. Optional orchestration boundary

The repository contains an assisted orchestration path for information-need analysis, retrieval planning and state inference. TESSERA's core product identity remains the deterministic evidence layer.

Whether assisted planning/synthesis belongs as an optional adapter, and what value it adds over direct structured evidence, is tracked explicitly in #74/#17/#28.

# 10. CI and experimental governance

**Tracking:** Issue #10 / PR #4, governance PRs, and #67 for Quality Gate v2.

```text
Issue / Test Card
→ implementation PR
→ unit / contract tests
→ CLI smoke
→ sanity evaluation
→ evidence + learnings
→ KEEP | ITERATE | REVERT | DROP | DEFER
```

Sanity metrics are regression indicators, not competitive benchmark claims.

## Current module map

| Module | Current role |
|---|---|
| `tessera/canonical.py` | Canonical parsing, classification and stable metadata semantics |
| `tessera/engine_core.py` | Write path, indexing, graph construction and core retrieval |
| `tessera/engine.py` | Evidence-aware facade integrating retrieval with provenance |
| `tessera/evidence.py` | Evidence records, ledger, freshness and span/provenance helpers |
| `tessera/security.py` | Basic deterministic write-side hostile-pattern audit/sanitization |
| `tessera/conflict.py` | Existing compatibility conflict logic; future state/arbitration redesign is experimental |
| `tessera/models.py` | Domain models for memory/write paths |
| `tessera/cli.py` | Human CLI surface |
| `tessera/mcp_server.py` | MCP transport surface; parity hardening tracked in #68/#77 |
| `tessera/orchestrator.py` | Optional assisted retrieval/synthesis path; boundary tracked in #74 |
| `benchmarks/sanity/` | Deterministic project-agnostic regression evaluation |

## Implemented vs planned

Implemented Foundation:

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

Planned / experimental:

```text
#68 Engine / CLI / MCP contract parity
#12 incremental/idempotent indexing
#69 text ingestion coverage
#70 structural segmentation
#13 metadata doctor
#14/#25/#26 controlled relations/graph intelligence
#15 temporal model + state keys
#71/#72 harness adapters + instruction resolver
#73 source/memory revision history
#16 conflict/supersession
#27 Evidence Arbitration
#32 source authority + instruction precedence
#20 four-state evidence sufficiency/abstention
#18 LongMemEval
#28 rendering ablation
#17 adaptive retrieval
#74 core vs optional LLM orchestrator boundary
#19 evidence-aware memory admission
#21 experience learning / utility feedback
```

## Target architecture — only if experiments justify it

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
Authority / Scope / Instruction Resolution
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
