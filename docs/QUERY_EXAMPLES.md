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

The exact Python result object may evolve, but current retrieval semantics include fields in these categories:

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

A representative current result looks conceptually like:

```yaml
id: lao/charter
type: factual
score: 0.43

filepath: /.../lao/charter.md
filename: charter.md

related_ids:
  - lao/learning-process

relevant_evidence: >
  O propósito do LAO é ...

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
  memory_id: lao/charter
  source:
    document_id: doc_...
    path: lao/charter.md
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
tessera query ./memories "qual o propósito do LAO?"
```

This kind of query has strong lexical support for a charter/purpose memory.

The expected behavior is:

```text
query
  ↓
charter/purpose memory ranks highly
  ↓
query-relevant paragraph is foregrounded
  ↓
full body remains available
  ↓
source/provenance remain inspectable
```

The important point is that the agent is not forced to trust a score alone. It can inspect both evidence and source.

---

# Example 2 — known paraphrase limitation

```bash
tessera query ./memories "pq o LAO existe?"
```

The current deterministic sanity fixture records a known limitation: the gold charter memory can appear at **#2 instead of #1** because the current retrieval path remains strongly lexical.

This is intentional as a benchmark baseline.

We do **not** want code like:

```python
if query == "pq o LAO existe?":
    boost("lao/charter")
```

Future semantic/adaptive retrieval should improve paraphrase recall through generalizable ablations (#17/#18), not by overfitting this query.

---

# Example 3 — query-aware evidence

Suppose a memory contains several paragraphs:

```text
The LAO experiments with multiple runtimes.

The current architecture persists learnings in TESSERA.

The team also publishes a weekly AI radar.
```

For:

```text
como o LAO aprende?
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
identity.id:        learnings_old
source.document_id: doc_970ff13b932d
source.path:        learnings_old.md
content_hash:       e8a6...
```

After rename/move:

```text
identity.id:        learnings_old
source.document_id: doc_970ff13b932d
source.path:        sub/learnings_moved.md
content_hash:       e8a6...
```

The knowledge identity and source-document identity survive the move; only location changes.

That means Evidence Ledger records can continue to refer to the same source entity rather than treating a rename as new knowledge.

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

The future instruction-precedence experiment (#32) will test authority/scope resolution. That precedence behavior is **not** implemented today.

---

# Example 7 — what the agent should receive today

A consuming agent can use current TESSERA results approximately like this:

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

The following demonstrates where the roadmap is heading, not current output.

Query:

```text
qual runtime o LAO usa atualmente?
```

Future target:

```yaml
results:
  - memory: M3
    relevance: 0.91
    evidence: "LAO agora utiliza arquitetura multi-runtime..."

    provenance:
      document_id: doc_182
      span: [31, 37]

    temporal:
      status: current

    relations:
      - type: supersedes
        target: M1
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

This requires future Test Cards:

```text
#15 temporal model/state keys
#16 conflict/supersession
#26 relation confidence
#27 evidence arbitration
#20 evidence sufficiency
```

It is included here to make the architectural direction understandable without confusing it with the current Foundation.

---

# Current sanity baseline

The CI sanity dataset is intentionally small and deterministic.

Current project baseline:

```text
Hit@1          75%
Hit@3         100%
Hit@5         100%
MRR           0.875
Evidence hit  100%
```

Use it to detect regressions, not to claim competitive superiority.

Competitive/LongMemEval evaluation belongs to #18.
