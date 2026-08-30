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

## LiveMem — Maintaining Memory State Continuity

Source: https://arxiv.org/abs/2608.02515  
Published: 2026-08-03

### What the paper says

LiveMem frames long-running inference as a state-continuity problem: an agent needs useful computation to survive when old tokens leave its bounded working context. It augments a pretrained full-attention model with a fixed-capacity recurrent memory state and supports it through memory-oriented post-training and state-aware serving.

### TESSERA interpretation

LiveMem and TESSERA address complementary layers:

```text
LiveMem
→ intrinsic model state across context turnover

TESSERA
→ external, inspectable evidence across files, versions and queries
```

The paper gives TESSERA a useful lifecycle test: evidence that has left the active context should remain recoverable without pretending the external index is an intrinsic neural state.

### Derived experiment

Build continuity cases with context turnover and measure retrieval/answer quality by evidence distance, while keeping model context budget and reader policy fixed.

### Difference / caution

TESSERA does not modify model weights, attention, KV-cache behavior or serving infrastructure.

### Status

Research reference. No intrinsic recurrent memory implemented.

---

## FinPerMA — Event-Grounded Personalized Memory Benchmark

Source: https://arxiv.org/abs/2608.04095  
Published: 2026-08-04

### What the paper says

FinPerMA evaluates whether memory systems update individualized user models after material events. It uses frozen longitudinal investor trajectories, deterministic theory-informed impact rules and a Post-Shock checkpoint. The benchmark contains 2,994 questions across 276 personas and reports that factual summaries can lose preference signals needed for personalization.

### TESSERA interpretation

A memory can retrieve yesterday's facts and still fail to represent today's user state. Preference-memory evaluation should therefore include:

```text
state before event
→ material event + evidence
→ state after event
→ supersession / conflict / temporal validity
```

### Derived experiment

Create domain-neutral preference-shock cases and compare raw evidence, summaries and typed memories on pre/post-event accuracy, evidence citation and obsolete-preference abstention.

### Difference / caution

The behavioral-finance rules are part of FinPerMA's benchmark construction; TESSERA should reuse the evaluation pattern without claiming financial-domain validity.

### Status

Candidate benchmark pattern. No FinPerMA adapter implemented.

---

## Persistent Memory and User Profiles — Personalized Long-Term Interaction

Source: https://arxiv.org/abs/2510.07925  
Published: 2025-10-09

### What the paper says

The paper derives requirements for adaptive personalized agents and proposes a framework combining persistent memory, evolving user profiles, multi-source retrieval, dynamic coordination and self-validation. It evaluates the approach on three public datasets and complements that evaluation with a five-day pilot user study.

### TESSERA interpretation

TESSERA should treat a user profile as a derived state view:

```text
source memories + temporal evidence
→ profile synthesis
→ validation
→ versioned profile view
```

The profile must not replace or erase the evidence from which it was inferred.

### Derived experiment

Compare retrieval-only personalization with versioned profile synthesis. Measure correctness, consistency after updates, provenance completeness and recovery from an incorrect profile update.

### Difference / caution

TESSERA provides memory/evidence infrastructure; final personalization, coordination and response generation remain outside its current product boundary.

### Status

Planned research direction. No profile-synthesis engine implemented.

---

## State Contamination — Safety in Evolving Memory

Source: https://arxiv.org/abs/2605.16746  
Published: 2026-05-16

### What the paper says

The paper studies how unsafe content can persist through transcripts, summaries, retrieved context and memory buffers. It calls the hidden survival of influence through apparently cleaner summaries memory laundering and reports that sanitizing before summarization reduces contamination more effectively than filtering only the completed summary.

### TESSERA interpretation

Memory safety is a lifecycle property:

```text
ingest
→ assess source
→ derive / summarize
→ reassess derived state
→ persist with lineage
→ retrieve with status visible
```

A derived summary should never silently receive greater authority than contaminated or unverified source evidence.

### Derived experiment

Inject controlled unsafe or misleading state before and after summarization. Measure propagation, laundering, false-positive sanitization, lineage preservation and whether retrieval exposes the safety status.

### Difference / caution

The paper's results do not establish that one generic filter is sufficient. TESSERA needs explicit policy boundaries and reproducible threat models before implementation claims.

### Status

Planned safety Test Card. Provenance exists; end-to-end contamination control does not.

---

## MemORAI — Adaptive Graph Intelligence

Sources:
- https://aclanthology.org/2026.findings-acl.1408/
- https://arxiv.org/abs/2605.01386

Published: Findings of ACL 2026

### What the paper says

MemORAI combines selective memory filtering and dual-layer compression with a provenance-enriched multi-relational graph. It retains turn-level factual origins and retrieves query-adaptive subgraphs using Dynamic Weighted PageRank. The paper evaluates retrieval and personalized generation on LOCOMO and LongMemEval.

### TESSERA interpretation

MemORAI reinforces three controls that must remain separate:

```text
storage gate
≠ provenance model
≠ query-adaptive graph retrieval
```

TESSERA can study each independently rather than importing a monolithic graph pipeline.

### Derived experiment

Extend #25/#26 with a graph-ranking arm and a selective-storage arm. Compare against no graph, unweighted expansion and current explainable retrieval using answer quality, recall, tokens, latency, provenance coverage and update cost.

### Difference / caution

Reported MemORAI results are not TESSERA results. Dynamic Weighted PageRank and its compression pipeline are not current TESSERA capabilities.

### Status

Research reference for planned graph and storage-gating experiments.

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
