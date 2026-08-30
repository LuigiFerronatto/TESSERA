# TESSERA — Retrieval Output Contract

> This document describes the structured result returned by the **current** `TesseraEngine.retrieve_context()` implementation. It is a runtime contract reference, not a proposal for future arbitration/temporal fields.

## Executive takeaway

TESSERA does not return only a string. Each retrieval hit is an evidence-rich object containing identity, ranking information, source navigation, query-aware evidence, full memory content and provenance when Canonical Metadata is available.

The human CLI may render these fields differently, but the semantic result object is the source contract.

## Em linguagem simples

When an agent asks TESSERA a question, the useful answer is not only:

```text
"here is some text"
```

It is closer to:

```text
which memory?
why did it rank here?
which part is relevant?
where did it come from?
which source version?
which other memories are directly connected?
what is the original full content?
```

The consuming agent can then decide how to reason with that evidence.

---

# Current result shape

A current retrieval hit can contain:

```yaml
id: project/charter

type: factual
filepath: /.../project/charter.md
filename: charter.md

score: 0.4308

score_explain:
  lexical_tfidf: 0.41
  lexical_overlap: 0.50
  lexical_score: 0.44
  title: 0.25
  metadata: 0.25
  raw_pagerank: 0.08
  normalized_relations: 1.0
  relations_contribution: 0.10
  type_boost: 1.0
  recency_boost: 1.0

relevant_evidence: "The project exists to provide auditable memory for agents."

evidence_info:
  text: "The project exists to provide auditable memory for agents."
  score: 2.12
  strategy: paragraph_lexical

body: |
  The project exists to provide auditable memory for agents.

frontmatter: {...}
related_ids:
  - project/learning-process

provenance:
  schema_version: 1
  evidence_id: ev_...
  memory_id: project/charter
  source:
    document_id: doc_...
    path: project/charter.md
    document_hash: ...
    content_hash: ...
    format: markdown
  span:
    start_line: 1
    end_line: 8
  fingerprint: ...
  extraction:
    method: canonical_document
    inferred: false

evidence:
  schema_version: 1
  evidence_id: ev_...
  memory_id: project/charter
  source: {...}
  span:
    start_line: 5
    end_line: 5
  fingerprint: ...
  extraction:
    method: paragraph_lexical
    inferred: false
```

Exact numeric values above are illustrative. Field semantics below are based on current code.

---

# Core fields

| Field | Current meaning | Null / absence behavior |
|---|---|---|
| `id` | Stable knowledge/memory identity used by the indexed graph. | Expected on every normal memory hit. |
| `type` | Current retrieval node type such as `factual`, `preference`, `procedural_anchor`. | Expected on normal memory hits. |
| `filepath` | Current physical source path used by the indexed node. | May be absent/`None` for non-file-backed compatibility cases. |
| `filename` | Source filename convenience field. | May be absent/`None`. |
| `score` | Final query relevance score used for ordering. | Expected. Do not interpret as truth/confidence. |
| `score_explain` | Inspectable component signals used by current ranking. | Expected for current ranked memory results. |
| `relevant_evidence` | Query-specific paragraph selected by deterministic overlap logic. | `None` when no paragraph meets current support threshold. |
| `evidence_info` | Extraction strategy and paragraph-level overlap score for `relevant_evidence`. | `None` when `relevant_evidence` is `None`. |
| `body` | Original indexed memory body/content. | Preserved even when evidence is foregrounded. |
| `frontmatter` | Compatibility/frontmatter representation attached to the node. | Shape can vary by source schema. |
| `related_ids` | Direct graph-neighbor IDs that are themselves memory-node types. | Usually an empty list when none exist. |
| `provenance` | Document-level Evidence Ledger record for canonical-backed results. | `None` if the result has no Canonical Metadata. |
| `evidence` | Query-specific Evidence Ledger record for the selected evidence span. | `None` if there is no `relevant_evidence`; span can be null if exact occurrence cannot be proven. |

---

# Score semantics

`score` is **retrieval relevance**, not a universal trust score.

Current ranking combines signals such as:

```text
lexical TF-IDF
+ direct token overlap
+ title / ID relevance
+ metadata relevance
+ normalized PageRank / relation signal
× deterministic type boost
× optional recency boost
```

Current default recency weight is disabled.

Never infer from a high `score` that:

```text
memory is true
source is authoritative
relation is trustworthy
memory is current
agent should act on it
```

Those are separate future/current dimensions.

## `score_explain`

Current keys include:

