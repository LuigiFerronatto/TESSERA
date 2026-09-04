# PR Evolution Audit — Issue #155 initialization UX

Audited starting `main`: `51d7f6240dc094ef57ea0d42f38e69976a96d381`,
the fetched canonical main when branch `feature/155-init-ux` was created. Live
routing was #155 `IN_PROGRESS`, #135/#16/#120 `READY`, and #118's authoritative
issue routing `BLOCKED` on #155. The drifted #118 Project status was corrected
from `Ready` to `Blocked`; no downstream implementation was started.

## Lifecycle state

- **Decision:** `PENDING`
- **Implementation PR:** [#210](https://github.com/LuigiFerronatto/TESSERA/pull/210)
- **Candidate branch:** `feature/155-init-ux`
- **Canonical merge:** not merged
- **Benchmark applicability:** `SMOKE_ONLY`
- **Exact final head audit:** pending

No text in this candidate describes #155 as implemented or validated on main.
The final head SHA, hosted CI and independent Maintainer Audit decision must be
recorded in the PR/issue evidence before merge. A post-merge lifecycle change
must record the canonical merge independently from the candidate SHA.

## Capability lineage

| Issue / delivery | Canonical contribution consumed by #155 |
|---|---|
| #117 / PR #150 | project-local and explicitly named global configuration resolution |
| #153 / PR #173 / `2508676` | separate generated-memory store, source roots and derived index |
| #154 / PR #175 / `05ce0dd` | `SourceDiscoveryPlan`, classification, clustering, safety and ignore policy |
| #155 / PR #210 | display, selection, plan, confirmation, persistence and indexing orchestration |

The implementation does not duplicate scanning, ignore parsing or indexing.
It adds one application layer around the three existing canonical boundaries.

## Before architecture

```text
project/global choice
-> storage-only InitPlan
-> immediate config mutation
-> immediate store-only index
```

The old interactive path did not ask where generated memories should live as a
separate product concept, did not show discovered project knowledge, and had no
recommended/custom/memory-only selection. JSON/dry-run described only storage
mutation, not the source corpus or safety plan.

## Candidate architecture

```text
InitRequest
  -> resolve project/global scope
  -> #154 SourceDiscoveryPlan
  -> recommended/custom/memory-only selection
  -> InitializationPlan + preflight
  -> human or JSON rendering
  -> explicit confirmation when interactive
  -> Configuration v2 + explicit ignore edit
  -> canonical TesseraEngine selected-source index
```

`InitializationPlan` is frozen and deterministically serializable. It records
the config/store/index paths, selected project sources, source roots, discovery
counts/details, current and proposed configuration, config/ignore changes,
planned mutations, warnings and preflight problems. The generated-memory store
is always a readable source, but its files are reported separately from selected
existing project sources.

## Selection and safety

- Recommended mode takes only #154 `selected_by_default` safe Markdown.
- Custom mode expands safe project-relative file/directory choices into exact
  file allow-list entries.
- Memory-only mode uses the generated store as the sole readable source.
- Mandatory forbidden candidates, source boundary escapes, unsafe symlinks and
  unsupported/ignored files cannot be selected.
- Mixed clusters remain selectable through their safe children; forbidden
  children remain excluded.
- Exact explicitly re-included convenience paths can reach the canonical
  indexer without weakening `.git` or derived-index exclusions.
- No prompt, planner or index path invokes a model/provider.

## Mutation and recovery

Planning reads current state and performs deterministic writeability checks but
does not create config, store, ignore or index paths. Interactive confirmation
is after the complete plan. Cancel, EOF, Ctrl+C and dry-run stop before apply.

An existing project/global configuration is compared with the proposal.
Equivalent reruns have no config mutation; non-interactive material changes
require `--update-existing`. Schema-v1 migration remains store-only unless a
broader source policy is explicit.

`.tessera-ignore` persistence requires an explicit safe path, previews the
proposed text through #154's parser, uses an atomic text write, and re-runs
canonical discovery after persistence. Deselection alone never edits it.

Indexing begins only after configuration and any approved ignore mutation. A
post-config index failure returns a structured partial-state result instead of
claiming completion, and the same initialization can recover idempotently.

## Evidence plan

`tests/test_issue_155_init_ux.py` covers:

- recommended/custom/memory-only flows;
- interactive/non-interactive semantic plan equality;
- cancel and deterministic dry-run zero mutation;
- JSON-only output and actionable non-interactive failure;
- existing config no-op/material diff/update guard;
- conservative v1 migration;
- explicit ignore preview/apply/repeat behavior;
- mixed clusters and safe recursive re-inclusion;
- `.env`, `.git`, symlink and outside-project rejection;
- separate config/store/index writeability preflight;
- selected-source-only indexing and post-init path-free commands;
- truthful partial config/index failure and recovery;
- source byte equality and repeated-init idempotency;
- independently located external generated store plus project sources.

The #117/#153/#154 contract suites remain in the focused gate. TESSERA CI adds
an editable-install CLI smoke that compares dry-run/applied JSON source plans,
proves dry-run created no `.tessera` state, and checks source mutation count.
Python 3.9/3.12, distribution, full suite and deterministic sanity remain the
hosted merge gates. LongMemEval is skipped under `SMOKE_ONLY` because retrieval
ranking and evidence semantics did not change. Exact final-head evidence is
recorded on PR #210 so this candidate document does not create a self-referential
commit-SHA requirement.

## Scope boundaries

Not included: #118 clean installed-artifact onboarding certification, #119/#166
broad renderer/taxonomy work, #120 MCP robustness, #134 publication, #157–#165
model/intelligence capabilities, #176 enrichment, #177/#196 hooks, #190 agent
setup, #191 conversation import, incremental indexing or non-Markdown ingestion.

## Routing while candidate is active

```text
#155 IN_PROGRESS (PR #210)
#135 READY
#16  READY
#118 BLOCKED on #155
#120 READY
```

#118 may become `READY` only after #155 has a canonical merge and lifecycle
validation and only if no other blocker exists then.
