# #155 — Safe project initialization and source selection

| Field | Value |
|---|---|
| Issue | [#155](https://github.com/LuigiFerronatto/TESSERA/issues/155) |
| Record status | `IN_PROGRESS` |
| Capability type | `CLI_ONBOARDING` |
| Pull request | Pending |
| Branch | `feature/155-init-ux` |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-04 |

## In one sentence

TESSERA can turn safe project-source discovery into one reviewable plan, then
configure and index exactly that plan only after explicit approval.

## What problem existed?

Configuration v2 separated generated memories, readable sources and the
derived index, while source discovery safely classified project candidates.
The old `init` command did not connect those contracts: it configured a
store-only corpus and indexed immediately, without source selection or a
complete source-aware plan.

## How did TESSERA behave before?

```text
choose project/global store
-> print storage mutation summary
-> write config
-> index store only
```

Project README, documentation and other recommended knowledge could only be
added by manually editing YAML.

## What changed or is being tested?

The candidate delivery adds a first-class `InitializationPlan` and keeps its
planning and apply phases separate:

```text
resolve scope and generated-memory destination
-> consume #154 SourceDiscoveryPlan
-> recommended / custom / memory-only selection
-> preflight config, store, sources, ignore and index
-> render the complete plan
-> confirm
-> persist configuration and explicit ignore edit
-> invoke canonical indexing with selected source roots
```

The same plan drives interactive, non-interactive, dry-run and JSON modes.

## How does it work now? — candidate, not yet on main

Interactive project setup prefers the current project, asks where newly
generated durable memories belong, displays the #154 groups and safety counts,
asks for a source policy, and prints the complete plan. A negative response,
Cancel, EOF or Ctrl+C stops before the apply boundary.

Non-interactive project setup requires `--sources recommended`, `custom`, or
`memory-only`. Custom mode accepts repeatable safe project-relative `--source`
paths. Mandatory forbidden candidates, symlinks and boundary escapes fail before
mutation. `--dry-run` validates the plan without creating config, store, ignore
or index state. `--json` emits only a machine-readable envelope derived from
the same plan.

Existing configuration is loaded and compared. A non-interactive material
change requires `--update-existing`; an equivalent rerun has no configuration
change. Schema-v1 input stays store-only unless the caller explicitly selects
a broader policy.

Deselection is one-run-only. A `.tessera-ignore` change exists only when a
selectable path is explicitly named with `--persist-exclusion`; the proposed
text is previewed through #154's canonical parser before apply and discovery is
re-run after persistence.

## Concrete example

```bash
tessera init --project . --store memories \
  --sources recommended --dry-run

tessera init --project . --store memories \
  --sources custom --source README.md --source docs \
  --non-interactive
```

The plan distinguishes:

```text
Generated memories   ./memories
Knowledge sources    README.md + docs/*.md
Derived index        ./.tessera/index
Source files changed 0
```

## How was it validated?

`tests/test_issue_155_init_ux.py` covers deterministic zero-mutation dry-run,
JSON-only output, recommended/custom/memory-only policies, forbidden and
symlink rejection, mixed safe/forbidden clusters, explicit ignore persistence,
existing-config diff/no-op behavior, schema-v1 migration, unwritable preflight,
selected-source indexing, partial index failure, external generated stores,
idempotency and source byte equality.

Focused #117/#153/#154/#155 validation currently passes. Full-suite, clean-copy,
Python 3.9/3.12, smoke, sanity, distribution and exact-head CI evidence will be
recorded on the pull request before a final decision.

## What improved?

- A user sees the complete realistic plan before mutation.
- Scripts and CI can declare the same decisions without a pseudo-TTY.
- Generated memory, readable sources and derived index remain separate.
- #154 policy remains the only source scanner and ignore parser.
- Indexing happens only after planning, confirmation and configuration.
- Source files remain byte-identical through init and repeat init.

## What remains unimplemented?

This card does not add a broad Rich/Textual renderer, AI enrichment, model
profiles, semantic embeddings, reranking, incremental indexing, MCP setup,
runtime hooks, agent integration, clean-room onboarding certification, PyPI
publication or non-Markdown ingestion.

## What is unlocked next?

#118 remains blocked until this candidate is canonically merged and lifecycle
validation is complete. #120 remains independently ready. No downstream card
is started by this implementation branch.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #155](https://github.com/LuigiFerronatto/TESSERA/issues/155) |
| Pull request | Pending |
| Starting main | `51d7f6240dc094ef57ea0d42f38e69976a96d381` |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Pending exact-head audit |
| Benchmark record | `SMOKE_ONLY`; LongMemEval not required |
| PR Evolution Audit | Pending |

## Evolution

```text
#153 store / sources / index
-> #154 discover / classify / group / explain
-> #155 select / plan / confirm / persist / index
-> #118 clean-room onboarding validation after canonical merge
```
