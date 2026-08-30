# TESSERA — Paper Notes

> Format: **what the paper says → what TESSERA learns → what we test → what is implemented**.

This document intentionally separates external research claims from TESSERA decisions.

---

## QUMem — Personalized Memory for Query-Conditioned User-State Inference

Source: https://arxiv.org/abs/2608.16168  
Published: 2026-08-17

### What the paper says

QUMem argues that fixed session/token boundaries and monolithic memories can mix unrelated information or bind together facts/preferences/insights that should be independently retrievable. It decomposes episodes into factual, preference and transferable-insight memories while preserving temporal/source evidence, then performs query-conditioned retrieval/state inference.

### What TESSERA takes from it

The strongest architectural influence is the semantic separation:

```text
facts
preferences
insights
```

TESSERA preserves exactly those three semantic drawers.

### What TESSERA does differently

- harness/project/reference documents are not forced into those drawers;
- TESSERA does not require QUMem's sequential multi-agent inference pipeline for every query;
- the consuming agent remains responsible for final cognition.

### Status

```text
three drawers            IMPLEMENTED
query-conditioned state  PLANNED / #17 #20
```

---

## A-MEM — Agentic Memory for LLM Agents

Source: https://arxiv.org/abs/2502.12110  
Published: 2025-02-17

### What the paper says

A-MEM uses Zettelkasten-inspired structured notes and dynamically creates links among memories. New memories can trigger changes to contextual representations/attributes of older memories.

### What TESSERA learns

- atomic notes + explicit links can form a useful evolving memory substrate;
- evolution needs lineage/provenance so an adaptive system does not erase why an older memory existed.

### TESSERA caution

TESSERA does not want unrestricted agentic self-editing of historical memory. Future evolution should preserve `derived_from`, `supersedes`, source evidence and deterministic/auditable updates.

### Status

```text
atomic/source-backed records    FOUNDATION
explicit relation foundation    IMPLEMENTED
adaptive evolution              LATER / #19 #21
```

---

## LongMemEval

Source: https://arxiv.org/abs/2410.10813  
Published: 2024-10-14

### What the paper says

LongMemEval evaluates five long-term memory abilities:

```text
information extraction
multi-session reasoning
temporal reasoning
knowledge updates
abstention
```

It also frames memory performance as a pipeline spanning indexing, retrieval and reading.

### What TESSERA learns

Benchmarking only retrieval IDs is insufficient. We need to distinguish:

```text
representation
retrieval
reader/rendering
downstream answer behavior
```

### Test Card

#18 LongMemEval V1/V2 adapters + ablations.

### Status

Planned. Current sanity metrics are internal regression checks only.

---

## GraphMemix — Query-Aware Evidence Forests

Source: https://arxiv.org/abs/2608.26983  
Published: 2026-08-27

### What the paper says

GraphMemix builds query-aware candidate graphs and optimizes an evidence forest under a maximum evidence budget. It distinguishes direct memory support from relation activation/reliability cost to reduce redundant/conflicting context while recovering complementary low-similarity evidence.

### TESSERA insight

The key lesson is not “use more graph”. It is:

```text
relation exists
≠ relation should be traversed for this query
```

### Derived experiment

#25 compares:

```text
A0 no graph expansion
A1 indiscriminate 1-hop
A2 query-aware 1-hop
A3 query-aware + relation confidence + budget
```

Metrics include quality, tokens, nodes visited and latency.

### Status

Planned experiment. Do not describe TESSERA as having evidence-forest optimization today.

---

## CaSKG — Counterfactual-Causal Skill Graphs

Source: https://arxiv.org/abs/2608.25500  
Published: 2026-08-26

### What the research signal says

The project research review highlights a central lesson: graph retrieval is only useful when the edges themselves are reliable, and edge candidates can be validated/calibrated before expansion.

### TESSERA insight

Relations need an auditable contract:

