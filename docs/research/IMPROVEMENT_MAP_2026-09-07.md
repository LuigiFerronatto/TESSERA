# Tessera: improvement opportunities beyond the current backlog

Archive tracking: [#223](https://github.com/LuigiFerronatto/TESSERA/issues/223). The original research snapshot predates this archive issue and its PR.

Research and repository review · 7 September 2026

**Status:** Dated research snapshot and proposed opportunities. This document does not amend the governed roadmap, change issue priorities, open candidate feature issues, or establish implemented capabilities. The existing two-implementation-card WIP limit plus one benchmark/documentation lane remains authoritative. See [TEST_CARD_OPERATING_MODEL.md](../TEST_CARD_OPERATING_MODEL.md).

**Recommendation:** strengthen Tessera's ability to provide current, sufficient, traceable evidence and demonstrate its contribution to successful agent work. Its best next improvements combine measurement, source-preserving memory construction, dependable state transitions, and learning with bounded applicability. Adding more memory mechanisms without these controls can increase cost and make old evidence harder to recover.

This report maps **48 concrete opportunities across ten areas: 11 candidates without a dedicated open contract and 37 material extensions of existing work**. It connects 28 primary papers to experiments. These are scoped opportunities, not 48 independent epics. It is a broad opportunity map, not a claim to enumerate every possible future feature.

## 1. What was reviewed

- Current `main`, pinned at [`708c973e23d5c4eb8a52d359a2cadc153e161a90`](https://github.com/LuigiFerronatto/TESSERA/commit/708c973e23d5c4eb8a52d359a2cadc153e161a90), whose latest commit contains the #16 conflict-resolution containment delivered by PR #219.
- The complete first page of open GitHub items: **82 issues and one pull request (#222)**; the page contained 83 items against a 100-item limit. All issue bodies were considered for overlap. Of the 82 issues, 13 are lifecycle/automation records; 69 concern roadmap, research, release, or documentation work. These are not 82 missing runtime features.
- The complete recursive repository tree; selected current implementation modules, architecture and output contracts, roadmap, paper notes, competitive landscape, and the committed benchmark records.
- Primary AI-memory papers, including recent 2026 work, with method, evaluation and limitation sections inspected where relevant. Paper findings below are authors' results, not replicated Tessera measurements.

The original research audit was read-only. Its subsequent archival PR adds research documentation only; it does not implement the proposed features or change repository settings. No new Tessera benchmark was run. Novelty judgments mean “no dedicated scope found in this open-issue snapshot,” not “never discussed or implemented anywhere.”

### Established strengths to preserve

Tessera already provides Markdown canonicalization, stable-identity machinery, explicit relations, local lexical/graph retrieval, explainable ranking, evidence spans when provable, source hashes, and Python/CLI/MCP surfaces. The current initialization separates source roots, generated memory, and the derived index. Optional assisted decomposition exists. These are a meaningful foundation. [Current README](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/README.md)

The latest conflict fix deliberately preserves candidates rather than silently choosing a newest record. It does **not** establish full temporal supersession or state reconstruction. Metadata fields and planned contracts should not be mistaken for completed semantics. [Conflict implementation](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/tessera/conflict.py), [issue #16](https://github.com/LuigiFerronatto/TESSERA/issues/16)

### What the recorded measurements establish

The committed LongMemEval dev-50 baseline reports:

| Metric | Recorded value | Correct interpretation |
|---|---:|---|
| Recall@1 | 47.10% | Retrieval metric on the frozen subset |
| Recall@10 | 91.67% | More evidence recovered when ten results are allowed |
| Evidence hit rate | 95.65% | At least some required evidence found on eligible positive queries |
| Provenance coverage | 100% | Returned evidence carries the measured provenance fields |
| Empty retrieval on abstention cases | 0% | Retrieval returned something for the four unanswerable cases; this is not an answer-abstention score |
| Final-answer accuracy | Not measured | Reader and judge were absent |

The baseline is from an earlier measured commit, not a fresh measurement of audited main. It includes 50 questions (46 positive, four abstention), not a full official score. The forward record contains environment-dependent latency, while the original baseline lacks comparable latency. Avoid promoting these results into an accuracy or speed superiority claim. [Baseline record](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/benchmarks/results/longmemeval-v1-dev-50/baseline.json), [forward record](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/benchmarks/results/longmemeval-v1-dev-50/forward.json)

## 2. Improvements already substantially represented in open issues

These remain important, but should not be presented as new discoveries.

| Existing workstream | Current open owners |
|---|---|
| Incremental indexing, metadata diagnostics, broader text ingestion and segmentation | #12, #13, #69, #70 |
| Time, state keys, revision history, conflict and supersession | #15, #16, #73 |
| Authority, instruction precedence and source arbitration | #27, #32, #71, #72 |
| Query adaptation, graph expansion, relation validation, sufficient evidence and abstention | #14, #17, #20, #25, #26 |
| Write admission, experience traces and utility feedback | #19, #21 |
| QUMem fidelity, role-aware episodes, supporting turns, multiple information needs and state reconstruction | #136–#146 |
| Embeddings, reranking, model profiles, local models and diagnostics | #157–#165 |
| Durable memory, task packets, Context Compiler and minimal agent API | #167–#171 |
| AI enrichment, conversation import, resumability and cost accounting | #176, #191, #192 |
| Integration, hooks, Skills, MCP, CLI experience and onboarding | #118–#121, #166, #177–#179, #190, #193, #196 |
| Reader/judge/full evaluation, multimodal benchmark and rendering | #18, #28, #103–#106, #142, #143 |
| Distribution, contribution documentation and exchange formats | #87, #134, #204 |

Issue numbers link to their complete current titles in the inventory at the end. Several are parent epics or overlapping product slices; their counts are not additive estimates of effort.

## 3. How to read the opportunity map

**N** = candidate for a new dedicated contract or Test Card; **E** = a material extension or sharper experiment under existing owners. Existing overlap is named even for N candidates. This classification is intentionally conservative.

**P0** = establish correctness or trustworthy measurement before dependent adaptive behavior; **P1** = next value-oriented experiment after prerequisites; **P2** = conditional exploration. These are recommendations, not changes to GitHub priorities.

Effort is relative: **S** = bounded fixture or component experiment; **M** = several contracts/components; **L** = substantial research or system work. It is not a delivery estimate. Every metric below is proposed unless explicitly described as recorded.

### A. Memory meaning and evidence integrity

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 01 | **Invalidate derived conclusions transitively.** A corrected fact should mark dependent insights, profiles and relations as needing revalidation; preserve their historical derivations. | E: #12, #16, #73, #167, #168; persisted dependency propagation extends packet invalidation. | P1 / M | Change one source supporting a three-level derivation. Measure stale conclusions exposed, valid conclusions wrongly invalidated, and repair work. |
| 02 | **Represent epistemic status explicitly.** Distinguish observation, reported claim, hypothesis, inference, decision and verified outcome as metadata within the existing three drawers. | E: #19, #20, #21, #26, #32. | P1 / M | Mix mocked results, intentions and executed outcomes. Measure unsupported promotion into factual evidence. |
| 03 | **Account for independent origins.** Trace copies, summaries and agent restatements to common ancestors so repeated claims do not gain artificial support. | E: #20 already handles same-source redundancy; #137/#140 cover lineage/dedup. New slice: transitive correlated origins. | P1 / M | One false source plus 20 paraphrases competes with two independent corrections. Measure false-majority errors and preservation of complementary facts from one source. |
| 04 | **Measure information lost during memory construction.** Track which source constraints, negations, numbers, exceptions and relations survive decomposition/compression. | E: #70, #136, #137, #176. | P0 / S–M | Gold annotations over raw episodes versus extracted notes; report omission, distortion and downstream answerability separately. |
| 05 | **Give entities a reversible identity registry.** Support aliases, scoped identity, explicit merges/splits and disjoint graph keyspaces for entities, tags and memories. | N dedicated entity-resolution contract; adjacent #14, #15, #26, #176, #204. | P1 / M | Homonyms, renamed tools, mistaken merges and legal memory IDs resembling internal entity/tag IDs. Measure false merges, identity collisions and correction propagation. |
| 06 | **Exercise bitemporal queries and late corrections.** Separate when a fact held from when Tessera learned it; support uncertain intervals and retrospective corrections. | E: #15, #16, #73; not a new temporal feature proposal. | P1 / M | Ask “what was true then?” and “what did we know then?” after delayed evidence. Report both accuracies and historical leakage. |

### B. Retrieval and context selection

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 07 | **Require a matched-budget raw-source baseline.** Compare raw lexical/dense retrieval with typed, graph and compiled representations using the same reader and input budget. | E: #18, #28, #103–#105, #142, #158, #159. | P0 / S–M | Factor representation × retriever × reader; track answer quality, evidence completeness, tokens and lifecycle cost. Retain complexity only when it adds measurable value. |
| 08 | **Retrieve progressively according to missing evidence.** Start small, identify uncovered needs, and expand only the relevant source, interval or relation neighborhood. | E: #17, #20, #25, #139, #140, #169. | P1 / M | Compare fixed top-k against bounded expansion. Measure completeness per token, latency tails and failed stopping decisions. |
| 09 | **Calibrate evidence sufficiency by task type.** Return explainable insufficiency reasons; fit thresholds on held-out data instead of treating relevance as confidence. | E: #20, #104, #169. | P1 / M | Use answerable/unanswerable and partial-evidence cases. Plot risk versus coverage; assess false certainty and unnecessary abstention. |
| 10 | **Search explicitly for counterevidence.** Reserve some retrieval budget for exceptions, dissenting sources and disconfirming observations. | E: #20, #25, #27, #140. | P1 / M | Compare confirmation-only retrieval with counterevidence expansion on frozen conflicting cases; retain it when correct resolution improves at acceptable cost. |
| 11 | **Validate PT-BR/English and code-switching continuity.** Evaluate accent variation, translated queries, local dates, jargon and cross-language retrieval without changing source text. | E: #136, #158, #176 already touch language; dedicated evaluation extends them. | P1 / S–M | Paired equivalent queries and localized histories; report gaps by language and failure type, including mistaken normalization of IDs. |
| 12 | **Make ranking explanations reproducible and faithful.** Capture effective weights, candidates, exclusions, applied boosts, versions and complete/degraded index coverage. | E: #13, #17, #28, #162, #166, #171. | P0 / S–M | Recompute the displayed score; test source-order permutations, disabled boosts, ties and failed source parsing. Detect unexplained changes and silent omissions. |

### C. Retention, freshness and consolidation

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 13 | **Define verifiable forgetting and purge.** Distinguish hiding, expiry, archival and actual removal; trace effects through derived notes, caches and managed exports. | N; adjacent #12, #73, #168, #196, #204. | P1 / L | Delete a synthetic fact and search every managed derivative after rebuild/restore. State clearly which external copies cannot be revoked. |
| 14 | **Protect rare but important exceptions.** Retention should reflect error cost and conditional applicability, not retrieval popularity alone. | E: #19, #20, #21, #169. | P1 / M | Add a rarely needed prohibition among frequent successes. Measure critical-rule recall after corpus growth and consolidation. |
| 15 | **Consolidate with explicit preservation constraints.** Build versioned summaries retaining source pointers and exception coverage; allow re-expansion. Later, evaluate versioned writer routines offline with rollback. | E: #19, #136, #168, #176. | P1 / M; learned writer P2 / L | Compare no consolidation, unconstrained and constrained summaries. Measure token savings against lost qualifiers; validate writer-policy changes on held-out hard cases. |
| 16 | **Make freshness depend on source volatility.** A changed source or invalid premise can trigger revalidation; age alone should not declare a fact false. | E: #12, #15, #20, #73, #196, #204. | P1 / M | Replay stable and volatile facts. Measure stale exposure, needless refreshes and legitimate late corrections rejected. |
| 17 | **Evaluate hot/cold retrieval and selective maintenance.** Keep fast working views derived and disposable; adapt consolidation to measured workload pressure. | E: #12, #17, #167, #168, #169, #192. | P2 / M–L | Grow corpora at fixed query budget; measure recall of old evidence, RAM, p95 latency, rebuild cost and foreground delay. |

### D. Learning from agent experience

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 18 | **Learn from paired success and failure.** Derive conditional lessons from comparable attempts, including what differed and which outcome was independently verified. | E: #21, #136. | P1 / M | Same-task positive/negative traces versus success-only summaries. Measure repeated-error reduction and unsupported causal conclusions. |
| 19 | **Separate reusable procedures from environment details.** Keep general steps distinct from tool versions, project IDs and local configuration, linked through applicability metadata. | E: #21, #71, #72, #121. | P1 / M | Transfer a lesson between projects and change a tool version. Measure correct reuse and environment-specific contamination. |
| 20 | **Promote lessons through verification stages.** Observation → candidate insight → repeatedly validated procedure → separately packaged skill. Tessera stores evidence and status; the host executes skills. | E: #21, #121, #193; evidence-bearing promotion is the additional scope. | P2 / M–L | Require reproducible task assertions before promotion; measure false promotion, regressions, revocation and transfer. |
| 21 | **Measure the marginal utility of a memory.** Use paired with/without-memory trials and exposure-aware feedback so frequent retrieval is not mistaken for causal value. | E: #21 explicitly owns utility; add attribution and feedback-bias controls. | P1 / M | Fix task/model/prompt, vary only the evidence supplied, randomize order. Measure task-success lift, harm and evaluation cost. |
| 22 | **Route failures back to the responsible memory stage.** Distinguish missing source, extraction loss, retrieval miss, stale inference, ignored evidence and execution failure. | E: #21, #103, #104, #162, #196. | P1 / M | Inject one fault per stage and assess diagnosis precision; do not rewrite memory to compensate for a tool-execution failure. |

### E. Multiple agents, people and runtimes

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 23 | **Enforce access for principals across shared memory.** Scope labels need a permission contract when stores serve different users or agents. | N; adjacent #167, #168, #178. | P2 / L; prerequisite for a shared service. | Mix private and shared evidence. Probe retrieval, graph traversal, diagnostics and cached contexts; measure unauthorized disclosure. |
| 24 | **Publish between private and shared stores deliberately.** Isolate competing experiment branches; promote approved records with origin lineage, review/revocation and conflict handling. | N; adjacent #19, #73, #168, #178, #193, #204. | P2 / L | Two agents publish conflicting lessons concurrently. Test idempotency, contamination isolation, permissions and revocation without silently merging stores. |
| 25 | **Model who said, knows or believes what.** Preserve speaker, audience, reply-thread structure and group-specific vocabulary. | E: #137, #138, #143, #191. | P1 / M | Ask a group question from different participants' perspectives. Measure wrong-speaker attribution and mistaken consensus. |
| 26 | **Condition transfer on the consuming runtime/model.** Keep evidence portable while recording where a procedure was validated; test capability-dependent reuse. | E: #21, #71, #177, #193, #196. | P2 / M | Cross a producer/consumer matrix of harnesses and models using the same source corpus; measure negative transfer and context overhead. |

### F. Storage, recovery and performance

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 27 | **Add multiwriter conflict and retry semantics.** Preserve the existing atomic note replacement; add expected-version checks and distinguish retrying an event from executing the same task again. | N dedicated cross-process contract; #73, #120, #177, #192, #196 are adjacent. | P0 / M | Race two processes against one ID, retry one event, then run a new identical task. Require explicit update conflicts, no duplicate retry and distinct execution history. |
| 28 | **Publish coherent index and citation generations.** Build graph/vector/ledger snapshots separately; pin readers to a complete generation and validate source version before attaching spans. | E: #12, #73, #120, #158, #171, #192. | P0 / M | Query during rebuild or paragraph movement after indexing. Require a version-consistent citation or explicit stale/unknown status, and last-good recovery. |
| 29 | **Keep identity durable across disposable-index deletion.** Stable identity decisions for documents without IDs must survive cache clearing, moves and restoration. | E: repair/clarification of #12, #73, #168; stable identity already exists. | P0 / S–M | Index an unannotated source, rename/edit it, remove derived cache, rebuild and compare document/memory IDs and provenance links. |
| 30 | **Define the serialized-index trust boundary.** Prefer inert, schema-validated derived formats; do not treat an externally supplied executable serialization as ordinary data. | N; adjacent #12, #120, #134. | P0 / M | Validate safe rejection/rebuild for foreign or tampered caches and mixed dependency versions; measure reload cost. |
| 31 | **Specify migration, backup and restore contracts.** Preserve canonical content, identities, semantics and pending operations across software upgrades and interrupted restores. | N; adjacent #73, #118, #134, #204. | P1 / M | Round-trip supported versions with partial failure and rollback. Require semantic equivalence and no silent field loss. |
| 32 | **Retract only affected derived objects.** Maintain reverse dependencies from source versions to segments, embeddings, relations, evidence and state views. | E: #12, #73, #158, #192. | P1 / M | Edit or remove 1% of a corpus. Measure unnecessary recomputation and dangling/stale objects; preserve identical unaffected outputs. |

### G. Security and trust through the memory lifecycle

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 33 | **Propagate trust and taint through derivations.** An untrusted page should not gain authority because a trusted agent summarized it. | E: #19, #26, #27, #32, #137, #176. | P1 / M | Poison → summary → insight → context; measure attack success and legitimate correction loss. Trust cannot be asserted solely by the content itself. |
| 34 | **Recheck permissions and policy at use time.** Revoked access must affect cached contexts, evidence inspection and graph expansion, not only initial ingestion. | N enforcement contract, paired with 23; adjacent #167, #168, #178. | P2 / M; prerequisite for shared service. | Revoke a source between retrieval and reuse; probe IDs, snippets and cached packets for leakage. |
| 35 | **Test indirect and multilingual memory poisoning.** Exercise malicious imported Markdown, obfuscated instructions, long-turn attacks and safety/utility trade-offs. | E: #19, #32, #69, #176, #191. | P1 / S–M | Run benign documentary examples beside attacks; track false positives and downstream attacks after transformation. |
| 36 | **Export the minimum authorized evidence.** Enforce content and metadata redaction on bundles and traces with explicit reports of semantic loss. | E: #196, #204; broader privacy contract coordinates with 23/34. | P2 / M | Seed secrets in bodies, filenames, metadata, relationships and cached summaries; measure leakage and preserved useful evidence. |

### H. Evaluation that measures agent benefit

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 37 | **Create a longitudinal real-task evaluation track.** Assess continuing a project, honoring a changed requirement, avoiding a known failed approach and recovering after a context reset. | E: #18, #21, #106, #142, #143, #169, #170 already own task-benefit metrics. | P0 / M | Extend with repeated real-task fixtures comparing no memory, raw-source retrieval and Tessera under fixed budgets and externally verifiable outcomes. |
| 38 | **Measure performance after long sequences of writes.** Track old, rare and recent knowledge separately as experience accumulates. | E: #12, #15, #18, #21, #143. | P1 / M | Replay a time-ordered stream with delayed probes; report reachability loss, retention, update accuracy and operational cost by age. |
| 39 | **Run a memory dose-response study.** Vary corpus size, granularity and supplied context to discover when more memory harms decisions. | E: #17, #18, #21, #169. | P1 / S–M | Use 1×/10×/100× distractor growth and several context budgets. Distinguish useful recall from interference and dilution. |
| 40 | **Add stage-specific ground truth.** Attribute loss between source capture, decomposition, ranking, context packing, reading and action verification. | E: #28, #103, #104, #136, #137, #142. | P0 / M | Store gold source spans and task assertions; report representation loss, recall, utilization and final execution separately. |
| 41 | **Estimate uncertainty and check cross-model reproducibility.** Use paired comparisons, repeated runs where stochastic, held-out tasks and calibrated judges. | E: #18, #67, #104, #105, #142. | P0 / S–M | Preregister practical margins, confidence intervals and per-category floors; prevent a tiny development set from choosing every architecture. |

### I. Product use and adoption

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 42 | **Make memory inspection answer a user's actual question.** Show why an item was used, what it came from, what changed and how to correct it. | E: #13, #119, #166, #171, #178. | P1 / M | User tasks: locate a bad inference, inspect original evidence, correct scope and verify affected results. Measure completion and time. |
| 43 | **Validate a specific user and recurring job.** Pilot portable project continuity with a small cohort before broadening to every agent-memory use case. | N dedicated adoption experiment; adjacent #118, #134, #178. | P1 / S–M | Measure time to first useful retrieval, voluntary reuse, repeated-context reduction and independently verified task benefit. No default content telemetry. |
| 44 | **Give connectors a change/revocation contract.** Imports need stable source IDs, deletions, retries and permission propagation, not just “read once.” | N general connector contract; adjacent #69, #191, #192, #204. | P2 / M–L | Replay edits, renames, deletions and revoked access from one source. Measure duplicate ingestion, stale evidence and recovery. |
| 45 | **Distribute auditable memory packs.** Package versioned domain evidence or procedural references with provenance, applicability, trust and upgrade diagnostics. | E: #121, #193, #204; public ecosystem is conditional. | P2 / M | Install/update/remove a pack without upgrading its trust or mixing its evidence with personal facts; measure compatibility and useful task transfer. |

### J. Development governance and focus

| ID | Opportunity and concrete change | Coverage | Priority / effort | First experiment and decision signal |
|---|---|---|---|---|
| 46 | **Generate lifecycle projections from canonical event/decision records.** Extend the existing manifest and board-sync machinery to reduce independently edited roadmap/card/status copies. | E: existing #203 delivery; #67, #208 and lifecycle issues. | P1 / M | Replay merge/correction events twice and out of order; require convergence, preserved history and zero unexplained drift. |
| 47 | **Bound and deduplicate maintenance automation.** Reconcile the same event idempotently, cap retries/cost, and distinguish unavailable evidence from failed evidence. | N dedicated automation reliability slice; adjacent #67 and failed-job issues. | P1 / S–M | Replay the same trigger and inject transient failures. Measure duplicate issues, false blocks, retry cost and time to recovery. |
| 48 | **Measure and tune the existing work-in-progress policy around outcomes.** Test a balance of reliability, memory-quality and adoption experiments; revisit after results. | E: existing governed WIP and #172/#203 portfolio work. | P1 / S | Track cycle time, maintainer minutes, implemented capabilities and validated user outcomes. Adjust the existing limit from evidence, not issue count. |

## 4. Source-level findings that justify near-term reliability work

Two distinctions prevent duplicate implementation: **01** concerns whether a persisted conclusion is still supported; **32** concerns which derived computations need to rerun. They may share lineage infrastructure but have different correctness criteria. Likewise, #121/#193 package official Tessera integration Skills; learned agent procedures in **19/20** need a separate experimental lifecycle and should not be confused with those product integrations.

These observations identify concrete contracts worth testing. They are not claims of demonstrated exploitation or measured production incidents.

| Observation in audited source | Why it matters | Follow-up |
|---|---|---|
| Individual note writes use a temporary file, file `fsync` and atomic `os.replace`; the identity manifest and index snapshots are saved separately, and no expected-revision check appears in the reviewed writer. | Atomic replacement protects one file; it does not establish multiwriter conflict detection or a transaction across derived artifacts. | 27–28; preserve current atomicity while defining broader consistency. |
| Evidence enrichment combines cached canonical hashes with a snippet span found in the file read at query time. | If the file changes after indexing, a span from newer bytes can be labeled with an older hash. This is a static data-flow inference, not a reproduced failure. | 28; pin or verify source versions before attaching exact spans. |
| `identity_manifest.json` is stored inside the derived-index directory. | For sources lacking explicit IDs, index disposal and identity continuity need to be reconciled. | 29; preserve authoritative identity decisions separately from disposable ranking data. |
| `_load_index_if_fresh()` calls `pickle.load` before checking the source fingerprint/specification. | A fingerprint check does not make deserializing an untrusted cache safe. | 30; inspect the actual cache ownership/sharing model and choose an inert format or strict trust boundary. |
| The source fingerprint is based on count and latest mtime. | A content change need not change those aggregate values. | Already belongs to #12; add adversarial same-count/mtime fixtures rather than a duplicate feature issue. |
| Retrieval uses TF-IDF seeds, one-hop expansion and personalized PageRank. Evidence extraction selects a paragraph by lexical overlap. | Graph sophistication is constrained by candidate discovery and source preservation; relevance does not establish sufficient support. | 04, 07–12 and 40. |
| Recency is disabled by default, while the explanation field can still report a computed recency value. | Explanations should state the value actually applied, not merely a signal that was computed. | 12; score-reconstruction check is a small bounded improvement. |
| Entities/tags and memory IDs share graph keys; the graph is a `DiGraph` with one edge per node pair. | Namespace collision and multiple relation types need explicit representation tests. | 05 and existing #14/#26; do not build another generic graph epic. |
| Ledger association scans records per memory, snapshots can be fully rewritten, and query expansion recomputes subgraph vectors. | There are concrete scaling candidates, but their user impact has not been profiled. | 17/32/38; measure 1k/10k/100k corpora, hubs, cold/warm start, RAM and p95 before changing storage engines. |

[Engine source](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/tessera/engine_core.py), [evidence implementation](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/tessera/evidence.py), [canonical identity](https://github.com/LuigiFerronatto/TESSERA/blob/708c973e23d5c4eb8a52d359a2cadc153e161a90/tessera/canonical.py)

## 5. Recommended sequencing

### First: make the next result trustworthy

1. Address 27/29/30 as bounded reliability investigations, coordinating index consistency with #12.
2. Establish 07/37/40/41 as one evaluation program under existing benchmark owners. Use current native capabilities and a fixed external reader; do not make the test harness depend on future Context Compiler delivery.
3. Launch 43 with a narrow use case: resuming project work across sessions or agent runtimes while preserving changed requirements and prior failures.

Deliverable: a dependable source/identity baseline and evidence that Tessera helps a real recurring task compared with raw-source retrieval.

### Second: reduce incorrect use of remembered information

Complete prerequisite temporal/provenance work already in #15/#16/#73/#137, then test 01/03/04/10/33. Keep uncertainty explicit: invalidating a dependency means “revalidate,” not “automatically conclude the opposite.”

Deliverable: lower stale-state, copied-evidence and extraction-loss errors without an unacceptable rise in abstention, latency or maintenance cost.

### Third: demonstrate experience transfer

Under #21, compare 18/19/21/22 and use 38/39 as regression controls. Store applicability and verified outcome evidence. Promote procedures only after held-out transfer tests; avoid treating one successful anecdote as a general rule.

Deliverable: fewer repeated failures and better task performance on future tasks at a measured total cost.

### Conditional expansion

Shared service/federation (23/24/34), broad connectors (44), skill promotion (20) and memory-pack ecosystems (45) should follow actual demand. Local single-user Tessera does not need a distributed platform to validate its core value.

The independent evaluation program can run alongside the existing governed delivery queue. This report does not authorize bypassing dependencies, audit checks or repository protections.

## 6. Five concrete experiment briefs

### X1 — Does memory construction earn its cost?

Compare raw Markdown/session retrieval, current Tessera, typed extraction and a derived context view. Cross representation with lexical and semantic retrieval where available. Fix reader, prompt, source snapshot and tokenizer; run equal evidence-token budgets. Include cold-build and warm-query cost separately. Measure task success, all-needed-evidence recall, factual support, latency and total model calls. Use held-out tasks to select the default. Do not compare equal top-k as if it meant equal context cost.

### X2 — Can a copied falsehood become a majority?

Create a source claim, paraphrases and summaries by multiple agents, a genuinely independent corroboration and a later correction. Preserve both known and missing lineage cases. Compare item dedup, source-level grouping and transitive origin grouping with targeted evidence recovery. Measure false-majority decisions and complementary evidence wrongly suppressed. Do not discard all records from one source: distinct facts in that source can each be necessary.

### X3 — Does a correction reach its consequences?

Construct source fact → derived insight → recommended procedure → compiled task context. Update or revoke one premise, including a late correction with an earlier effective date. Compare no propagation, direct invalidation and transitive dependency invalidation. Measure stale conclusions served, false invalidation, historical reconstruction and recomputation cost. Quarantine an unsupported conclusion pending review; preserve its historical existence.

### X4 — Does an agent learn the right lesson?

For matched tasks, collect externally verified successes and failures. Compare no memory, raw trajectories, success summaries and contrastive conditional lessons. Then change project and tool version. Measure repeated-error rate, positive transfer, negative transfer, constraint violations and memory overhead. Separate a useful correlation from a causal explanation. The executing agent verifies actions; Tessera stores the trace, outcome evidence and applicable lesson.

### X5 — Does more memory eventually make the agent worse?

Stream growing quantities of related and unrelated memories while probing old facts, rare exceptions and recent updates at fixed context budgets. Compare flat growth, relevance-only pruning and provenance-preserving consolidation with protected exceptions. Measure evidence reachability, task success, false certainty, index footprint and maintenance costs over time. A source that remains on disk but cannot be retrieved represents operational forgetting.

For all five, agree practical success margins and per-category floors before running. Report paired uncertainty and known dataset limitations. Use deterministic task assertions when available, human review for disputed cases, and a calibrated judge only for the remaining semantic judgments. “Tests pass” establishes implementation behavior; it does not establish product benefit.

## 7. Architectural boundaries for these experiments

- Source files remain authoritative and inspectable; generated memories have explicit lineage. Graphs, vectors, context packets and cached profiles remain derived.
- Keep the three semantic drawers: facts, preferences and insights. Epistemic status, skill applicability, ownership and verification are metadata or projections, not an excuse to duplicate canonical storage.
- Preserve the deterministic core and optional model boundary. New model-assisted methods should compete against cheap baselines and operate through explicit configuration.
- The consuming agent owns final reasoning, response and action execution. Tessera can expose evidence, conflicts, uncertainty, temporal state and applicability without becoming a general autonomous agent.
- Memory retrieval relevance, source authority, claim confidence, temporal validity and demonstrated utility are different quantities.
- Preserve losses and failures visibly. Empty extraction, failed extraction, rejected admission, no retrieval match, insufficient evidence and blocked access are distinct outcomes.

Avoid defaulting to a larger graph, more LLM agents, automatic forgetting, fixed newest-wins logic, uncontrolled self-editing, neural-memory training inside the core, or a shared cloud service before the relevant experiment and user need justify them.

## 8. AI-memory papers and reading order

The complete 28-paper review, limitations, opportunity-ID crosswalk and recommended reading order are preserved in [MEMORY_PAPERS_2026-09-07.md](MEMORY_PAPERS_2026-09-07.md). That review also records one supplementary limited-evidence paper inspected during the search. Canonical entries live in [REFERENCES.md](REFERENCES.md).

## 9. Other strategic options to revisit when demand justifies them

These are product branches, not prerequisites for the 48 experiments: native Windows/macOS release qualification; supported-version and security-update policy; encrypted multi-device synchronization; managed hosting; additional provider-store migration adapters beyond OKF; secure credential storage when configuration friction is measured; and multimodal ingestion preserving original asset references plus timestamp/bounding-box evidence. Existing #106 is a multimodal benchmark proposal, not a complete multimodal product contract. Treat each expansion as a separate demand, privacy, interoperability and operating-cost decision.

The first release already has publication/security requirements in #134. Extend those with maintained-release operations rather than proposing existing release controls as new work.


## 10. Open-issue inventory used for overlap checks

Snapshot taken on 7 September 2026. Open status is time-sensitive. The list preserves all 82 issue titles; the separate PR follows the table.

| Issue | Title | Lane |
|---|---|---|
| [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) | [Foundation F8] Incremental and idempotent indexing | Roadmap / research / release / documentation |
| [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) | [Foundation F9] Metadata Doctor and corpus diagnostics | Roadmap / research / release / documentation |
| [#14](https://github.com/LuigiFerronatto/TESSERA/issues/14) | [Epic M3] Typed relations and controlled graph expansion | Roadmap / research / release / documentation |
| [#15](https://github.com/LuigiFerronatto/TESSERA/issues/15) | [Temporal P1] Temporal model and state keys | Roadmap / research / release / documentation |
| [#16](https://github.com/LuigiFerronatto/TESSERA/issues/16) | [Temporal P1] Conflict resolution and supersession | Roadmap / research / release / documentation |
| [#17](https://github.com/LuigiFerronatto/TESSERA/issues/17) | [Adaptive P2] Query compiler and adaptive retrieval strategy | Roadmap / research / release / documentation |
| [#18](https://github.com/LuigiFerronatto/TESSERA/issues/18) | [Epic M1] LongMemEval adapters and TESSERA ablations | Roadmap / research / release / documentation |
| [#19](https://github.com/LuigiFerronatto/TESSERA/issues/19) | [Adaptive P2] Write gating and memory admission | Roadmap / research / release / documentation |
| [#20](https://github.com/LuigiFerronatto/TESSERA/issues/20) | [State P3] Evidence sufficiency, conflict status and abstention | Roadmap / research / release / documentation |
| [#21](https://github.com/LuigiFerronatto/TESSERA/issues/21) | [Learning P4] Experience traces, derived insights and utility feedback | Roadmap / research / release / documentation |
| [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) | [Experiment] Query-aware graph expansion with evidence budget | Roadmap / research / release / documentation |
| [#26](https://github.com/LuigiFerronatto/TESSERA/issues/26) | [Experiment] Relation confidence and edge validation | Roadmap / research / release / documentation |
| [#27](https://github.com/LuigiFerronatto/TESSERA/issues/27) | [Experiment] Source arbitration for memory, tools and documents | Roadmap / research / release / documentation |
| [#28](https://github.com/LuigiFerronatto/TESSERA/issues/28) | [Evaluation] Structured Evidence rendering ablation | Roadmap / research / release / documentation |
| [#32](https://github.com/LuigiFerronatto/TESSERA/issues/32) | [Experiment] Source authority, scope and instruction precedence | Roadmap / research / release / documentation |
| [#67](https://github.com/LuigiFerronatto/TESSERA/issues/67) | [P0 CI] TESSERA Quality Gate v2 — contracts and governance | Roadmap / research / release / documentation |
| [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) | [Foundation] Text ingestion coverage beyond Markdown | Roadmap / research / release / documentation |
| [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) | [Foundation] Structural segmentation without destroying source fidelity | Roadmap / research / release / documentation |
| [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) | [Intelligence] Harness adapter registry for textual agent instructions | Roadmap / research / release / documentation |
| [#72](https://github.com/LuigiFerronatto/TESSERA/issues/72) | [Intelligence] Instruction Resolver — applicability, scope and deterministic precedence | Roadmap / research / release / documentation |
| [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) | [Temporal] Versioned memory/source revision history | Roadmap / research / release / documentation |
| [#78](https://github.com/LuigiFerronatto/TESSERA/issues/78) | [Documentation] Remove project-specific references from legacy and deep-dive docs | Roadmap / research / release / documentation |
| [#80](https://github.com/LuigiFerronatto/TESSERA/issues/80) | [Documentation] Architecture diagrams and visual system | Roadmap / research / release / documentation |
| [#87](https://github.com/LuigiFerronatto/TESSERA/issues/87) | [Repository] Add standalone LICENSE and contribution guide | Roadmap / research / release / documentation |
| [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103) | [Evaluation] LongMemEval V1 frozen-evidence reader baseline | Roadmap / research / release / documentation |
| [#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) | [Evaluation] Versioned and calibrated LLM-as-a-judge contract | Roadmap / research / release / documentation |
| [#105](https://github.com/LuigiFerronatto/TESSERA/issues/105) | [Benchmark] LongMemEval V1 full-500 preregistered evaluation | Roadmap / research / release / documentation |
| [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) | [Benchmark] LongMemEval-V2 multimodal agent-memory adapter and small-tier evaluation | Roadmap / research / release / documentation |
| [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) | [M1 Onboarding] Verify clean local installation and CI bootstrap | Roadmap / research / release / documentation |
| [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) | [M1 CLI] Redesign the terminal experience as an inspectable product surface | Roadmap / research / release / documentation |
| [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) | [M1 MCP] Refactor MCP startup, contracts and operational robustness | Roadmap / research / release / documentation |
| [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121) | [M1 Skills] Define and package official TESSERA Skills | Roadmap / research / release / documentation |
| [#134](https://github.com/LuigiFerronatto/TESSERA/issues/134) | [M1 Release] Publish the first TESSERA distribution to PyPI | Roadmap / research / release / documentation |
| [#136](https://github.com/LuigiFerronatto/TESSERA/issues/136) | [QUMem P1] Validate typed F/P/I decomposition fidelity and 1-pass vs 3-pass extraction | Roadmap / research / release / documentation |
| [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) | [QUMem P1] Preserve source episode, supporting turns and temporal position for atomic memories | Roadmap / research / release / documentation |
| [#138](https://github.com/LuigiFerronatto/TESSERA/issues/138) | [QUMem P1] Make dynamic episode construction role-aware and continuity-driven | Roadmap / research / release / documentation |
| [#139](https://github.com/LuigiFerronatto/TESSERA/issues/139) | [QUMem P1] Represent multiple query-conditioned information needs before retrieval | Roadmap / research / release / documentation |
| [#140](https://github.com/LuigiFerronatto/TESSERA/issues/140) | [QUMem P1] Add bounded multi-query and multi-store retrieval planning | Roadmap / research / release / documentation |
| [#141](https://github.com/LuigiFerronatto/TESSERA/issues/141) | [QUMem P1] Implement structured query-conditioned state reconstruction (Fq / Tq / Iq) | Roadmap / research / release / documentation |
| [#142](https://github.com/LuigiFerronatto/TESSERA/issues/142) | [QUMem P1] Add a frozen end-to-end QUMem fidelity regression suite | Roadmap / research / release / documentation |
| [#143](https://github.com/LuigiFerronatto/TESSERA/issues/143) | [Evaluation] Add a QUMem-aligned personalized-memory and preference-evolution benchmark track | Roadmap / research / release / documentation |
| [#144](https://github.com/LuigiFerronatto/TESSERA/issues/144) | [QUMem P2] Expose validated assisted memory-construction and state contracts across Python / CLI / MCP | Roadmap / research / release / documentation |
| [#145](https://github.com/LuigiFerronatto/TESSERA/issues/145) | [Epic QUMem] Query-conditioned memory construction and state reconstruction | Roadmap / research / release / documentation |
| [#146](https://github.com/LuigiFerronatto/TESSERA/issues/146) | [QUMem Docs] Reconcile paper-fidelity claims with audited main and new Test Cards | Roadmap / research / release / documentation |
| [#157](https://github.com/LuigiFerronatto/TESSERA/issues/157) | [M2 Models] Add typed model profiles for embeddings, generation and reranking | Roadmap / research / release / documentation |
| [#158](https://github.com/LuigiFerronatto/TESSERA/issues/158) | [M2 Retrieval] Add optional local/cloud semantic embeddings and versioned semantic index | Roadmap / research / release / documentation |
| [#159](https://github.com/LuigiFerronatto/TESSERA/issues/159) | [M3 Retrieval] Evaluate optional local/cloud reranking over frozen candidate sets | Roadmap / research / release / documentation |
| [#160](https://github.com/LuigiFerronatto/TESSERA/issues/160) | [M2 Intelligence] Configure AI pipeline stages by capability with explicit fallbacks | Roadmap / research / release / documentation |
| [#161](https://github.com/LuigiFerronatto/TESSERA/issues/161) | [M2 Init UX] Add Local / Private Hybrid / Cloud intelligence presets | Roadmap / research / release / documentation |
| [#162](https://github.com/LuigiFerronatto/TESSERA/issues/162) | [M2 Diagnostics] Add model/pipeline doctor and capability readiness reporting | Roadmap / research / release / documentation |
| [#163](https://github.com/LuigiFerronatto/TESSERA/issues/163) | [M2 Local Models] Define explicit model artifact download, cache, device and offline lifecycle | Roadmap / research / release / documentation |
| [#164](https://github.com/LuigiFerronatto/TESSERA/issues/164) | [Epic Intelligence] Provider-agnostic retrieval and reasoning model stack | Roadmap / research / release / documentation |
| [#165](https://github.com/LuigiFerronatto/TESSERA/issues/165) | [M2 Local Generation] Evaluate local generative models for memory organization and assisted reasoning | Roadmap / research / release / documentation |
| [#166](https://github.com/LuigiFerronatto/TESSERA/issues/166) | [M1 CLI UX] Add unified human/plain/JSON renderers, dashboard, errors and terminal interaction system | Roadmap / research / release / documentation |
| [#167](https://github.com/LuigiFerronatto/TESSERA/issues/167) | [M2 Context] Add agent working-context bootstrap and task-state packets | Roadmap / research / release / documentation |
| [#168](https://github.com/LuigiFerronatto/TESSERA/issues/168) | [M2 Memory] Define the Long-Term Memory layer and durable-agent-memory contract | Roadmap / research / release / documentation |
| [#169](https://github.com/LuigiFerronatto/TESSERA/issues/169) | [M2 Context] Build the Context Compiler for minimum-sufficient agent state | Roadmap / research / release / documentation |
| [#170](https://github.com/LuigiFerronatto/TESSERA/issues/170) | [M2 Epic] Agent Cognitive Continuity — Long-Term Memory → Context → Agent | Roadmap / research / release / documentation |
| [#171](https://github.com/LuigiFerronatto/TESSERA/issues/171) | [M2 Agent API] Define the minimal agent-facing memory surface (search / context / evidence / remember / inspect) | Roadmap / research / release / documentation |
| [#176](https://github.com/LuigiFerronatto/TESSERA/issues/176) | [M2 AI Indexing P0] Add optional AI-assisted legacy corpus enrichment and semantic memory indexing | Roadmap / research / release / documentation |
| [#177](https://github.com/LuigiFerronatto/TESSERA/issues/177) | [M2 Integrations] Add CLI lifecycle hook adapters and normalized agent event capture | Roadmap / research / release / documentation |
| [#178](https://github.com/LuigiFerronatto/TESSERA/issues/178) | [UX Epic] End-to-end TESSERA onboarding, integration and memory lifecycle experience | Roadmap / research / release / documentation |
| [#179](https://github.com/LuigiFerronatto/TESSERA/issues/179) | [Research] Cross-system memory lifecycle and hook architecture — MemPalace, Mem0, MemOS, Letta and Graphiti | Roadmap / research / release / documentation |
| [#190](https://github.com/LuigiFerronatto/TESSERA/issues/190) | [M1 Integration UX] Add dual-path agent setup: direct `tessera integrate <runtime>` and guided `tessera mcp setup` | Roadmap / research / release / documentation |
| [#191](https://github.com/LuigiFerronatto/TESSERA/issues/191) | [M2 Conversation Import] Detect and import historical agent conversations as source evidence | Roadmap / research / release / documentation |
| [#192](https://github.com/LuigiFerronatto/TESSERA/issues/192) | [M2 Enrichment Runtime] Add resumable, incremental and cost-aware AI enrichment execution | Roadmap / research / release / documentation |
| [#193](https://github.com/LuigiFerronatto/TESSERA/issues/193) | [M1 Distribution] Package official agent integrations through Skills, plugins and MCP without duplicating memory semantics | Roadmap / research / release / documentation |
| [#194](https://github.com/LuigiFerronatto/TESSERA/issues/194) | [aw] Detection Runs | Lifecycle / automation |
| [#196](https://github.com/LuigiFerronatto/TESSERA/issues/196) | [M2 Hooks Core] Define a project-agnostic, runtime-agnostic lifecycle hook contract for TESSERA | Roadmap / research / release / documentation |
| [#199](https://github.com/LuigiFerronatto/TESSERA/issues/199) | [aw] Failed jobs: TESSERA PR Maintainer Audit | Lifecycle / automation |
| [#202](https://github.com/LuigiFerronatto/TESSERA/issues/202) | [aw] Failed jobs: TESSERA PR Maintainer Audit | Lifecycle / automation |
| [#204](https://github.com/LuigiFerronatto/TESSERA/issues/204) | [Interoperability] Add Open Knowledge Format (OKF) import/export compatibility without weakening TESSERA semantics | Roadmap / research / release / documentation |
| [#206](https://github.com/LuigiFerronatto/TESSERA/issues/206) | [lifecycle] Reconcile AGENTIC_GOVERNANCE.md with post-merge state of PR #198 | Lifecycle / automation |
| [#208](https://github.com/LuigiFerronatto/TESSERA/issues/208) | [lifecycle] Reconcile #203 project board sync into ROADMAP.md lifecycle matrix | Lifecycle / automation |
| [#209](https://github.com/LuigiFerronatto/TESSERA/issues/209) | [aw] Failed jobs: TESSERA PR Maintainer Audit | Lifecycle / automation |
| [#211](https://github.com/LuigiFerronatto/TESSERA/issues/211) | [lifecycle] Reconcile #155/#210 post-merge state and unblock #118 | Lifecycle / automation |
| [#213](https://github.com/LuigiFerronatto/TESSERA/issues/213) | [lifecycle] Reconcile #155 lifecycle after canonical merge (PR #210) | Lifecycle / automation |
| [#214](https://github.com/LuigiFerronatto/TESSERA/issues/214) | [aw] Failed jobs: TESSERA PR Maintainer Audit | Lifecycle / automation |
| [#215](https://github.com/LuigiFerronatto/TESSERA/issues/215) | [lifecycle] Reconcile #118 to READY after canonical #155 merge (PR #210, lifecycle PR #212) | Lifecycle / automation |
| [#217](https://github.com/LuigiFerronatto/TESSERA/issues/217) | [lifecycle] Reconcile #135 lifecycle to canonical VALIDATED state | Lifecycle / automation |
| [#220](https://github.com/LuigiFerronatto/TESSERA/issues/220) | [docs-drift] Weekly audit: docs/ROADMAP.md #155 status internally inconsistent (VALIDATED vs stale READY) | Lifecycle / automation |
| [#221](https://github.com/LuigiFerronatto/TESSERA/issues/221) | [lifecycle] reconcile #16 P0 containment lifecycle post-merge | Lifecycle / automation |

Open PR: [#222 — [lifecycle] Reconcile #16 P0 containment after PR #219](https://github.com/LuigiFerronatto/TESSERA/pull/222). Its lifecycle reconciliation does not itself add the full temporal-state semantics of #16.
