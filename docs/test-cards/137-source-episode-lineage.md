# 137 — Source episodes and atomic-memory lineage

| Field | Value |
|---|---|
| Issue | [#137](https://github.com/LuigiFerronatto/TESSERA/issues/137) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | [Draft #297](https://github.com/LuigiFerronatto/TESSERA/pull/297) |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

Automatically decomposed memories keep their actual source episode and validated
turn references, so an auditor can inspect what was cited without treating a
memory's position as truth or temporal validity.

## What problem existed?

Canonical `20814a47ec0f72d7bea0639e0b057df1ecf5cded` retained an `episode_id`
string but no independently durable dialogue source. Decomposed candidates
contained only type/content, and automatic writes discarded supporting turns.
Existing source-document/version evidence described the atomic note itself.

## How did TESSERA behave before?

The same frozen five-candidate fixture had zero inspectable episode links,
zero of six supporting references retained, and no source-turn evidence spans.
Index rebuilds could not restore information that was never persisted. The
baseline is a real clean checkout of the canonical base, not an emulation.

## What changed or is being tested?

`EpisodeTurn` and `Episode.from_turns()` accept actual ordered positions, roles,
timestamps and content. Source episodes are no-overwrite Markdown records in
`_episodes/`. Each automatic write passes through the existing gate, references
that source/version and records validated supporting positions plus exact spans
through the existing EvidenceRecord contract. Canonical lineage is a projection
of native fields; it is not another source of truth.

## How does it work now? — CANDIDATE, NOT MERGED

Turn-aware candidates require ordered, unique, positive, source-bounded IDs.
Invalid references fail before any write. `temporal_position` is the last cited
position within the episode; no validity fields or automatic supersession are
introduced. Engine/CLI JSON/MCP retrieval retains lineage with a fresh status.
Source inspection works without an index. Cache schema 3 forces stale caches
to rebuild. Manually supplied notes keep their previous behavior.

Legacy section-only automatic inputs retain their exact sections and report
`episode_only_no_source_turns` with empty support/null position. Actual
interaction IDs are never invented from summaries. Semantic support is not
proven by structural reference validation.

## Concrete example

A source with assistant rationale at position 32 and user confirmation at 34
can support a preference with `provenance_turns: [32, 34]` and
`temporal_position: 34`. The original turns remain inspectable with their roles
and available timestamps. The source-version/span references survive deleting
and rebuilding the index. Position 99 is rejected if it does not exist.

## How was it validated?

`tests/test_episode_lineage.py` covers real ordered/sparse positions, multiple
supports, duplicate-content exact spans, source immutability, malformed/forged
references, unsupported IDs, source loss/change, index/result parity, legacy
manual APIs, byte-exact CRLF/Unicode content, path containment and gate behavior.
The local full regression run passed 607 tests with 5 tooling-only skips;
final exact-candidate counts and remote CI are recorded in the draft PR.

The frozen structural audit uses no model/provider and includes disjoint spans,
assistant rationale plus user confirmation, and preferences in different
episodes. It measures references already supplied by the test double, never
semantic precision. [Baseline](../evidence/137/baseline.json) and
[candidate](../evidence/137/candidate.json) bind the shared fixture checksum and
runtime-Python hash; the candidate report's checkout revision is its starting
base, with the runtime hash identifying the measured changes.

| Structural metric | Canonical baseline | Candidate |
|---|---:|---:|
| Inspectable source-episode linkage | 0/5 | 5/5 |
| Supporting references retained | 0/6 | 6/6 |
| Provable turn spans retained | 0/6 | 6/6 |
| Write/index/rebuild/result lineage parity | 0/5 | 5/5 |
| Lineage loss after initial persistence | Not measurable | 0/5 |
| Source + atomic Markdown bytes | 3,613 | 13,192 |
| Decomposition prompt UTF-8 bytes | 2,576 | 4,493 |

The storage increase is 9,579 bytes for this tiny fixture, including 2,413
source bytes. This is a real cost, not a performance improvement claim.
Synthetic retrieval sanity preserves baseline Hit@1 0.75, Hit@3/5 1.0,
MRR 0.875, evidence hit rate 1.0, and the missing-evidence guard.
Exact-head REQUIRED LongMemEval dev-50 remains a separate remote gate.

## What improved?

An auditor can navigate from a derived claim to an actual preserved source
version and ordered supporting turns. Invalid support cannot quietly become
invented evidence. Lost or changed sources are diagnosed rather than repaired
from derived memories. Legacy inputs remain usable with explicit limitations.

## What remains unimplemented?

Supporting-turn semantic precision/recall and preference-trajectory accuracy
remain unmeasured without reviewed labels and real extraction. Boundary
classification (#138), one-pass/three-pass semantics (#136), temporal state
(#15), legacy-source enrichment (#176), version history (#73) and write receipts
(#263) remain separate. This PR does not promote an unmerged candidate to KEEP
or unlock dependent issues. Python exposes turn ingestion/source inspection;
new CLI/MCP turn-input or inspection operations are not added.

## What is unlocked next?

After human review, exact-head validation and canonical merge, #136/#138/#176
can reuse this source/turn model and EvidenceRecord contract. No dependent
runtime work should assume this unmerged implementation is canonical.

## Technical provenance

- Canonical base: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Hard prerequisite #135: PR [#216](https://github.com/LuigiFerronatto/TESSERA/pull/216), merge `c324ac2f46d48f7b49769b2fea9df0a2a93b42de`, `KEEP`
- [Source/temporal/output contract](../EPISODE_LINEAGE.md)
- [Reproducible structural runner](../../benchmarks/lineage/README.md)
- No provider credentials, model download, paid call, merge or deployment
- Rollback: revert the candidate; preserve `_episodes/` as source evidence and rebuild derived caches. Older code ignores added frontmatter, but will no longer validate/expose lineage
- Post-merge: record canonical merge, reconcile decision/roadmap/stage and reevaluate declared dependencies only

## Evolution

Source-version-aware notes + #135 fallback integrity
→ selected #137 candidate adds independently durable source/turn lineage
→ structural retention measured; semantic quality remains explicitly unmeasured
→ human/CI/benchmark review before any canonical KEEP decision
