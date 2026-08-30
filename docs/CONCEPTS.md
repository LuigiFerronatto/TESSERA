# TESSERA — Core Concepts

This glossary defines the terms that should remain stable across code, documentation, Test Cards and benchmarks.

## Memory vs source document

A **memory/knowledge object** is the conceptual item TESSERA retrieves.

A **source document** is the physical text file that supports that object.

They are intentionally not the same identity.

```text
identity.id
→ persistent knowledge/memory identity

source.document_id
→ persistent source document identity

source.path
→ current location of the source

content/document hashes
→ source version fingerprints
```

---

## Drawer

A semantic drawer is one of exactly three categories:

```text
facts
preferences
insights
```

These are the only primary semantic drawers.

A harness instruction, README, experiment record or reference document may be indexed with `drawer: null`.

That does not create a new drawer.

---

## Document type

`document_type` describes what kind of text artifact a source is.

Examples:

```text
memory
harness_instructions
skill_instructions
project_context
decision_record
experiment_record
report
reference
```

Document type is orthogonal to semantic drawer.

---

## Kind

`kind` is a more specific behavioral/semantic classification used by the current system and compatibility layer.

Examples include:

```text
factual
preference
procedural_anchor
instruction
```

Do not infer an additional semantic drawer from `kind`.

---

## Scope

Scope describes where a piece of knowledge/instruction applies.

This becomes especially important for harness documents such as:

```text
CLAUDE.md
AGENTS.md
*.SKILL.md
```

Future authority/precedence work (#32) will test how document type + scope + validity should interact.

---

## Relevance

Retrieval relevance answers:

> How useful is this item for the current query?

The current final retrieval score exists to order candidates.

It must not be treated as truth, confidence or authority.

---

## Confidence

Confidence answers a different question:

> How certain are we about this memory, relation or assessment?

Confidence may be missing/null when TESSERA has no evidence to justify a value.

The Foundation explicitly avoids inventing `confidence: high` for metadata that did not provide it.

---

## Authority

Authority answers:

> How authoritative is this source for this subject/scope?

Authority is not yet a completed runtime policy. It is tracked experimentally in #32.

Example future distinction:

```text
CLAUDE.md instruction
→ potentially authoritative within its applicable repository scope

learning note
→ useful evidence, but not automatically authoritative for instructions
```

Authority must remain separate from retrieval relevance and confidence.

---

## Utility

Utility represents whether a memory has proven useful in downstream work.

It is a future learning dimension, not a truth signal.

```text
high utility
≠ high confidence
≠ high authority
```

Tracked under the later experience/learning work (#21).

---

## Relation type

Relation type answers:

> What does this edge mean?

Future controlled relation types may include:

```text
related_to
supports
contradicts
supersedes
evolved_from
caused_by
resolved_by
derived_from
```

Only the relation foundation exists today. Rich typed-relation behavior is experimental (#14/#26).

---

## Relation origin

Relation origin answers:

> Where did the edge come from?

Possible future classes:

```text
explicit
inferred
derived
```

Examples:

```text
explicit
→ frontmatter / wikilink / human-authored declaration

inferred
→ lexical / semantic / structural inference

derived
→ deterministic temporal/conflict rule
```

Tracked in #26.

---

## Relation confidence

Relation confidence answers:

> How strongly do we believe the edge itself is correct?

This is distinct from query relevance.

```text
edge confidence = 0.99
query-edge relevance = 0.08
→ trustworthy relation, probably useless for this query
```

TESSERA's roadmap explicitly avoids adding relation confidence directly to the default final retrieval score.

---

## Query relevance of a relation

Query-edge relevance answers:

> Is following this relation useful for this specific query?

This is the core hypothesis behind query-aware graph expansion (#25).

```text
relation exists
≠ relation should be traversed
```

---

## Relevant Evidence

`relevant_evidence` is a query-specific snippet/paragraph selected from a retrieved memory.

It is not a replacement for the original memory.

Conceptually:

```text
result
├── relevant_evidence
└── full body
```

If no paragraph meets the current evidence heuristic, it can be `None`.

---

## Evidence Record

An Evidence Record is a deterministic provenance object derived from Canonical Metadata.

It answers:

> Which source document/version/span supports this memory or query-specific evidence?

Current fields include:

```text
evidence_id
memory_id
source.document_id
source.path
source.document_hash
source.content_hash
source.format
span
fingerprint
extraction method
```

---

## Evidence Ledger

The Evidence Ledger is the rebuildable collection of Evidence Records.

It is **not** the source of truth; source files are.

It should remain a provenance substrate rather than absorbing query-time decisions.

---

## Evidence Assessment

Planned concept, not implemented runtime behavior.

Evidence Assessment would attach inspectable facets such as:

```text
authority
confidence
temporal validity
source type
```

to a piece of evidence without rewriting its provenance record.

This is part of #27/#32.

---

## Evidence Arbitration

Planned concept tracked in #27.

Evidence Arbitration asks:

> When multiple evidence sources disagree, can TESSERA expose the conflict and prefer one only when deterministic rules justify it?

It must not hide unresolved disagreement simply to produce a cleaner result.

---

## Evidence status

Planned concept tracked in #20.

The current experimental contract uses four states:

```text
sufficient
insufficient
conflicting
ambiguous
```

They represent different control-flow conditions for the consuming agent.

```text
sufficient   → continue
insufficient → search / expand
conflicting  → inspect provenance / arbitration
ambiguous    → verify / ask / tool call
```

This classifier is not implemented yet.

---

## Temporal validity

Temporal validity is not equivalent to document recency.

Future temporal modeling (#15) distinguishes concepts such as:

```text
occurred_at
observed_at
valid_from
valid_until
recorded_at
indexed_at
```

Core rule:

```text
event time
≠ truth validity
≠ time TESSERA learned/indexed the information
```

---

## State key

A future `state_key` groups memories that represent different versions of the same state.

Example:

```yaml
state_key: lao.runtime.strategy
```

This enables deterministic temporal/supersession experiments without relying on generic recency.

Tracked in #15/#16.

---

## Provenance vs assessment vs decision

One of the most important TESSERA invariants is:

```text
PROVENANCE
≠ AUTHORITY
≠ CONFIDENCE
≠ TEMPORAL VALIDITY
≠ QUERY RELEVANCE
≠ ARBITRATION DECISION
```

If these dimensions become one number, TESSERA loses auditability.

---

## Source of truth vs derived artifacts

Primary:

```text
source text files
```

Derived/rebuildable:

```text
canonical representations
identity manifest
index/cache
graph representation
evidence ledger
benchmark artifacts
```

Derived artifacts should never silently become a competing authoritative source.

---

## Test Card

A Test Card is the unit of architectural decision-making in TESSERA.

It contains:

```text
hypothesis
baseline
experiment
metrics
success/failure signals
evidence
learnings
decision
```

Possible decisions:

```text
KEEP
ITERATE
REVERT
DROP
DEFER
```

This allows a technically successful feature to be dropped if it does not improve the measured system.
