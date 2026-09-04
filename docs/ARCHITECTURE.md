# TESSERA — Architecture

> Current architecture reference for the Foundation on `main`.
>
> See also: [OVERVIEW.md](OVERVIEW.md), [FEATURES.md](FEATURES.md), [CONCEPTS.md](CONCEPTS.md), [QUERY_EXAMPLES.md](QUERY_EXAMPLES.md), [OUTPUT_CONTRACT.md](OUTPUT_CONTRACT.md), [ROADMAP.md](ROADMAP.md), and [research/](research/).

## Executive takeaway

TESSERA is a **text-first, agent-agnostic memory and evidence layer**. It is not a final-answer engine and it is not merely GraphRAG.

The current Foundation provides canonical understanding of heterogeneous text, stable knowledge/source identity, explicit graph structure, explainable multi-signal retrieval, query-aware evidence, source-version-aware provenance, a basic heuristic write-side sanitization gate, and CI/Test Card governance.

Advanced memory admission, query-aware graph expansion, relation confidence, temporal state, instruction resolution, authority, Evidence Arbitration and abstention remain experiments.

## Product contract

```text
AGENT
  │ natural-language information need
  ▼
TESSERA
  │ hides storage/index/graph/provenance mechanics
  ▼
STRUCTURED EVIDENCE
  │ evidence + source + relations + score/provenance
  ▼
AGENT
  └─ reasons / acts / answers
```

## Architectural invariants

- Source text remains the source of truth.
- Indexes, manifests, graph snapshots and evidence ledgers are derived/rebuildable.
- Exactly three semantic drawers exist: `facts`, `preferences`, `insights`.
- Non-memory documents may be indexed with `drawer: null`.
- `document_type`, scope, authority, confidence, temporal state, relations, quality and utility are facets, not new drawers.
- Retrieval relevance ≠ confidence ≠ authority ≠ relation confidence ≠ temporal validity ≠ utility.
- File path = location, not identity.
- Hash = version/fingerprint, not identity.
- No generative LLM is mandatory for the basic Foundation path.
- User source files are not silently rewritten during indexing.
- Public examples/fixtures are project-agnostic.
- Configuration discovery selects one store; configured v2 sources are an
  explicit per-project allow list, never an implicit corpus merge.

## Configuration and Engine boundary

Issue #117 implements [ADR 0003](adr/0003-configuration-and-store-discovery.md).
The Issue #153 candidate evolves the Engine handoff without changing selection
precedence:

```text
explicit path
  → canonical/deprecated environment
  → nearest exact project config
  → explicitly named global registry entry
  → actionable failure
                    ↓
          ResolvedConfiguration
        ┌───────────┼────────────┐
        ↓           ↓            ↓
   store.path    sources      index.path
   write only    read only    derived only
        └───────────┼────────────┘
                    ↓
             TesseraEngine
```

The resolver alone checks exact project configuration markers and registry
metadata. Engine does not discover repositories, prompt, read global
configuration, or select among projects. It iterates only the resolved source
roots and include patterns. Generated writes remain strictly contained by
`store.path`; source files are never copied or rewritten; `.tessera/index` is
excluded from source iteration and can be deleted/rebuilt independently.

Schema-v1 project configuration, direct `storage_dir`, environment selection,
and named-global stores conservatively use their prior store as the sole source.
They do not gain project README/docs/research files on upgrade. Explicit v2
source roots must remain physically contained by the project, except for the
exact generated-memory store when the user selected it outside the project;
symlink escapes fail safely. A named global store never absorbs current-project
sources.

Project source discovery is a separate read-only proposal layer:

```text
physical project root
  -> mandatory safety exclusions
  -> .tessera-ignore subset
  -> Markdown-only classification
  -> recommendation policy
  -> top-level location clusters
  -> SourceDiscoveryPlan
```

`tessera.source_discovery` scans only the supplied physical project root. It
skips all symlinks, performs metadata-first size/format checks, never traverses
ancestors/siblings/home, and returns explicit reason codes. Mandatory
exclusions run before ignore negation, so derived indexes, `.git`, special
files and high-confidence secret/key artifacts cannot become selectable.
Discovery does not mutate configured `sources`. Issue #155 consumes that plan
through a separate application boundary:

```text
InitRequest
  -> SourceDiscoveryPlan
  -> explicit source policy
  -> InitializationPlan + preflight
  -> human/JSON rendering
  -> confirmation (interactive only)
  -> config / explicit ignore mutation
  -> canonical Engine indexing of selected roots
```