```text
relation_type
→ what does the edge mean?

relation_origin
→ where did it come from?

relation_confidence
→ how strongly do we believe the edge is correct?

query_relevance
→ is it useful for this query?
```

These dimensions should not collapse into one score.

### Candidate contract

```yaml
relations:
  - type: supersedes
    target: mem_102
    origin:
      kind: explicit
      method: frontmatter
    confidence: 0.96
    evidence:
      - evidence_id: ev_...
    validation:
      status: validated
      method: deterministic
```

### Derived experiment

#26 Relation Confidence / Edge Validation.

### Status

Planned. Current TESSERA relations do not yet expose this complete contract.

---

## MemToC — Memory-Tool Conflict Resolution

Source: https://arxiv.org/abs/2608.26295  
Published: 2026-08-26

### What the paper says

MemToC creates controlled cases where model memory and tool results can independently be correct or wrong. It reports strong over-reliance on tool returns in several instruction-tuned models and observes that some arbitration improvements hurt abstention.

### TESSERA insight

Conflict is not only:

```text
memory old vs memory new
```

It can be:

```text
MEMORY   says A
TOOL     says B
DOCUMENT says C
```

TESSERA should not silently hide that disagreement.

### Architecture derived from the paper

```text
Evidence Ledger
→ immutable provenance

Evidence Assessment
→ authority / confidence / temporal validity

Evidence Arbitration
→ conflict / preferred evidence / reasons / unresolved candidates

Evidence Status
→ sufficient / insufficient / conflicting / ambiguous
```

### Derived Test Cards

- #27 Source/Evidence Arbitration
- #20 Evidence Sufficiency/Abstention
- #32 Source Authority/Scope/Instruction Precedence

### Status

Planned experiments. Evidence Ledger is implemented; arbitration is not.

---

## RENDER — Controlling Reader-Facing Evidence

Source: https://arxiv.org/abs/2608.23568  
Original submission: 2026-06-05

### What the paper says

RENDER holds underlying information constant while varying the reader-facing artifact. It reports large downstream differences across memory-style renderings, showing that evaluation can confound retrieval/memory quality with presentation quality.

### TESSERA insight

We must benchmark:

```text
same retrieval
same evidence
same reader
same prompt policy

ONLY renderer changes
```

### Planned renderer ablation

```text
RAW
→ full memory/source

EVIDENCE
→ relevant span + provenance

STRUCTURED
→ relevant span + provenance + relations + temporal/conflict metadata
```

### Derived Test Card

#28, connected to LongMemEval #18.

### Status

Planned benchmark control. Current TESSERA already has evidence-rich results, but their downstream rendering value has not yet been isolated experimentally.

---

# Product papers used as architecture references

## Mem0 paper

Source: https://arxiv.org/abs/2504.19413

Relevant ideas:

- dynamic extraction/consolidation of salient conversational information;
- graph variant for relational context;
- explicit attention to latency/token cost.

TESSERA use:

- production-memory baseline;
- compare extraction-based atomic memory against strong raw/verbatim and hybrid baselines rather than assuming atomic representation wins.

---

## Zep / Graphiti paper

Source: https://arxiv.org/abs/2501.13956

Relevant ideas:

- temporal knowledge graph for changing facts/relationships;
- integration of conversational and structured business data;
- temporal/context retrieval as a first-class concern.

TESSERA use:

- major reference for temporal validity, incremental graphs and historical fact representation;
- benchmark against TESSERA's evidence-first/text-first approach once #15/#16 exist.

---

# How to add a paper note

Use this template:

```markdown
## Paper title
Source:
Published:

### What the paper says
Primary-source summary only.

### TESSERA interpretation
What architectural lesson we infer.

### Derived Test Card
Issue(s), hypothesis and metrics.

### Difference / caution
What we intentionally do not copy or what is not directly comparable.

### Status
Implemented / Experimental / Planned / Dropped / Deferred.
```

If a paper does not create a testable hypothesis, it may remain only in `REFERENCES.md`.
