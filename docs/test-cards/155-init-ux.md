# #155 — Safe project initialization and source selection

| Field | Value |
|---|---|
| Issue | [#155](https://github.com/LuigiFerronatto/TESSERA/issues/155) |
| Record status | `VALIDATED` |
| Capability type | `CLI_ONBOARDING` |
| Pull request | [#210](https://github.com/LuigiFerronatto/TESSERA/pull/210) |
| Branch | `feature/155-init-ux` |
| Final candidate | `cf9f9c754becb87923c5a5c6bad4c3172cc9f344` |
| Merge commit | `4c112195f1572bf352d1cc6a1042c69711381da8` |
| Decision | `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-09-04 |

## In one sentence

TESSERA now turns safe project-source discovery into one reviewable initialization plan, then configures and indexes exactly that plan only after explicit approval.

## What problem existed?

Configuration v2 and safe discovery existed, but no single initialization
contract connected source selection, a reviewable plan, confirmation and
selected-source indexing.

## How did TESSERA behave before?

Before #155, Configuration v2 and safe discovery existed, but `tessera init` still behaved as a storage-oriented flow:

```text
choose project/global store
→ print storage mutation summary
→ write config
→ index store only
```

Project README, documentation and other recommended knowledge had to be added manually to configuration.

## What changed or is being tested?

The merged implementation adds a first-class `InitializationPlan` and keeps planning separate from mutation:

```text
resolve scope and generated-memory destination
→ consume #154 SourceDiscoveryPlan
→ recommended / custom / memory-only selection
→ preflight config, store, sources, ignore and index
→ render complete plan
→ confirm
→ persist Configuration v2 and any explicitly approved ignore edit
→ invoke canonical selected-source indexing
```

Interactive, non-interactive, dry-run and JSON modes use the same semantic plan.

## How does it work now?

Planning is side-effect free. Apply begins only after the complete plan is
accepted, persists the approved configuration and exclusions, and then indexes
exactly the selected sources.

### Safety invariants

- Generated memories, readable sources and the derived index remain distinct.
- `--dry-run`, Cancel, EOF, Ctrl+C and negative confirmation mutate no canonical state.
- Source files remain unchanged.
- Forbidden, escaping and unsafe symlink sources are rejected before mutation.
- `.tessera-ignore` persistence is explicit and reuses #154 parsing semantics.
- Existing material configuration changes require explicit confirmation or `--update-existing`.
- No provider, model or network dependency was introduced.

## How was it validated?

The final candidate `cf9f9c754becb87923c5a5c6bad4c3172cc9f344` received an independent Maintainer Audit decision of `KEEP` with no supported P0/P1 findings.

Exact-head evidence recorded on PR #210 includes:

- focused #117/#153/#154/#155 suite: `89 passed`;
- Python 3.9 clean-worktree suite: `502 passed, 5 skipped`;
- Python 3.12 clean-worktree suite: `502 passed, 5 skipped`;
- successful distribution build and installed-wheel smoke;
- deterministic sanity unchanged: Hit@1 `0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence hit rate `1.00`;
- source byte/hash equality across init/index/doctor/query/repeat init;
- `source_files_modified: 0`;
- LongMemEval correctly skipped under `SMOKE_ONLY` because retrieval/ranking/evidence semantics did not change.

PR #210 was canonically merged into `main` as `4c112195f1572bf352d1cc6a1042c69711381da8` and Issue #155 closed as completed.

## Concrete example

```bash
tessera init --project . --store memories/generated \
  --sources recommended --non-interactive

tessera init --project . --store memories/generated \
  --sources custom --source README.md --source docs --non-interactive

tessera init --project . --store memories/generated \
  --sources memory-only --non-interactive

tessera init --project . --store memories/generated \
  --sources recommended --dry-run --json
```

## What improved?

Users can see and approve one complete source-aware initialization plan, and
automation receives the same plan as the interactive flow. Dry-run and cancel
remain non-mutating, while apply indexes only explicitly selected safe sources.

## What remains unimplemented?

This card does not implement:

- #118 clean-room release certification;
- #119/#166 broader CLI presentation architecture;
- #120 MCP robustness;
- #134 PyPI publication;
- #157–#165 intelligence/model stack;
- #176 AI enrichment;
- #177/#196 lifecycle hooks;
- #190 agent-integration setup;
- #191 conversation import;
- incremental indexing or non-Markdown ingestion.

## What is unlocked next?

#118 declared #155 as its only active blocker. With #155 now canonically validated, #118 is eligible to transition from `BLOCKED` to `READY` after routing/board reconciliation.

This does not change execution order. Queue remains historical/ordinal, and #135 remains the next implementation card at Queue #2.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [Issue #155](https://github.com/LuigiFerronatto/TESSERA/issues/155) |
| Pull request | [PR #210](https://github.com/LuigiFerronatto/TESSERA/pull/210) |
| Starting main | `51d7f6240dc094ef57ea0d42f38e69976a96d381` |
| Final candidate | `cf9f9c754becb87923c5a5c6bad4c3172cc9f344` |
| Canonical merge | `4c112195f1572bf352d1cc6a1042c69711381da8` |
| Decision | `KEEP` |
| Benchmark record | `SMOKE_ONLY`; LongMemEval not required |
| PR Evolution Audit | [PR_EVOLUTION_155.md](../PR_EVOLUTION_155.md) |

## Evolution

```text
#153 store / sources / index VALIDATED
→ #154 discover / classify / group / explain VALIDATED
→ #155 select / plan / confirm / persist / index VALIDATED
→ #118 clean-room onboarding READY after routing reconciliation
```
