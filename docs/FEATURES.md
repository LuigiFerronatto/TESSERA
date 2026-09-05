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

## 8. Truthful deterministic write-gate contract

**Tracking:** Issue #92

### Persistence-format contract

Markdown (`md`) is the only canonical writable format. The Engine and MCP
reject every other `persist_format` value before sanitization, warnings,
timestamps, source writes, registry/graph changes, index rebuilds, or Evidence
Ledger changes. This keeps every acknowledged write discoverable by the current
Markdown source pipeline. Arbitrary JSON persistence/ingestion is not supported.

The canonical `write_memory_note_result()` path instantiates
`WriteGatingEngine` and runs:

```python
evaluate(content, tags)
```

before persisting the memory. It returns threat detection, actual content
change, admission, stable reasons, exact UTF-8 SHA-256 hashes, and whether
persistence occurred. The legacy filepath-returning method remains compatible
for accepted writes and raises with the canonical result for reject/review.

Conceptually:

```text
candidate memory
   ↓
known-pattern / suspicious-tag detection
   ↓
optional deterministic transformation
   ↓
accept | accept_sanitized | reject | review
   ↓
admission finalized before mutation
   ├─ reject/review → no canonical persistence/index side effects
   └─ accepted → atomic Markdown persistence + truthful metadata
```

Safe unchanged text has `sanitized=false`. Direct known hostile instructions
are rejected because the current deterministic policy cannot prove the full
logical payload safe. Quoted/documentary examples and suspicious-tag-only
ambiguity are review-only and are not written to the canonical corpus.
`accept_sanitized` remains in the schema but is constructable only for the
versioned complete whole-content transformation; the current evaluator does
not emit it.

Before gate evaluation, a canonical path validator requires a non-empty,
portable, forward-slash logical ID whose resolved `.md` destination is a strict
descendant of the resolved storage root. Absolute, drive/UNC, dot-segment,
non-canonical separator, reserved-name, case-alias, NUL, trailing-separator and
existing symlink escape forms are rejected without mutation.

### Important boundary

This is a **small deterministic known-pattern gate**, not comprehensive semantic
prompt-injection protection or the full future memory-admission system.

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
Engine/CLI/MCP direct-query parity           #68 implemented
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
core vs optional LLM boundary                #74 ADR accepted; migration follows
evidence-aware memory admission              #19
experience learning                           #21
```

## Deterministic core and optional assisted behavior

The binding contract is
[`ADR 0001`](adr/0001-core-vs-optional-llm-boundary.md).

**CURRENT:** Python Engine retrieval, CLI `query`, and MCP
`query_memories()` are deterministic and return the same lossless structured
evidence contract. They do not call a provider or inspect credentials.

**CURRENT:** `TesseraOrchestrator`, `TesseraTaskHook`, CLI `start`, assisted
episode decomposition, and MCP assisted tools are legacy optional LLM surfaces.
They are available only with an application-provided callable or an explicitly
selected deprecated compatibility adapter; no provider resolves implicitly.
They are not the basic retrieval contract and do not own the consuming agent's
final answer. Episode decomposition treats a valid `[]` as assisted success;
expected provider, parse or schema failure uses a separately labelled,
deterministic offline fallback whose candidates still require the canonical
write gate.

**TARGET:** planners, context consolidation, readers, and benchmark judges are
explicitly selected adapters outside the core. The O0–O4 modes in the ADR are
future-facing contracts, not an implemented feature list.

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
