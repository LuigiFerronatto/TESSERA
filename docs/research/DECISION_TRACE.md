# TESSERA — Research → Decision Trace

This document answers:

> **Which external idea changed the TESSERA roadmap, and how?**

It is not a changelog. It is a rationale map from research signal to hypothesis/Test Card.

---

## Three semantic drawers

### Signal
QUMem — https://arxiv.org/abs/2608.16168

### External idea
Facts, preferences and transferable insights should be independently retrievable rather than bound into one monolithic memory.

### TESSERA decision
Preserve exactly three semantic drawers:

```text
facts
preferences
insights
```

### Important adaptation
Non-memory text such as harness instructions is not forced into those drawers.

### Status
Implemented through Canonical Metadata / #9.

---

## Stable source identity before provenance/temporal intelligence

### Signal
Internal architecture requirement reinforced by source-backed memory research and the need to audit evidence across file moves/edits.

### TESSERA decision
Separate:

```text
knowledge identity
source document identity
path
version hashes
```

### Why
Evidence → Source must remain valid after rename/move, and version changes must not imply a new conceptual entity.

### Status
Implemented #9, used by Evidence Ledger #11.

---

## Evidence Ledger before conflict/arbitration

### Signal
Need for source evidence in QUMem-like structured memory plus later source-conflict requirements highlighted by MemToC.

### TESSERA decision
Implement immutable/rebuildable provenance first:

```text
evidence_id
memory_id
source document
version hashes
span
```

Then build assessment/arbitration above it.

### Status
Evidence Ledger implemented #11. Arbitration planned #27.

---

## Do not add graph expansion just because a graph exists

### Signal
GraphMemix — https://arxiv.org/abs/2608.26983

### External idea
Query-specific evidence-graph construction under cost/budget can outperform naive similarity-only or indiscriminate graph context.

### TESSERA decision
Change the graph experiment from:

```text
graph vs no graph
```

to:

```text
no expansion
vs indiscriminate 1-hop
vs query-aware 1-hop
vs query-aware + confidence + budget
```

### Status
Test Cards #14/#25, planned.

---

## Relation existence is not relation reliability

### Signal
CaSKG — https://arxiv.org/abs/2608.25500

### External idea
Graph retrieval depends on reliable edges; validation/calibration can matter before expansion.

### TESSERA decision
Separate:

```text
relation_type
relation_origin
relation_confidence
query_relevance
```

and attach evidence/validation when available.

### Non-decision
Do **not** put relation confidence directly into default FINAL_SCORE.

### Status
#26 planned.

---

## Conflict resolution becomes Evidence Arbitration

### Signal
MemToC — https://arxiv.org/abs/2608.26295

### External idea
Tool and model/memory sources can independently be correct or wrong; source preference without correctness/abstention controls is unsafe.

### Previous TESSERA framing

```text
memory old
vs
memory new
→ supersession
```

### Revised framing

```text
memory
tool
document
runtime observation
→ explicit conflict set
→ deterministic preference only when justified
→ unresolved evidence remains visible
```

### Architectural separation

```text
Evidence Ledger
→ provenance

Evidence Assessment
→ authority/confidence/validity

Evidence Arbitration
→ preferred/reasons/unresolved
```

### Status
#16 expanded; #27 created; planned.

---

## Abstention becomes four-state evidence status

### Signal
MemToC's observation that arbitration improvements can hurt abstention.

### Previous framing

```text
sufficient / insufficient
```

### Revised TESSERA framing

```text
sufficient
insufficient
conflicting
ambiguous
```

### Control-flow intention

```text
sufficient   → continue
insufficient → search/expand
conflicting  → inspect provenance/arbitration
ambiguous    → verify/ask/tool call
```

### Status
#20 planned.

---

## Authority must be separate from confidence

### Signal
MemToC source arbitration + TESSERA harness/document scope requirements.

### TESSERA decision
Define authority as:

> How authoritative is this source for this subject/scope?

and keep it separate from:

```text
confidence
relevance
validity
```

### Example

```text
CLAUDE.md: "Use uv"
learning.md: "maybe use pip"
```

Precedence should eventually consider scope/document type/authority/validity rather than newest-wins.

### Status
#32 planned.

---

## Rendering must be benchmarked separately from retrieval

### Signal
RENDER — https://arxiv.org/abs/2608.23568

### External idea
The same underlying evidence can produce materially different downstream QA depending on reader-facing representation.

### TESSERA decision
LongMemEval must control rendering as a separate ablation:

```text
RAW
EVIDENCE
STRUCTURED
```

while holding retrieval/evidence/reader constant.

### Status
#28 linked to #18, planned.

---

## Keep a strong raw/verbatim baseline

### Signal
MemPalace official benchmark/repository — https://github.com/MemPalace/mempalace

### External idea/claim
The project reports strong LongMemEval retrieval recall using verbatim storage + semantic retrieval, challenging assumptions that extraction is always required.

### TESSERA decision
Do not benchmark Atomic TESSERA only against weak baselines.

#18 should include:

```text
Raw/verbatim
vs Atomic
same encoder
session-normalized evaluation
token-budget evaluation
same downstream reader
```

### Status
Planned #18.

---

## Treat temporal graph systems as a serious baseline

### Signal
Zep/Graphiti:

- https://arxiv.org/abs/2501.13956
- https://help.getzep.com/graphiti/getting-started/overview

### External idea
Temporal graph edges/facts can carry lifecycle/validity and update incrementally as events arrive.

### TESSERA decision
#15/#16 must prove that TESSERA's state-key/evidence approach is useful rather than assuming a lighter design is automatically better.

### Status
Planned.

---

# Decision rule for future research

A new paper/product should not automatically become a feature.

Use:

```text
SOURCE
  ↓
What does it actually claim/do?
  ↓
Does it expose a TESSERA gap or hypothesis?
  │
  ├─ NO → references only
  │
  └─ YES
       ↓
    Test Card
       ↓
    baseline + ablation + metrics
       ↓
    KEEP / ITERATE / DROP / DEFER
```

This is how TESSERA avoids paper-driven architecture drift.