Interactive, non-interactive, dry-run and JSON modes all serialize the same
`InitializationPlan`. Planning never constructs an Engine and therefore cannot
create a store or index. Cancel and dry-run stop before the apply boundary.
Project configuration includes the generated store as a readable source so new
durable memories remain indexable, while selected existing project sources are
stored as exact allow-list entries. The derived index is written only after
confirmation and config persistence. Source bytes are never rewritten.

## Episode decomposition failure boundary

Episode decomposition is a pure candidate-producing step before persistence:

```text
episode
  -> assisted structured extraction
       valid non-empty list -> assisted candidates
       valid []             -> intentional empty result
       expected provider failure
       parse/schema failure -> deterministic local fallback candidates
  -> canonical typed writer
  -> write gate
  -> durable memory
```

The fallback is local, offline, repeatable and provider-independent. It does
not retry, query another provider, use embeddings or write directly. Only the
current provider-invocation and parsing/schema failure boundary can select it;
unrelated programming errors propagate. Engine, Hook, CLI and MCP delegate to
the same implementation. Diagnostics distinguish `assisted` from
`deterministic_fallback` without changing the compatibility list-returning
Python API.

This repair does not redefine QUMem F/P/I semantics, episode construction or
lineage. The three canonical drawers remain `facts`, `preferences` and
`insights`, and all candidates use the same existing write gate.

## Current read / retrieval pipeline

```text
TEXT FILES
   ↓
DISCOVER
   ↓
PARSE + CANONICAL NORMALIZATION
   ├─ complete / partial / absent frontmatter
   ├─ document classification
   ├─ semantic drawer when applicable
   ├─ metadata_origin
   ├─ scope
   └─ explicit/local relations
   ↓
STABLE IDENTITY
   ├─ identity.id
   ├─ source.document_id
   ├─ source.path
   ├─ document_hash
   └─ content_hash
   ↓
GRAPH / INDEX
   ├─ memory/document nodes
   ├─ tag/entity structure
   ├─ explicit relations
   └─ lexical corpus / TF-IDF
   ↓
RETRIEVAL
   ├─ lexical TF-IDF
   ├─ token overlap
   ├─ title / ID relevance
   ├─ metadata relevance
   ├─ graph/PageRank structural signal
   └─ deterministic intent/type boost
   ↓
QUERY-AWARE EVIDENCE
   ├─ relevant paragraph when supported
   └─ None instead of arbitrary evidence when unsupported
   ↓
EVIDENCE LEDGER / PROVENANCE
   ├─ evidence_id
   ├─ source document identity
   ├─ source version hashes
   ├─ exact span when uniquely provable
   └─ freshness state
   ↓
STRUCTURED RETRIEVAL RESULT
```

## Current write path

The write path contains a **narrow deterministic security gate** governed by
[`WRITE_GATE_CONTRACT.md`](WRITE_GATE_CONTRACT.md):

```text
persistence format validation (`md` only)
   ├─ unsupported → deterministic failure, no mutation
   └─ supported
   ↓
portable memory-ID validation + resolved storage containment
   ├─ invalid/outside/symlink escape → reject, no mutation
   └─ contained destination
   ↓
candidate memory content
   ↓
WriteGatingEngine.evaluate()
   ├─ detection (known patterns / suspicious tags)
   ├─ optional deterministic transformation
   └─ admission: accept | accept_sanitized | reject | review
   ↓
admission finalized before mutation
   ├─ reject/review → no canonical side effect
   └─ accept/accept_sanitized
       ↓
atomic Markdown persistence + truthful security metadata
   ↓
derived registry/index/graph/Evidence Ledger updates
```

Markdown is the only canonical writable persistence format because it is the
format discovered by the current source iterator. Acknowledged writes are
therefore indexable after rebuild. JSON writing and arbitrary JSON ingestion
are not supported; unsupported format values fail before the security gate or
any filesystem/runtime mutation.

`content_changed` is derived from SHA-256 hashes of the exact UTF-8 original
payload and persistence candidate. The compatibility `sanitized` field is true
only for `accept_sanitized`. The current version emits no sanitized admission:
direct known hostile instructions are rejected, while quoted/documentary
examples are routed to review without canonical persistence. The schema keeps
`accept_sanitized` only for a future versioned, complete bounded transformation.
This gate does not claim comprehensive semantic prompt-injection protection;
#19 remains the separate evidence-aware memory-admission experiment.

This is different from roadmap #19:

```text
basic deterministic write admission  IMPLEMENTED in PR candidate #108; not on main
full evidence-aware memory admission  PLANNED (#19)
```

# 1. Canonical Metadata Layer

**Tracking:** Issue #9 / PR #3

TESSERA normalizes heterogeneous project text into one canonical representation before indexing.

```yaml
identity:
  id: project/charter
classification:
  document_type: memory
  kind: factual
  drawer: facts
source:
  document_id: doc_...
  path: project/charter.md
metadata_origin:
  drawer: inferred
```

Harness instructions remain orthogonal to semantic drawers:

```yaml
classification:
  document_type: harness_instructions
  kind: instruction
  drawer: null
```

This allows `CLAUDE.md`, `AGENTS.md` and `*.SKILL.md` to participate without being forced into facts/preferences/insights. Adapter/precedence behavior remains experimental (#71/#72/#32).

# 2. Stable identity model

```text
identity.id
→ persistent knowledge/memory identity

source.document_id
→ persistent source-document identity

source.path
→ current source location

document_hash / content_hash
→ current source/content version
```

Expected lifecycle:

```text
MOVE / RENAME
identity.id        SAME
source.document_id SAME
source.path        CHANGED
content_hash       SAME
```

```text
CONTENT EDIT
identity.id        SAME
source.document_id SAME
source.path        SAME
content_hash       CHANGED
```

Source revision history beyond the current version is a separate experiment (#73); stable hashes alone are not presented as a full immutable history.

# 3. Graph representation

TESSERA preserves explicit/local relations and graph structure, but the graph is **not the final relevance engine**.

```text
explicit relations
   ↓
graph
   ↓
PageRank / structural signal
   ↓
one component of retrieval ranking
```

Future relation intelligence must keep these separate:

```text
relation_type
≠ relation_origin
≠ relation_confidence
≠ query_relevance
```

Planned Test Cards: #14, #25, #26.

# 4. Explainable retrieval

**Tracking:** Issue #8 / PR #2

Current ranking combines inspectable signals:

```text
ranking
  ← lexical TF-IDF
  ← direct overlap
  ← title / ID
  ← metadata
  ← normalized relation/PageRank signal
  ← deterministic type/intent behavior
```

Recency is disabled by default because recent information is not necessarily current truth.

The sanity corpus intentionally contains a colloquial purpose paraphrase so lexical limitations remain visible. We do not add query-specific boosts to hide a bad ranking.

# 5. Query-aware Relevant Evidence

TESSERA foregrounds a query-specific paragraph when lexical support exists while preserving the full memory body.

```text
retrieved memory
├─ relevant_evidence
└─ full body
```

If evidence cannot be supported, `relevant_evidence` remains `None`.

The future four-state #20 contract is not implemented yet:

```text
sufficient
insufficient
conflicting
ambiguous
```

# 6. Evidence Ledger

**Tracking:** Issue #11 / PR #6

The Evidence Ledger is an immutable/rebuildable provenance substrate derived from source files and Canonical Metadata.

```yaml
evidence_id: ev_...
memory_id: project/charter
source:
  document_id: doc_...
  path: project/charter.md
  document_hash: sha256:...
  content_hash: sha256:...
span:
  start_line: 31
  end_line: 37
extraction:
  method: paragraph_lexical
```

It answers: **where did this evidence come from, and which source version supports it?**

It does not decide authority, truth, arbitration winner, query relevance or temporal validity. If evidence text occurs multiple times and the exact occurrence cannot be proven, the span is null rather than guessed.

# 7. Derived state and indexing

```text
SOURCE FILES
   ├─ canonical metadata
   ├─ identity manifest
   ├─ graph/index cache
   └─ evidence ledger
```

Derived state must be reconstructible from source files. Current indexing still uses coarse cache/rebuild semantics; **incremental/idempotent indexing remains #12**.

Two additional Foundation gaps are explicit rather than implied:

```text
#69 plain-text ingestion beyond Markdown
#70 structure-aware segmentation of long documents
```

# 8. Interface boundary

The Python engine is the semantic source of retrieval results. CLI and MCP are transports/renderers around that contract.

Direct Engine retrieval, CLI JSON query output and MCP `query_memories()` use
the same lossless evidence contract; #68 closed that parity gap. The typed-store
MCP helper `query_store()` still uses a smaller hand-projected shape and is not
the canonical direct-query contract.

# 9. Optional orchestration boundary

The binding decision is
[`ADR 0001`](adr/0001-core-vs-optional-llm-boundary.md). **CURRENT:** the
repository contains a legacy assisted orchestration path that makes LLM calls
for information-need analysis, retrieval-query planning and context synthesis
around deterministic Engine retrieval. It preserves retrieval hits as
`raw_memories`, but generated context has no machine-checked grounding envelope.

**TARGET:** core retrieval ends at structured evidence with provenance. Optional
planner, consolidation and reader adapters consume that contract; the consuming
agent owns cognition, final-answer policy and abstention. Benchmark judges are
benchmark-only infrastructure. O0–O4 in the ADR constrain future work and are
not all implemented today.

```text
CURRENT direct path
Python / CLI query / MCP query_memories
→ TesseraEngine
→ deterministic retrieval
→ structured evidence + provenance

CURRENT explicit assisted path
CLI start / MCP pipeline / task hook
→ application llm_fn or explicitly selected deprecated compatibility adapter
→ LLM need analysis + planning
→ deterministic retrieval
→ LLM-generated context + raw_memories
```

Current limitations include an eager task-hook wrapper during MCP startup and
assisted MCP signatures that cannot yet carry the full adapter selection
envelope. Issue #120 owns that lifecycle refactor. Generic startup performs no
project-specific provider probing, and compatibility failures never become raw
prompt output.

# 10. CI and experimental governance

**Tracking:** Issue #10 / PR #4, governance PRs, and #67 for Quality Gate v2.

```text
Issue / Test Card
→ implementation PR
→ unit / contract tests
→ CLI smoke
→ sanity evaluation
→ evidence + learnings
→ KEEP | ITERATE | REVERT | DROP | DEFER
```

Sanity metrics are regression indicators, not competitive benchmark claims.

## Current module map

| Module | Current role |
|---|---|
| `tessera/canonical.py` | Canonical parsing, classification and stable metadata semantics |
| `tessera/engine_core.py` | Write path, indexing, graph construction and core retrieval |
| `tessera/engine.py` | Evidence-aware facade integrating retrieval with provenance |
| `tessera/evidence.py` | Evidence records, ledger, freshness and span/provenance helpers |
| `tessera/security.py` | Basic deterministic write-side hostile-pattern audit/sanitization |
| `tessera/conflict.py` | Existing compatibility conflict logic; future state/arbitration redesign is experimental |
| `tessera/models.py` | Domain models for memory/write paths |
| `tessera/config.py` | Closed v1/v2 project and global schemas, bounded discovery, and one resolved store/source/index boundary |
| `tessera/cli.py` | Human CLI surface |
| `tessera/mcp_server.py` | MCP transport; direct `query_memories()` has #68 parity, while legacy assisted-hook startup is an ADR 0001 deviation |
| `tessera/orchestrator.py` | Legacy optional assisted planning/synthesis path governed by ADR 0001 |
| `benchmarks/sanity/` | Deterministic project-agnostic regression evaluation |

## Implemented vs planned

Implemented Foundation:

```text
canonical text normalization
stable memory identity
stable source-document identity
explicit relation parsing
graph representation
explainable multi-signal ranking
query-aware relevant evidence
Evidence Ledger / provenance
basic heuristic write-side sanitization
CI + sanity evaluation
Test Card governance
```

Planned / experimental:

```text
#68 Engine / CLI / MCP direct-query contract parity (implemented)
#12 incremental/idempotent indexing
#69 text ingestion coverage
#70 structural segmentation
#13 metadata doctor
#14/#25/#26 controlled relations/graph intelligence
#15 temporal model + state keys
#71/#72 harness adapters + instruction resolver
#73 source/memory revision history
#16 conflict/supersession
#27 Evidence Arbitration
#32 source authority + instruction precedence
#20 four-state evidence sufficiency/abstention
#18 LongMemEval
#28 rendering ablation
#17 adaptive retrieval
#74 core vs optional LLM orchestrator boundary (ADR accepted)
#19 evidence-aware memory admission
#21 experience learning / utility feedback
```

## Target architecture — only if experiments justify it

```text
QUERY
  ↓
Candidate Retrieval
  ↓
Seed Evidence
  ↓
Query-Aware Graph Expansion
  ↓
Relation Reliability
  ↓
Temporal Validity / State Keys
  ↓
Authority / Scope / Instruction Resolution
  ↓
Conflict Detection
  ↓
Evidence Arbitration
  ↓
Evidence Status
  ↓
Structured Renderer
  ↓
CONSUMING AGENT
```

This is roadmap architecture, not current runtime behavior. Individual layers may be simplified or dropped if their Test Cards do not show measurable value.
