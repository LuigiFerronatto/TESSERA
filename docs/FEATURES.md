# TESSERA — Implemented Features

> This catalog describes capabilities that exist in the current Foundation. Planned/Test Card work is listed separately and is **not** presented as implemented.

## Executive takeaway

TESSERA already provides the core substrate required for auditable agent memory: canonical text normalization, stable identities, explainable retrieval, query-relevant evidence, graph-linked context, provenance, and a basic deterministic write-side sanitization gate.

The current Foundation is intentionally conservative. Incremental indexing, evidence-aware memory admission, temporal-state reasoning, confidence-aware relations, source arbitration and abstention remain experiments in the roadmap.

---

## 1. Canonical text ingestion

**Tracking:** Issue #9 / PR #3

Projects rarely have one perfect Markdown schema. Some files have complete frontmatter, some partial metadata and some none at all.

TESSERA normalizes supported text documents into Canonical Metadata while preserving the source file as the source of truth. It understands memory documents as well as non-memory knowledge such as harness instructions and project context.

```yaml
# semantic memory
drawer: facts
kind: factual
```

```yaml
# harness knowledge
document_type: harness_instructions
kind: instruction
drawer: null
```

There are exactly three semantic drawers:

```text
facts
preferences
insights
```

`document_type`, `scope`, `authority`, temporal state and relations are facets, not additional drawers.

---

## 2. Stable knowledge and source identity

**Tracking:** Issue #9 / PR #3

TESSERA separates:

```text
identity.id
source.document_id
source.path
document_hash / content_hash
```

Expected behavior:

```text
rename / move
identity.id        SAME
source.document_id SAME
source.path        CHANGED
content_hash       SAME
```

```text
content edit
identity.id        SAME
source.document_id SAME
source.path        SAME
content_hash       CHANGED
```

This is foundational for provenance, incremental indexing and later temporal reasoning.

---

## 3. Explicit relation parsing and graph representation

**Tracking:** Issue #9 / PR #3

TESSERA currently preserves explicit/local relations found in supported metadata and links and represents them in its graph. The graph already participates as a structural retrieval signal.

Not implemented yet:

- typed relation reliability/confidence (#26);
- query-aware graph expansion budget (#25);
- controlled relation ablations (#14);
- automatic causal relation inference.

---

## 4. Explainable multi-signal retrieval ranking

**Tracking:** Issue #8 / PR #2

Current ranking combines inspectable signals such as:

- TF-IDF lexical similarity;
- direct token overlap;
- title/ID relevance;
- metadata relevance;
- normalized graph/PageRank signal;
- deterministic type/intent boost;
- optional recency behavior, disabled by default in the Foundation.

The purpose is not to claim full semantic retrieval. The purpose is to make ranking behavior measurable and debuggable.

The project-agnostic sanity fixture includes both direct and colloquial purpose queries. A paraphrase can still rank the intended charter memory below another relevant candidate because the current retrieval path remains strongly lexical. That limitation is kept visible rather than hidden by query-specific tuning.

---

## 5. Query-aware Relevant Evidence

**Tracking:** Issue #8 / PR #2

Instead of only returning an entire memory, TESSERA selects a paragraph/snippet that overlaps with the current query when there is sufficient lexical evidence.

```text
memory
├── relevant_evidence   ← foregrounded for this query
└── full body           ← still preserved
```

If no paragraph has enough support, `relevant_evidence` remains `None` instead of falling back to an arbitrary first paragraph.

That behavior is an early foundation for future Evidence Sufficiency/Abstention (#20), but the four-state classifier itself is not implemented yet.

---

## 6. Evidence Ledger and provenance

**Tracking:** Issue #11 / PR #6

Every canonical indexed memory can be mapped to deterministic evidence records.

```yaml
evidence_id: ev_...
memory_id: project/charter
source:
  document_id: doc_...
  path: project/charter.md
  document_hash: ...
  content_hash: ...
  format: markdown
span:
  start_line: 31
  end_line: 37
extraction:
  method: paragraph_lexical
  inferred: false
```

If query-specific evidence appears more than once and the exact occurrence cannot be proven, TESSERA returns a null span instead of guessing.

Freshness states include:

```text
fresh
metadata_changed
content_changed
missing_source
```

The ledger is provenance, not arbitration. Future authority, confidence, temporal validity and preferred-source decisions live above this immutable/rebuildable substrate if their Test Cards succeed.

---

## 7. Source-version-aware evidence IDs

**Tracking:** Issue #11 / PR #6

Evidence IDs include the source document version/hash and span, so a source change produces a new evidence version while memory/document identity can remain stable.

```text
same entity
new source version
```

is distinct from:

```text
new entity
```

---

## 8. Basic heuristic write-side sanitization

**Tracking:** existing write path; documentation correction Issue #54

### Persistence-format contract

Markdown (`md`) is the only canonical writable format. The Engine and MCP
reject every other `persist_format` value before sanitization, warnings,
timestamps, source writes, registry/graph changes, index rebuilds, or Evidence
Ledger changes. This keeps every acknowledged write discoverable by the current
Markdown source pipeline. Arbitrary JSON persistence/ingestion is not supported.

The current `write_memory_note()` path instantiates `WriteGatingEngine` and runs:

```python
audit_and_sanitize(content, tags)
```

before persisting the memory.

Today this gate performs deterministic checks for a small known set of hostile-instruction patterns and suspicious tags, and applies deterministic redaction for matched patterns.

Conceptually:

```text
candidate memory
   ↓
known-pattern / suspicious-tag audit
   ↓
optional redaction
   ↓
MemoryFrontmatter security metadata
   ↓
Markdown persistence
```

### Important boundary

This is a **basic security/sanitization gate**, not the full future memory-admission system.

It does not yet decide comprehensively:

```text
is this genuinely new?
is it duplicated?
is it useful/stable enough to persist?
is it sufficiently supported by evidence?
should it become durable memory at all?
```

Those broader questions are the planned #19 **evidence-aware memory admission / advanced write gating** Test Card.

---

## 9. Deterministic CI and sanity evaluation

**Tracking:** Issue #10 / PR #4

TESSERA CI runs:

```text
Python 3.9 tests
Python 3.12 tests
CLI smoke
sanity retrieval evaluation
```

The sanity evaluator measures Hit@1/3/5, MRR, evidence hit rate, latency, returned context size and missing-evidence behavior.

The public fixture is synthetic and project-agnostic. Its metrics are regression guards, **not** competitive benchmark claims. LongMemEval is tracked separately in #18.

---

# Current Foundation boundary

Implemented:

```text
source text
→ canonical metadata
→ stable identities
→ explicit graph links
→ index
→ explainable ranking
→ relevant evidence
→ provenance/evidence ledger
→ structured retrieval result

write_memory_note
→ validate `persist_format == "md"`
→ basic heuristic audit/sanitization
→ Markdown persistence
```

Still experimental/planned:

```text
Engine/CLI/MCP contract parity              #68
incremental indexing                         #12
plain-text ingestion                         #69
structural segmentation                      #70
metadata doctor                              #13
query-aware graph expansion                  #25
relation confidence                          #26
temporal state / state keys                  #15
harness adapters / instruction resolver      #71/#72
authority + instruction precedence           #32
source revision history                      #73
conflict resolution                          #16
evidence/source arbitration                  #27
4-state sufficiency / abstention              #20
LongMemEval                                   #18
renderer ablation                             #28
adaptive retrieval                            #17
core vs optional LLM orchestrator boundary   #74
evidence-aware memory admission              #19
experience learning                           #21
```

---

# Why the Foundation matters

These features create the substrate for every later capability:

```text
stable identity
     ↓
provenance
     ↓
reliable incremental state
     ↓
temporal reasoning / relations
     ↓
conflict representation
     ↓
sufficiency / abstention
```

TESSERA is deliberately building this chain in order instead of adding high-level intelligence on top of unstable source identity.
