# TESSERA — Implemented Features

> This catalog describes capabilities that exist in the current Foundation. Planned/Test Card work is listed separately and is **not** presented as implemented.

## Executive takeaway

TESSERA already provides the core substrate required for auditable agent memory: canonical text normalization, stable identities, explainable retrieval, query-relevant evidence, graph-linked context and provenance.

The current Foundation is intentionally conservative. Temporal-state reasoning, confidence-aware relations, source arbitration and abstention remain experiments in the roadmap.

---

## 1. Canonical text ingestion

**Tracking:** Issue #9 / PR #3

### Why it exists
Projects rarely have one perfect Markdown schema. Some files have complete frontmatter, some partial metadata and some none at all.

### What TESSERA does
TESSERA normalizes supported text documents into Canonical Metadata while preserving the source file as the source of truth.

It understands memory documents as well as non-memory knowledge such as harness instructions and project context.

Examples:

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

### Important invariant
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

This allows a file to move without becoming a new source document and allows content to change without losing conceptual identity.

### Expected behavior

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

TESSERA currently preserves explicit/local relations found in supported metadata and links and represents them in its graph.

The graph is already used as a structural signal in retrieval.

### What is **not** implemented yet

The following are future Test Cards, not current capabilities:

- typed relation reliability/confidence (#26);
- query-aware graph expansion budget (#25);
- deep graph traversal;
- automatic causal relation inference.

---

## 4. Explainable multi-signal retrieval ranking

**Tracking:** Issue #8 / PR #2

TESSERA no longer relies on raw PageRank alone.

The current ranking combines inspectable signals such as:

- TF-IDF lexical similarity;
- direct token overlap;
- title/ID relevance;
- metadata relevance;
- normalized graph/PageRank signal;
- deterministic type/intent boost;
- optional recency behavior, disabled by default in the Foundation.

The purpose is not to claim full semantic retrieval. The purpose is to make ranking behavior measurable and debuggable.

### Known limitation

The paraphrase:

```text
pq o LAO existe?
```

can still place the intended `lao/charter` result at #2 instead of #1. This remains visible in the sanity baseline rather than being hidden by query-specific tuning.

---

## 5. Query-aware Relevant Evidence

**Tracking:** Issue #8 / PR #2

Instead of only returning an entire memory, TESSERA selects a paragraph/snippet that overlaps with the current query when there is sufficient lexical evidence.

Conceptually:

```text
memory
├── relevant_evidence   ← foregrounded for this query
└── full body           ← still preserved
```

If no paragraph has enough support, `relevant_evidence` remains `None` instead of falling back to an arbitrary first paragraph.

That behavior is an early foundation for future Evidence Sufficiency/Abstention (#20), but the four-state sufficiency classifier itself is not implemented yet.

---

## 6. Evidence Ledger and provenance

**Tracking:** Issue #11 / PR #6

Every canonical indexed memory can be mapped to deterministic evidence records.

A provenance record includes:

```yaml
evidence_id: ev_...
memory_id: mem_...
source:
  document_id: doc_...
  path: ...
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

### Auditability rule

If the query-specific evidence text appears more than once and the exact occurrence cannot be proven, TESSERA returns a null span instead of guessing.

### Freshness states

The Evidence Ledger can distinguish source freshness conditions such as:

```text
fresh
metadata_changed
content_changed
missing_source
```

### Important boundary

The ledger is provenance, not arbitration.

Future authority, confidence, temporal validity and preferred-source decisions should live above this immutable/rebuildable substrate.

---

## 7. Source-version-aware evidence IDs

**Tracking:** Issue #11 / PR #6

Evidence IDs include the source document version/hash and span, so a source change produces a new evidence version while the memory/document identity can remain stable.

This preserves the difference between:

```text
same entity
new source version
```

and:

```text
new entity
```

---

## 8. Deterministic CI and sanity evaluation

**Tracking:** Issue #10 / PR #4

TESSERA CI runs:

```text
Python 3.9 tests
Python 3.12 tests
CLI smoke
sanity retrieval evaluation
```

The sanity evaluator measures:

- Hit@1;
- Hit@3;
- Hit@5;
- MRR;
- evidence hit rate;
- latency;
- returned context size;
- missing-evidence behavior.

Current regression baseline recorded by the project:

```text
Hit@1          75%
Hit@3         100%
Hit@5         100%
MRR           0.875
Evidence hit  100%
```

This is a regression guard, **not** a competitive benchmark.

LongMemEval is tracked separately in #18.

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
```

Still experimental/planned:

```text
incremental indexing                 #12
metadata doctor                      #13
query-aware graph expansion          #25
relation confidence                  #26
temporal state / state keys          #15
conflict resolution                  #16
evidence/source arbitration          #27
authority + instruction precedence   #32
4-state sufficiency / abstention      #20
LongMemEval                           #18
renderer ablation                     #28
adaptive retrieval                    #17
write gating                          #19
experience learning                   #21
```

---

# Why the Foundation matters

The value of these features is less visible than a final-answer demo, but they create the substrate for every later capability:

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
