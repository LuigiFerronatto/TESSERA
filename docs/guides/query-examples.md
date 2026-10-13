# TESSERA — Query Examples

> These examples separate **current behavior/baselines** from **future target contracts**. Do not read future examples as implemented features.

## Executive takeaway

A TESSERA query should return enough information for an agent to answer three questions:

1. **What memory/evidence did you find?**
2. **Why did it rank here?**
3. **Where did it come from?**

The consuming agent remains responsible for reasoning and answering.

---

# Current retrieval result shape

Current retrieval semantics include fields in these categories:

```text
identity
ranking
source/navigation
relations
relevant evidence
full memory
score explanation
provenance/evidence record
```

A representative result looks conceptually like:

```yaml
id: project/charter
type: factual
score: 0.43

filepath: /.../project/charter.md
filename: charter.md

related_ids:
  - project/learning-process

relevant_evidence: >
  The project exists to provide an auditable memory layer for agents.

evidence_info:
  strategy: paragraph_lexical
  score: 0.7

score_explain:
  lexical_tfidf: 0.42
  lexical_overlap: 0.50
  title: 0.25
  metadata: 0.25
  raw_pagerank: 0.08
  normalized_relations: 1.0
  type_boost: 1.0

provenance:
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
    end_line: 12

evidence:
  evidence_id: ev_...
  extraction:
    method: paragraph_lexical
    inferred: false
  span:
    start_line: 7
    end_line: 8

body: >
  Full original memory body...
```

Not every field is guaranteed to be non-null. In particular, `relevant_evidence`, query-specific `evidence` or an exact span can be absent when the system cannot prove them.

---

# Example 1 — direct purpose query

```bash
tessera query ./memories "qual o propósito do projeto?"
```

Expected current behavior:

```text
query
  ↓
purpose/charter memory ranks highly
  ↓
query-relevant paragraph is foregrounded
  ↓
full body remains available
  ↓
source/provenance remain inspectable
```

The agent is not forced to trust a score alone. It can inspect both evidence and source.

---

# Example 2 — paraphrase robustness

```bash
tessera query ./memories "pq esse projeto existe?"
```

The deterministic sanity fixture contains both direct and colloquial purpose queries so paraphrase behavior remains observable.

We do **not** want code like:

```python
if query == "pq esse projeto existe?":
    boost("project/charter")
```

Future semantic/adaptive retrieval should improve paraphrase recall through generalizable ablations (#17/#18), not by overfitting one sentence.

---

# Example 3 — query-aware evidence

Suppose a memory contains several paragraphs:

```text
The project supports multiple execution environments.

Verified learnings are persisted as source-backed memory and retrieved later.

The repository also publishes periodic research notes.
```

For:

```text
como o projeto aprende?
```

TESSERA should foreground the paragraph that overlaps with the learning/memory question rather than blindly returning the first paragraph.

If no paragraph reaches the evidence heuristic threshold:

```yaml
relevant_evidence: null
evidence: null
```

This is preferable to fabricating an evidence span.

---

# Example 4 — provenance after a file move

Before:

```text
identity.id:        project/deployment-policy
source.document_id: doc_970ff13b932d
source.path:        project/deployment-policy.md
content_hash:       e8a6...
```

After rename/move:

```text
identity.id:        project/deployment-policy
source.document_id: doc_970ff13b932d
source.path:        archive/deployment-policy.md
content_hash:       e8a6...
```

The knowledge identity and source-document identity survive the move; only location changes.

---

# Example 5 — source content changed

After editing the moved file:

```text
identity.id:        SAME
source.document_id: SAME
source.path:        SAME
content_hash:       CHANGED
```

Existing evidence records can therefore be checked for freshness.

Possible freshness states include:

```text
fresh
metadata_changed
content_changed
missing_source
```

---

# Example 6 — harness instruction indexing

Source:

```text
CLAUDE.md
AGENTS.md
project.SKILL.md
```

These documents are indexable text, but they are not forced into semantic memory drawers.

Conceptual canonical form:

```yaml
document_type: harness_instructions
kind: instruction
drawer: null
scope: ./**
```

Future #71/#72/#32 experiments will test harness adapters, applicability, authority and scope precedence. Those behaviors are **not** implemented today.

---

# Example 7 — what the agent should receive today

```text
TESSERA RESULT
│
├── memory identity
├── ranking score/explanation
├── relevant evidence
├── original body
├── related IDs
└── provenance/evidence record

AGENT
│
├── inspect evidence
├── navigate source if necessary
├── compare multiple results
└── decide/answer
```

TESSERA is not the final answer generator in this contract.

---

# Future target example — NOT IMPLEMENTED

Query:

```text
qual runtime o projeto usa atualmente?
```

Possible future target:

```yaml
results:
  - memory: project/runtime/current
    relevance: 0.91
    evidence: "The project now uses a multi-runtime execution strategy."

    provenance:
      document_id: doc_182
      span: [31, 37]

    temporal:
      status: current

    relations:
      - type: supersedes
        target: project/runtime/legacy
        confidence: 0.98
        origin: derived

resolution:
  status: resolved
  preferred: ev_103
  reasons:
    - newer_validity
    - explicit_supersession

evidence_status:
  status: sufficient
```

This requires future Test Cards including temporal state, conflict/supersession, relation confidence, Evidence Arbitration and evidence sufficiency. It is included to make the architectural direction understandable without confusing it with the current Foundation.

---

# Current sanity evaluation

The CI sanity dataset is intentionally small, synthetic and deterministic. It covers direct retrieval, paraphrase robustness, procedural retrieval, an operational gotcha and missing evidence.

Use it to detect regressions, not to claim competitive superiority.

Competitive/LongMemEval evaluation belongs to #18.
