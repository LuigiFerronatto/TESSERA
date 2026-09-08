# TESSERA — Research & Competitive References

> **Purpose:** auditable bibliography for ideas that influence TESSERA.
>
> **Original bibliography / product-document verification:** 2026-08-30.
>
> **Scoped paper review:** 2026-09-07; the 28 papers mapped as P01–P28 below,
> plus supplementary watchlist source S01. This does not redate verification of
> unrelated entries or fast-moving product documentation.
>
> A source appearing here does **not** mean TESSERA implements or validates its claims.

The [dated paper review](MEMORY_PAPERS_2026-09-07.md) connects this bibliography
to the complete improvement map, existing issue owners and proposed experiments.
Documentation archival is tracked in [#223](https://github.com/LuigiFerronatto/TESSERA/issues/223).
P01–P28 and opportunity numbers refer to that review and its linked map, not GitHub
issue numbers. Entries retained from the earlier bibliography are enriched in place;
the review adds 24 source sections and the primary paper to the existing
LongMemEval V2 section. S01 is supplementary and excluded from the 28-paper count.

For this review, **research-only** means that the proposed application has not been
implemented or validated by adding the reference. It does not erase any existing
TESSERA implementation or benchmark work documented elsewhere. Publication and
revision dates identify the source record; they are distinct from the review date.

## Source policy

Keep five layers separate:

```text
external source
→ what the paper/product actually says

TESSERA interpretation
→ what we think the signal means for our architecture

Test Card
→ how we plan to measure that interpretation

implementation
→ what code actually exists

TESSERA result
→ what this repository/CI/benchmark actually measured
```

Never rewrite a paper claim as a TESSERA result. Prefer primary/official sources. Revalidate fast-moving product docs before using them externally.

---

# Core memory research

## QUMem

**Paper:** *QUMem: Personalized Memory for Query-Conditioned User-State Inference in LLM Agents*  
ArXiv: https://arxiv.org/abs/2608.16168  
Published: 2026-08-17

Relevant signal:
- independent handling of facts, preferences and transferable insights;
- query-conditioned user-state inference;
- temporal/source evidence.

TESSERA interpretation:
- exactly three semantic drawers: `facts`, `preferences`, `insights`;
- do not make QUMem's full inference pipeline mandatory for basic retrieval.

Related: #9, #17, #20.

2026-09-07 review mapping: **P08**; opportunities 02, 04, 06, 08, 25;
existing fidelity work #136–#146. Treat the full sequential inference pipeline as
an experiment, preserving the independent facts/preferences/insights distinction.
Status of these proposed extensions: **research-only**.

---

## A-MEM

**Paper:** *A-MEM: Agentic Memory for LLM Agents*  
ArXiv: https://arxiv.org/abs/2502.12110  
Published: 2025-02-17

Relevant signal:
- atomic structured notes;
- Zettelkasten-inspired links;
- adaptive memory evolution.

TESSERA interpretation:
- atomic/interconnected memory is useful;
- automatic memory evolution must remain auditable and must not silently rewrite historical evidence.

Related: #14, #19, #21.

---

## LongMemEval

**Paper:** *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory*  
ArXiv: https://arxiv.org/abs/2410.10813  
Published: 2024-10-14

Core abilities:
1. Information Extraction
2. Multi-Session Reasoning
3. Knowledge Updates
4. Temporal Reasoning
5. Abstention

TESSERA use:
- external benchmark backbone in #18;
- internal sanity Hit@k/MRR must never be presented as LongMemEval performance.

2026-09-07 review mapping: **P11**; initial submission 2024-10-14,
v2 revised 2025-03-04; ICLR 2025. The paper separates indexing, retrieval and reading
across 500 questions. Opportunities 07, 09, 37, 40, 41 extend evaluation under
#18, #28, #103–#105, #142. Conversational QA does not establish autonomous task
completion, and repeated tuning on one development subset risks overfitting.
Status of these proposed evaluation extensions: **research-only**.

---

## LongMemEval V2

**Paper:** *LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues*\
Primary: https://arxiv.org/abs/2605.12493\
Published: 2026-05-12\
Project: https://xiaowu0162.github.io/longmemeval-v2/

Repository / project source:
- https://github.com/xiaowu0162/LongMemEval-V2

TESSERA use:
- later-stage evaluation once Foundation/ablation adapter is reliable;
- not part of basic CI.

Source signal:
- questions over prior experience cover static/dynamic state, workflows,
  environment gotchas and premise awareness;
- this is a distinct benchmark, not simply a replacement question set for V1.

TESSERA interpretation:
- extend evidence-gathering evaluation to environment-specific experience;
- measure real task completion separately from questions about previous tasks.

Review mapping: **P12**; opportunities 19, 26, 37, 38; existing #106, #21, #143.
Status: **research-only** mapping to the existing V2 evaluation scope; no adapter
or new result is delivered by this reference update.

---

# Additional long-term memory research

## LiveMem

**Paper:** *LiveMem: Maintaining Memory State Continuity in Long-Running LLM Inference*  
ArXiv: https://arxiv.org/abs/2608.02515  
Published: 2026-08-03

Source signal:
- treats state continuity under context turnover as distinct from retrieving selected history;
- maintains a fixed-capacity recurrent memory state while the active KV context remains bounded;
- combines context turnover, memory-oriented post-training and state-aware serving.

TESSERA interpretation:
- distinguishes intrinsic model-state continuity from TESSERA's external, text-first evidence layer;
- motivates lifecycle tests in which supporting evidence leaves the active context but must remain recoverable;
- does not justify coupling TESSERA to one model architecture or serving stack.

Status: reference for future continuity evaluation; not an implemented intrinsic-memory capability.

---

## FinPerMA

**Paper:** *FinPerMA: A Theory-Informed, Event-Grounded Personalized-Memory Benchmark for LLM Agents*  
ArXiv: https://arxiv.org/abs/2608.04095  
Published: 2026-08-04

Source signal:
- event-grounded evaluation over frozen longitudinal investor trajectories;
- a Post-Shock checkpoint tests whether a material event updates the persistent user model;
- 2,994 questions from 276 personas;
- reported results show factual summaries can preserve details while losing preference signals needed after shocks.

TESSERA interpretation:
- personalized memory must be evaluated on state transitions, not only fact recall;
- preference updates need temporal evidence, explicit supersession/conflict handling and before/after checkpoints;
- the financial domain is a benchmark setting, not a claim that TESSERA is a financial-advice system.

Status: candidate benchmark pattern for temporal preference-update tests; no FinPerMA adapter implemented.

---

## Persistent Memory and User Profiles

**Paper:** *Enabling Personalized Long-term Interactions in LLM-based Agents through Persistent Memory and User Profiles*  
ArXiv: https://arxiv.org/abs/2510.07925  
Published: 2025-10-09

Source signal:
- derives technical requirements from a unified personalization definition;
- combines persistent memory, evolving user profiles, multi-source retrieval, dynamic coordination and self-validation;
- evaluates the framework on three public datasets and a five-day pilot user study.

TESSERA interpretation:
- a user profile is a derived, evolving view over evidence rather than a replacement for source memories;
- profile updates should preserve provenance, validation state and the evidence that caused the change;
- response personalization remains the consuming agent's responsibility.

Status: architecture reference for future user-state/profile synthesis; not implemented as a profile engine.

---

## State Contamination

**Paper:** *State Contamination in Memory-Augmented LLM Agents*  
ArXiv: https://arxiv.org/abs/2605.16746  
Published: 2026-05-16

Source signal:
- persistent transcripts, summaries, retrieved context and memory buffers create a state-control safety surface;
- unsafe influence can survive compression in a less visibly toxic summary, described as memory laundering;
- sanitizing state before summarization is reported as more effective than cleaning only the completed summary.

TESSERA interpretation:
- provenance alone is insufficient if contaminated content is normalized into trusted persistent state;
- ingestion, derivation and retrieval need separate safety assessments and lineage;
- derived summaries must not silently gain more authority than their source evidence.

Status: safety reference for future contamination and derivation-lineage Test Cards; no complete sanitization policy implemented.

---

## MemORAI

**Paper:** *MemORAI: Memory Organization and Retrieval via Adaptive Graph Intelligence for LLM Conversational Agents*  
ACL Anthology: https://aclanthology.org/2026.findings-acl.1408/  
ArXiv: https://arxiv.org/abs/2605.01386  
Published: Findings of ACL 2026

Source signal:
- selective memory filtering with dual-layer compression;
- provenance-enriched multi-relational graphs with turn-level factual origins;
- query-adaptive subgraph retrieval using dynamically weighted PageRank;
- evaluation on LOCOMO and LongMemEval.

TESSERA interpretation:
- selective storage, evidence provenance and query-conditioned traversal are separable controls;
- turn-level origin supports the Evidence Ledger direction;
- adaptive graph weighting should be compared against lexical, no-expansion and bounded-expansion baselines before adoption.

Status: research reference for #25/#26 and future storage-gating experiments; adaptive PageRank is not implemented.

---

# Recent research signals mapped to Test Cards

## GraphMemix

**Paper:** *GraphMemix: Query-Aware Evidence Forests for Long-Term Multimodal Agent Memory*  
ArXiv: https://arxiv.org/abs/2608.26983  
Published: 2026-08-27

Source signal:
```text
query-aware candidate graph
+ direct evidence utility
+ relation activation/reliability cost
+ maximum evidence budget
+ forest optimization
```

Paper reports a new quality/lifecycle-cost Pareto frontier across four long-term multimodal memory benchmarks.

TESSERA interpretation:
> relation existence does not imply that the relation should be traversed for the current query.

Derived Test Card:
- #25 Query-aware graph expansion / Evidence Budget
- parent #14 Typed Relations / Controlled Expansion

Status: planned experiment, not implemented capability.

---

## CaSKG

**Paper:** *CaSKG: Counterfactual-Causal Skill Graphs for Scalable Agent Skill Retrieval*  
ArXiv: https://arxiv.org/abs/2608.25500  
Published: 2026-08-26  
Code: https://github.com/ZhiyuanLi218/Caskg

Source signal:
- high-recall directed candidate graph;
- semantic, lexical, I/O and structural signals;
- counterfactual remove/substitute/reorder probes;
- calibrated weighted graph before task-conditioned expansion.

Reported comparison against Graph-of-Skills:
- ScienceWorld six-model macro-average: 72.62 → 80.50;
- ALFWorld success: 80.01% → 86.79%.

TESSERA interpretation:
```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

Derived Test Card:
- #26 Relation Confidence / Edge Validation

Important boundary:
- relation confidence must not silently become another default `FINAL_SCORE` weight.

---

## MemToC

**Paper:** *MemToC: Benchmarking Memory-Tool Conflict Resolution in Large Language Models*  
ArXiv: https://arxiv.org/abs/2608.26295  
Published: 2026-08-26

Source signal:
- 6,504 controlled episodes from 542 factual questions;
- independently controlled correctness of model-memory answer and tool return;
- strong tool-following bias even when tools are wrong;
- many attempted improvements reduce abstention in undesirable ways.

Reported observations include:
- instruction-tuned models retain a verified-correct answer against a wrong tool only 6.5–17.1% of eligible cases;
- when both sources are wrong, tool output is repeated in 78.4–86.0% of cases.

TESSERA interpretation:
```text
memory-vs-memory conflict
≠
source arbitration across memory / tool / document
```

Derived Test Cards:
- #27 Evidence / Source Arbitration
- #20 four-state Evidence Sufficiency / Abstention
- #32 Source Authority / Scope / Instruction Precedence

---

## RENDER

**Paper:** *RENDER: Controlling Reader-Facing Evidence in LLM Memory Evaluation*  
ArXiv: https://arxiv.org/abs/2608.23568  
Original submission: 2026-06-05

Source signal:
- reader-facing artifact is itself an evaluation variable;
- same underlying information can produce materially different downstream memory/QA results;
- reported matched-budget resolved packets outperform recency-truncated raw dialogue by 42.4–72.6 points depending on model/setup.

TESSERA interpretation:
```text
retrieval quality
≠ rendering quality
```

Derived Test Cards:
- #28 RAW vs EVIDENCE vs STRUCTURED renderer ablation
- parent #18 LongMemEval controls

---

# September 2026 research expansion

The following entries correspond to the [2026-09-07 review](MEMORY_PAPERS_2026-09-07.md).
The [improvement map](IMPROVEMENT_MAP_2026-09-07.md) defines their opportunity
numbers and experiment briefs. QUMem (P08), Zep (P09), LongMemEval (P11), and
LongMemEval V2 (P12) remain in their existing sections to avoid duplicate entries.
All applications in this section are **research-only**. Related issue IDs identify
existing scope or overlap, not a new approval, delivered feature or changed status.

## Reproducing LightMem

**Paper:** *Reproducing LightMem: Naive RAG Is Just as Good for Memory Management*\
Primary: https://arxiv.org/abs/2607.29104\
Published: 2026-07-31; v1

Source signal:
- a fixed constructed memory store can produce substantially different results
  with different retrievers;
- construction may lose answer-relevant information, while compression can help
  under tight answering-token budgets.

TESSERA interpretation: compare raw, atomic and summarized evidence under the same
reader and budget; measure construction loss separately from retrieval loss.
This is a reproduction of particular LightMem settings, not proof that all
structured memory is unnecessary.

Review mapping: **P01**; opportunities 04, 07, 15, 40; experiment X1;
related #18, #28, #70, #103–#105, #136, #137, #142, #158, #159, #176.
Status: **research-only** ablation proposal.

---

## STALE

**Paper:** *STALE: Can LLM Agents Know When Their Memories Are No Longer Valid?*\
Primary: https://arxiv.org/abs/2605.06527\
Published: 2026-05-07; v1

Source signal: tests state resolution, stale-premise resistance and adaptation
when later events undermine earlier assumptions without explicitly negating them.

TESSERA interpretation: mark dependent conclusions for evidence-linked
revalidation after source changes. Distinguish historical truth, outdated state,
uncertainty and insufficient support. Inferred invalidation can be wrong, so
candidate transitions must remain reversible.

Review mapping: **P02**; opportunities 01, 06, 10, 16; experiment X3;
related #12, #15, #16, #20, #27, #73, #167, #168.
Status: **research-only** state-change evaluation proposal.

---

## Beyond Memory Majority / CAMA

**Paper:** *Beyond Memory Majority: Latent-Source Reasoning for Multi-Agent Memory Arbitration*\
Primary: https://arxiv.org/abs/2608.19701\
Published: 2026-08-20; v1

Source signal: groups query-dependent correlated evidence and seeks missing
independent support rather than counting agent restatements as separate origins.

TESSERA interpretation: track transitive common ancestry across copies, summaries
and derived insights, then test whether correlated repetition creates false
support. One source may contain complementary facts; dependence must not become
an unconditional one-source-one-fact limit. Controlled correlation variants
require reproduction on TESSERA fixtures.

Review mapping: **P03**; opportunities 03, 10, 24, 33; experiment X2;
related #20, #26, #27, #32, #137, #140.
Status: **research-only** provenance and arbitration proposal.

---

## When Continual Learning Moves to Memory

**Paper:** *When Continual Learning Moves to Memory: A Study of Experience Reuse in LLM Agents*\
Primary: https://arxiv.org/abs/2604.27003\
Published: April 2026; v1 inspected

Source signal: old experience can remain stored while near-duplicate additions
displace it from retrieval; finer storage and more frequent retrieval can hurt
reuse in the tested task sequences.

TESSERA interpretation: probe old, rare and recent capabilities as the corpus
grows; compare atomic retrieval, procedure reconstruction and diversity controls.
The small ALFWorld/BabyAI study and sparse retriever establish a failure mechanism
to test, not a universal objection to atomic memories.

Review mapping: **P04**; opportunities 14, 15, 38, 39; experiment X5;
related #17, #18, #19, #21, #143, #169.
Status: **research-only** backward-transfer and interference evaluation.

---

## UtilMem

**Paper:** *UtilMem: Benchmarking Evidence Utilization in Long-Term Conversational Memory*\
Primary: https://arxiv.org/abs/2608.30508\
Inspected text: https://arxiv.org/html/2608.30508v1\
Published: 2026-08-31; v1

Source signal: evaluates synthesis of scattered evidence, implicit relevance and
distractor resistance in long-form answers, using comparison with oracle context.

TESSERA interpretation: measure whether retrieved evidence improves a supported
decision, plan or summary, alongside retrieval coverage. Separate retrieval misses
from evidence the reader ignores or misuses. Judge-relative normalized robustness
is not ordinary QA accuracy; retain human checks on a sample.

Review mapping: **P05**; opportunities 07, 37, 39, 40;
related #18, #28, #103, #104, #142, #143, #169, #170.
Status: **research-only** utilization benchmark proposal.

---

## Controlled Memory Interference

**Paper:** *Controlled Memory Interference in Continual LLM Agents*\
Primary: https://arxiv.org/abs/2608.07622\
Inspected text: https://arxiv.org/html/2608.07622v1\
Published: 2026-08-07; v1

Source signal: count-controlled repetition, same-slot conflicts and unrelated
additions expose different failure modes; retrieving an update and adopting it
correctly can fail independently.

TESSERA interpretation: vary distractor relationships at equal corpus sizes and
measure target retrieval, correct-update adoption and false-update acceptance
separately. The controlled conditions are diagnostics, not population failure-rate
estimates.

Review mapping: **P06**; opportunities 03, 06, 14, 38, 39; experiment X5;
related #15, #16, #18, #20, #21, #137, #140, #143.
Status: **research-only** interference fixture proposal.

---

## Sufficient Context

**Paper:** *Sufficient Context: A New Lens on Retrieval Augmented Generation Systems*\
Primary: https://arxiv.org/abs/2411.06037\
Published: 2024-11-09; v3 revised 2025-04-23

Source signal: relevant retrieved context can still be insufficient to answer;
selective response benefits from evidence-completeness signals alongside model
confidence.

TESSERA interpretation: expose missing evidence and reasons for insufficiency,
then evaluate gather-more and abstention decisions at matched budgets. Similarity
is not a calibrated truth probability. This is RAG research; improved correctness
among answered questions must be reported with its answer-coverage trade-off.

Review mapping: **P07**; opportunities 08, 09, 40, 41;
related #17, #18, #20, #25, #104, #139, #140, #169.
Status: **research-only** sufficiency calibration proposal.

---

## MemoTime

**Paper:** *MemoTime: Memory-Augmented Temporal Knowledge Graph Enhanced Large Language Model Reasoning*\
Primary: https://arxiv.org/abs/2510.13614\
Published: 2025-10-15; v3 revised 2026-02-23

Source signal: decomposes compound temporal questions into explicit operators and
selects evidence paths with compatible temporal bounds.

TESSERA interpretation: validate interval intersection, before/after and
historical-state queries before adding assisted planning. Test cross-entity
temporal consistency independently from recency ranking. Structured temporal-KG
QA does not establish performance over noisy conversations or Markdown sources.

Review mapping: **P10**; opportunities 06, 08, 10;
related #15, #16, #17, #20, #25, #73, #139, #140.
Status: **research-only** temporal-operator experiment.

---

## GroupMemBench

**Paper:** *GroupMemBench: Benchmarking LLM Agent Memory in Multi-Party Conversations*\
Primary: https://arxiv.org/abs/2605.14498\
Published: 2026-05-14; v2 revised 2026-05-16

Source signal: speaker beliefs, audience-specific vocabulary and reply structure
matter for group memory; ingestion can erase features that lexical retrieval
preserves.

TESSERA interpretation: retain speaker, audience and thread structure in episode
construction and compare against raw BM25 retrieval. Probe mistaken consensus and
wrong-speaker attribution. Synthetic English conversations do not establish
multilingual or multimodal behavior.

Review mapping: **P13**; opportunities 05, 07, 11, 25;
related #18, #136–#138, #143, #191; opportunity 05 remains a separate
entity-resolution candidate.
Status: **research-only** group-context evaluation proposal.

---

## Agent-Native Memory Systems Study

**Paper:** *Are We Ready For An Agent-Native Memory System?*\
Primary: https://arxiv.org/abs/2606.24775\
Published: 2026-06-23; v1

Source signal: compares representation/storage, extraction, retrieval/routing and
maintenance across 12 systems and two baselines; results depend on workload, and
localized maintenance can reduce cost.

TESSERA interpretation: identify the limiting stage before selecting a different
store or graph; measure update correctness and lifecycle cost as well as answer
quality. Its workload-dependent results do not nominate one universal backend.

Review mapping: **P14**; opportunities 07, 17, 28, 32, 37, 40;
related #12, #18, #28, #73, #103, #104, #158, #192.
Status: **research-only** system decomposition and maintenance ablation.

---

## CONTRAMEM

**Paper:** *CONTRAMEM: Learning Self-Evolving Procedural Memory from Contrasting Multi-Model Trajectories*\
Primary: https://arxiv.org/abs/2608.22533\
Inspected text: https://arxiv.org/html/2608.22533v1\
Published: August 2026; v1 inspected

Source signal: contrasts different models' attempts on the same tasks and distills
scoped function/task guidance through localized edits.

TESSERA interpretation: retain comparable positive/negative traces, independently
verified outcomes, applicability and counterexamples. Separate tool contracts from
task procedures. The diversity increment is smaller than the entire gain over no
memory; timing-related failures remain difficult and adapted controls are not
original-method replications.

Review mapping: **P15**; opportunities 18, 19, 21, 26; experiment X4;
related #21, #71, #72, #121, #136, #177, #193, #196.
Status: **research-only** contrastive experience experiment.

---

## From Memory to Skills / MSCE

**Paper:** *From Memory to Skills: Evidence-Grounded Co-Evolution Governance for Long-Horizon LLM Agents*\
Primary: https://arxiv.org/abs/2607.16621\
Inspected text: https://arxiv.org/html/2607.16621v1\
Date scope: July–August 2026 manuscript; the inspected HTML header and manuscript
carry different dates, so no single release day is asserted here.

Source signal: separates traces, procedures and environmental knowledge; promotes
supported procedures to skills with evidence, applicability and verification.

TESSERA interpretation: add explicit promotion, revalidation and revocation stages
for procedural guidance. TESSERA can retain evidence/status while the host executes
skills. The paper's gain/reliability estimates are heuristic, not causal credit
assignment, and LLM transformations add cost and noise.

Review mapping: **P16**; opportunities 02, 18–22; experiment X4;
related #19, #20, #21, #121, #193.
Status: **research-only** evidence-bearing procedure lifecycle proposal.

---

## MemP / Memᵖ

**Paper:** *Memᵖ: Exploring Agent Procedural Memory*\
Primary: https://arxiv.org/abs/2508.06433\
Inspected revision: https://arxiv.org/html/2508.06433v4\
Published: 2025-08-08; v4 revised 2026-04-15

Source signal: compares trajectory and procedural representations, update
strategies and model transfer. Improvements depend on task and metric; a reported
TravelPlanner configuration improves some measures while worsening hard constraints.

TESSERA interpretation: treat representation choice as an ablation under #21;
retain applicability, environment version, failure cases and outcome evidence.
Report constraint violations separately from average success and step reductions.

Review mapping: **P17**; opportunities 18, 19, 20, 26; experiment X4;
related #21, #71, #72, #121, #177, #193.
Status: **research-only** procedural-representation baseline.

---

## MemRL

**Paper:** *MemRL: Self-Evolving Agents via Runtime Reinforcement Learning on Episodic Memory*\
Primary: https://arxiv.org/abs/2601.03192\
Inspected revision: https://arxiv.org/html/2601.03192v2\
Published: 2026-01-06; v2 revised 2026-02-12

Source signal: screens experiences for relevance, then uses outcome-learned
utility without updating backbone weights.

TESSERA interpretation: keep relevance, factual confidence and demonstrated
usefulness separate; test outcome attribution and relevance gating under existing
utility-feedback scope. Multiple retrieved experiences complicate credit
assignment, and repeated runtime epochs differ from held-out transfer.

Review mapping: **P18**; opportunities 08, 14, 21, 26;
related #17, #19, #20, #21, #169.
Status: **research-only** utility-aware retrieval experiment; utility is not truth.

---

## MemSkill

**Paper:** *MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents*\
Primary: https://arxiv.org/abs/2602.02474\
Inspected text: https://arxiv.org/html/2602.02474v1\
Published: February 2026; v1 inspected

Source signal: learns memory-construction routines and improves their selection
using hard cases, rather than only storing task procedures.

TESSERA interpretation: version extraction/consolidation routines and validate
writer-policy changes offline with a held-out hard-case buffer and rollback.
Outcome supervision is required; limited benchmark subsets and excluded adversarial
questions constrain extrapolation to full benchmark results.

Review mapping: **P19**; opportunities 04, 15, 22, 41;
related #19, #21, #70, #104, #136, #176.
Status: **research-only**, deferred offline learned-writer experiment.

---

## MemCon

**Paper:** *Memory as a Controlled Process: Learned Adaptive Memory Management for LLM Agents*\
Primary: https://arxiv.org/abs/2607.13591\
Inspected text: https://arxiv.org/html/2607.13591v1\
Published: July 2026; v1 inspected

Source signal: a lightweight controller selects memory actions such as retrieval
depth, retry, consolidation or no operation.

TESSERA interpretation: begin with an optional read-only budget policy and compare
skip/small/expanded retrieval using verified outcomes and total cost. Lightweight
control does not remove LLM calls from the backend. Unsupported maintenance hooks
can become no-ops, and policy transfer needs evaluation.

Review mapping: **P20**; opportunities 08, 15, 17, 21;
related #17, #19, #20, #21, #169, #192.
Status: **research-only** adaptive-operation policy proposal.

---

## DeltaMem

**Paper:** *DeltaMem: Incremental Experience Memory for LLM Agents via Residual Trees*\
Primary: https://arxiv.org/abs/2606.03083\
Inspected text: https://arxiv.org/html/2606.03083v1\
Published: June 2026; v1 inspected

Source signal: separates reusable base procedures from environment-specific
variations and reconstructs the applicable chain.

TESSERA interpretation: test scoped procedure variants and environment
compatibility before adopting a residual-tree representation. Preserve source
links when composing variants. Extraction adds inference cost, thresholds vary by
benchmark, and stale environment details remain an acknowledged limitation.

Review mapping: **P21**; opportunities 15, 19, 26;
related #21, #71, #72, #121, #177, #193.
Status: **research-only** applicability-aware procedure experiment.

---

## Multi-Agent Transactive Memory

**Paper:** *Multi-Agent Transactive Memory*\
Primary: https://arxiv.org/abs/2606.19911\
Inspected text: https://arxiv.org/html/2606.19911v1\
Published: June 2026; v1 inspected

Source signal: heterogeneous producers contribute experience reused by different
consumers, optionally with a learned utility reranker.

TESSERA interpretation: retain producer/model/harness/environment metadata and
measure a cross-runtime transfer matrix, negative transfer and cost. Shared
storage alone does not establish useful transfer; benchmark-specific reranking
gains do not establish cross-benchmark generalization.

Review mapping: **P22**; opportunities 18, 24, 26;
related #21, #177, #178, #193, #204.
Status: **research-only** shared-experience portability experiment.

---

## Collaborative Memory

**Paper:** *Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control*\
Primary: https://arxiv.org/abs/2505.18279\
Inspected text: https://arxiv.org/html/2505.18279v1\
Published: May 2025; v1 inspected

Source signal: private/shared memory fragments retain contributor/resource
provenance for permission-aware reuse under changing access.

TESSERA interpretation: any future shared service needs deterministic permission
checks for retrieval and derived records, including revocation, cached contexts
and exports. Moderate-scale simulations do not establish a production permission
boundary; do not delegate enforcement to an LLM's judgment.

Review mapping: **P23**; opportunities 23, 24, 34, 36;
adjacent #167, #168, #178, #196, #204. The map identifies dedicated permission
contracts as candidates, not completed work.
Status: **research-only**, conditional on shared-service scope.

---

## LightMem

**Paper:** *LightMem: Lightweight and Efficient Memory-Augmented Generation*\
Primary: https://arxiv.org/abs/2510.18866\
Published: 2025-10-21; v4 revised 2026-02-28

Source signal: topic grouping and compression support short-term consolidation
and offline long-term updates, reducing foreground work in the reported settings.

TESSERA interpretation: evaluate asynchronous consolidation with recoverable
source evidence. Compare total build-plus-query cost and online latency
separately; measure rare-fact loss and source recoverability. Pair this source
with the independent reproduction P01 before adopting compression assumptions.

Review mapping: **P24**; opportunities 15, 17, 32;
related #12, #19, #73, #136, #168, #176, #192.
Status: **research-only** consolidation and lifecycle-cost experiment.

---

## MemForest

**Paper:** *MemForest: An Efficient Agent Memory System with Hierarchical Temporal Indexing*\
Primary: https://arxiv.org/abs/2605.23986\
Published: May 2026; v2 revised 2026-07-31

Source signal: parallel extraction and localized dirty-path refresh reduce
dependencies on the write path and motivate measuring write-to-queryable latency.

TESSERA interpretation: test source-version freshness and selective recomputation
under concurrent ingestion/query workloads. Measure stale exposure, build cost
and quality while derived state is dirty. Structural insertion depth is not
end-to-end ingestion complexity; the results do not require TESSERA to use a tree.

Review mapping: **P25**; opportunities 17, 28, 32, 38;
related #12, #73, #120, #158, #171, #192.
Status: **research-only** incremental-maintenance experiment.

---

## Practical Memory Injection / MINJA

**Paper:** *A Practical Memory Injection Attack against LLM Agents*\
Primary: https://arxiv.org/abs/2503.03704\
Inspected revision: https://arxiv.org/html/2503.03704v2\
Published: 2025-03-05; v2 inspected

Source signal: ordinary interactions can seed persistent malicious records that
later influence behavior when retrieved as experience.

TESSERA interpretation: preserve source authority through extraction,
summarization and retrieval; test delayed, cross-session and transformed attacks
with benign-utility controls. Stored observations must not silently become
instructions. Attack success depends on the environment and store population;
this is not a measured vulnerability report about TESSERA.

Review mapping: **P26**; opportunities 02, 33, 35;
related #19, #26, #27, #32, #69, #137, #176, #191.
Status: **research-only** memory-lifecycle adversarial evaluation.

---

## Memory Poisoning Attack and Defense

**Paper:** *Memory Poisoning Attack and Defense on Memory Based LLM-Agents*\
Primary: https://arxiv.org/abs/2601.05504\
Inspected text: https://arxiv.org/html/2601.05504v1\
Published: 2026-01-09; v1

Source signal: re-examines poisoning under different legitimate-memory
populations and defense thresholds; rejecting suspicious writes can also reject
useful evidence.

TESSERA interpretation: evaluate populated stores and report attack resistance,
legitimate-write acceptance and downstream utility together. The narrow EHR/model
setting and heuristic defenses do not establish a general security boundary.

Review mapping: **P27**; opportunities 33, 35, 41;
related #19, #32, #69, #104, #176, #191.
Status: **research-only** safety/utility trade-off evaluation.

---

## Reliability-Conditional Belief Memory

**Paper:** *When Does Belief-Based Agent Memory Help? Reliability-Conditional Updating and Provenance-Capped Poisoning Defense*\
Primary: https://arxiv.org/abs/2606.22030\
Published: 2026-06-20; v2 revised 2026-07-16

Source signal: belief updating is more useful when evidence conflicts or differs
in reliability; confidence inferred from content can be manipulated, motivating
provenance-bounded trust.

TESSERA interpretation: separate confidence, provenance and evidence sufficiency;
test correlated poisoning alongside legitimate low-trust corrections. Controlled
contradiction settings and comparator differences limit headline conclusions.
Provenance caps have utility costs; complete taint propagation is not established
as an implemented defense by this source.

Review mapping: **P28**; opportunities 02, 03, 09, 33;
related #19, #20, #26, #27, #32, #137, #140.
Status: **research-only** conditional belief/arbitration experiment.

---

# Supplementary research watchlist

## FSFM — limited-evidence watchlist

**Paper:** *FSFM: A Biologically-Inspired Framework for Selective Forgetting of Agent Memory*\
Primary: https://arxiv.org/abs/2604.20300\
Initially inspected text: https://arxiv.org/html/2604.20300v1\
Published: 2026-04-22; v2 revised 2026-04-23; metadata checked 2026-09-07

Source signal: distinguishes decay, active deletion, safety-triggered forgetting
and adaptive retention decisions.

TESSERA interpretation: define demotion, archival, consolidation and deletion as
different operations; test rare-evidence loss, recoverability and removal from
managed derivatives. Its controlled telecom-domain evaluation and scale limits
do not justify a general security guarantee or the abstract's complete-risk-
elimination language.

Review mapping: **S01**, supplementary to P01–P28; opportunities 13–15, 17;
adjacent #12, #19, #21, #73, #168, #196, #204.
Status: **research-only, limited-evidence watchlist**. Retained because it informed
the research notes; excluded from the 28-paper core count and not promoted into
an adopted design or implementation commitment.

---

# Product / framework references

## Mem0

Primary docs verified:
- Graph Memory: https://docs.mem0.ai/open-source/features/graph-memory
- OSS v2 → v3 migration: https://docs.mem0.ai/migration/oss-v2-to-v3
- Long-term memory CLI: https://docs.mem0.ai/platform/cli
- Paper: https://arxiv.org/abs/2504.19413

Current-source caution:

Mem0 documentation reflects more than one architectural generation. A Graph Memory page describes entity/relationship extraction into an external graph backend beside vector retrieval. The newer OSS migration guide says external graph-store support was removed from the newer open-source algorithm and replaced with built-in entity linking, alongside semantic + BM25 + entity hybrid retrieval.

Therefore do not summarize Mem0 as simply:

```text
"vector + graph"
```

without specifying version/product path.

Relevant TESSERA comparison:
- extracted memory vs source-backed atomic representation;
- hybrid retrieval quality;
- scope/user/agent boundaries;
- provenance and source preservation;
- latency/context cost.

---

## Zep / Graphiti

**Paper:** *Zep: A Temporal Knowledge Graph Architecture for Agent Memory*\
Paper record: https://arxiv.org/abs/2501.13956\
Inspected text: https://arxiv.org/html/2501.13956v1\
Published: 2025-01-20; v1 inspected

Paper source signal: links original episodes and derived facts while separating
event validity from ingestion time.

2026-09-07 paper interpretation: distinguish historical truth from what was known
at the time, and retain correction history. Provider-authored benchmarks do not
isolate bitemporality; newly ingested evidence is not inherently more authoritative.

Review mapping: **P09**; opportunities 01, 06, 16, 28;
related #12, #15, #16, #73, #167, #168. Status of these proposed extensions:
**research-only**. The product-document observations below retain their original
2026-08-30 verification scope.

Primary docs verified:
- Zep v3: https://help.getzep.com/v3/overview
- Graph overview: https://help.getzep.com/graph-overview
- Graphiti overview: https://help.getzep.com/graphiti/getting-started/overview
- Graphiti welcome: https://help.getzep.com/graphiti/getting-started/welcome
- Zep vs Graphiti: https://help.getzep.com/zep-vs-graphiti
- Paper: https://arxiv.org/abs/2501.13956

Documented signals:
- Graphiti = open-source temporal Context Graph framework;
- entity/relationship/fact graph;
- episodic ingestion/provenance;
- bi-temporal validity/fact invalidation;
- incremental updates;
- time/full-text/semantic/graph hybrid retrieval;
- Zep = managed enterprise-scale Context Lake on top of Context Graph infrastructure.

TESSERA comparison:
- Graphiti makes temporal graph structure central;
- TESSERA currently makes source documents + canonical identity + Evidence Ledger the stable substrate and treats advanced graph behavior as an ablation.

Related: #12, #14, #15, #16, #25, #26, #27.

---

## Letta / MemGPT lineage

Primary docs verified:
- https://docs.letta.com/

Current positioning:
- platform for stateful agents;
- persistent memory/state is tightly integrated with the agent runtime/harness.

TESSERA comparison:
```text
Letta
→ memory/state integrated with agent runtime

TESSERA
→ memory mechanics abstracted behind a layer
→ evidence/provenance remains visible
```

Future evaluation should test whether hiding memory mechanics reduces failure modes or removes useful agent control.

---

## LangGraph / LangChain memory patterns

Primary docs verified:
- https://docs.langchain.com/oss/python/langchain/long-term-memory
- https://docs.langchain.com/oss/python/concepts/memory

Documented signals:
- long-term memory persists across threads;
- LangGraph stores JSON documents by namespace/key;
- conceptual taxonomy includes semantic, episodic and procedural memory;
- write timing can be hot-path or background.

TESSERA distinction:
```text
facts / preferences / insights
≠
semantic / episodic / procedural
```

TESSERA also keeps harness instructions as instruction/document semantics with `drawer: null` rather than treating them as another semantic drawer.

---

## MemOS

Primary/open-source sources verified:
- Repository: https://github.com/MemTensor/MemOS
- Intro: https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/memos_intro.md
- Core concepts: https://github.com/MemTensor/MemOS/blob/main/docs/en/open_source/home/core_concepts.md

Documented signals:
- Memory Operating System positioning;
- memory as a first-class orchestrated resource;
- MOS orchestration layer;
- MemCubes;
- multiple memory forms/types;
- lifecycle/scheduling/governance abstractions.

TESSERA distinction:
- intentionally narrower current Foundation;
- text-first source truth, stable identity, provenance and structured evidence before broader memory-OS orchestration.

---

## MemPalace

**Verified official public repository:**
- https://github.com/bassemhalawani/memorypalace

Repository warning states the official sources are that repository, the PyPI package, and `mempalaceofficial.com` documentation.

Documented signals:
- local-first;
- verbatim storage rather than summarize/extract/paraphrase by default;
- pluggable retrieval backend;
- structured palace organization;
- local temporal entity/relationship graph;
- reproducible benchmark artifacts.

Repository reports:
- 96.6% raw R@5 on LongMemEval for its stated zero-API-call retrieval path.

TESSERA use:
- important raw/verbatim baseline for #18;
- do not compare this R@5 directly to TESSERA's internal four-query sanity Hit@5;
- fair comparison requires same source histories, encoder controls where relevant, session normalization, token budgets and same reader/rendering policy.

---

# Research-to-roadmap rule

When a source changes architecture thinking:

```text
SOURCE
  ↓
SOURCE CLAIM
  ↓
TESSERA INTERPRETATION
  ↓
ISSUE / TEST CARD
  ↓
CONTROLLED EXPERIMENT
  ↓
TESSERA EVIDENCE
  ↓
KEEP | ITERATE | REVERT | DROP | DEFER
```

The research bibliography should make that path auditable rather than functioning as a list of fashionable papers.

---

# Reference hygiene checklist

When adding/updating a source:

1. Prefer the paper, official docs or official repository.
2. Record publication/update/verification date when useful.
3. Separate source claim from TESSERA interpretation.
4. Link the corresponding Test Card.
5. Mark implementation status: `implemented`, `experimental`, `planned`, `dropped/deferred`.
6. Revalidate fast-moving product behavior before external publication.
7. Never write “TESSERA outperforms X” without a controlled TESSERA benchmark result.