```text
lexical_tfidf
lexical_overlap
lexical_score
title
metadata
raw_pagerank
normalized_relations
relations_contribution
type_boost
recency_boost
```

`lexical_score` is a diagnostic composite; the final ranking uses the configured individual TF-IDF and overlap weights.

`recency_boost` is a legacy-named debug field and should not be read as proof that recency changed the final score when recency weighting is disabled. A future explainability hardening may make raw/weight/applied values more explicit.

---

# Relevant evidence vs full memory

The contract intentionally preserves both:

```text
relevant_evidence
→ what this query appears to need from the memory

body
→ the original indexed memory content
```

This prevents a query-specific excerpt from replacing the source memory.

Current evidence extraction is deterministic and lexical. It does not claim semantic entailment.

If no paragraph has at least the required query-token support:

```yaml
relevant_evidence: null
evidence_info: null
evidence: null
```

A retrieval hit can still exist because candidate/ranking behavior and evidence sufficiency are separate concerns.

---

# Provenance vs query-specific evidence

`provenance` and `evidence` have related but different roles.

## `provenance`

Document-level evidence record derived from Canonical Metadata:

```text
which stable source document?
which exact source version?
which canonical source span?
```

## `evidence`

Query-specific record created only when `relevant_evidence` exists:

```text
which exact snippet supports this retrieval for this query?
where does that snippet occur in the source?
```

If the snippet occurs more than once and TESSERA cannot prove which occurrence was intended:

```yaml
span:
  start_line: null
  end_line: null
```

TESSERA prefers explicit uncertainty to fabricated precision.

---

# Evidence record contract

Evidence records currently include:

```yaml
schema_version: 1
evidence_id: ev_...
memory_id: ...
source:
  document_id: ...
  path: ...
  document_hash: ...
  content_hash: ...
  format: ...
span:
  start_line: integer | null
  end_line: integer | null
fingerprint: sha256...
extraction:
  method: canonical_document | paragraph_lexical | ...
  inferred: boolean
```

Important identity rule:

```text
memory ID          = persistent knowledge identity
source document ID = persistent source-document identity
path               = current location
hashes             = source/content version
Evidence ID         = source-version/span-aware evidence identity
```

---

# Relations in the current contract

Today, `related_ids` exposes direct memory neighbors. Relation reliability is not yet first-class in the retrieval result.

Future Test Cards deliberately separate:

```text
relation_type       # what the edge means
relation_origin     # where it came from
relation_confidence # how strongly the edge itself is trusted
query_relevance     # whether traversing it helps this query
```

See #14, #25 and #26. Those future fields must not be documented as current runtime output until implemented.

---

# Human CLI vs machine-facing semantics

The human CLI is a presentation surface. Rich/plain rendering may choose labels, panels and formatting.

The semantic contract is the Python result returned from:

```python
engine.retrieve_context(query_text, top_n=...)
```

Current CLI text should therefore not be parsed as a stable machine protocol when the same data is available through the structured engine result.

Contract parity across Python, CLI and MCP is tracked explicitly in #68. Renderers/transports may differ; semantic evidence must not disappear silently.

---

# What is NOT in the current result contract

These are roadmap concepts, not current guaranteed fields:

```text
relation confidence / validation          #26
temporal validity / state keys             #15
source authority / instruction precedence  #32/#72
Evidence Arbitration resolution            #27
four-state evidence_status                 #20
adaptive retrieval strategy                #17
utility feedback                            #21
```

Future additions should be backward-compatible where practical or explicitly versioned.

---

# Consumer guidance

A consuming agent should conceptually treat a hit as:

```text
relevance signal
+ evidence
+ provenance
+ navigation
+ original content
```

not as:

```text
final answer
or
truth score
```

For a high-stakes or conflicting future scenario, the agent should use provenance/assessment/arbitration signals once those Test Cards exist rather than treating `score` as authority.

---

# Known limitations of the current contract

- Candidate generation remains lexical/TF-IDF seeded.
- Query-aware evidence uses lexical paragraph overlap, not entailment.
- A nonsense query can produce no retrieval candidates, or low-quality candidates depending on lexical seed behavior; `relevant_evidence=None` is the current evidence guard, not the full future abstention system.
- `recency_boost` debug naming is less explicit than the desired raw/weight/applied model.
- `frontmatter` remains a compatibility surface; canonical semantics should be preferred internally.
- Human CLI formatting is not a formal machine serialization protocol.
- MCP currently exposes a reduced subset of the engine result; #68 exists to close that transport-parity gap.

These are documented so future PRs can improve them without pretending the current contract is stronger than it is.
