# PR Evolution Audit — Issue #154 safe source discovery

Audited starting `main`: `8f1c0c19a04ec4bde686b124389eb17a61856de0`,
the fetched canonical main when branch `test-card/154-safe-source-discovery`
was created. No open pull request overlapped #154. Live routing was #154
`READY`, #155 `BLOCKED` on #154, #118 `BLOCKED` on #154/#155, and #134
`BLOCKED` on #118 plus #87.

## Capability lineage

| Issue | Canonical contribution retained by #154 |
|---|---|
| #92 | Write admission/path containment remains independent from readable candidates. |
| #93 | One selected legacy store remains the complete implicit corpus across surfaces. |
| #95 | Generic runtime remains project-agnostic; legacy compatibility is explicit. |
| #117 | Physical project root and deterministic project/global configuration selection. |
| #153 | `store.path` writes, explicit `sources` read/index, and `index.path` derived state; canonical squash merge `2508676d472088733702b6ed920fc829df9a7681`. |
| #154 | Safely discover/classify additional project candidates without selecting them. |
| #155 | Future display/select/confirm/persist/index workflow; not implemented here. |

#153 and #154 are separate deliveries:

```text
#153 = WHAT paths can be configured as store / sources / index
#154 = HOW project source candidates are safely discovered / classified
#155 = HOW a user selects and confirms those candidates
```

The #153 candidate and canonical merge remain one `CONFIGURATION_V2` delivery;
none of that capability is counted again as #154.

## Before architecture

```text
ResolvedConfiguration
  -> store.path
  -> explicit sources
  -> index.path

safe project-wide candidate proposal -> absent
```

## Candidate architecture

```text
project root
  -> physical containment
  -> mandatory exclusions
  -> .tessera-ignore
  -> Markdown/size/readability policy
  -> recommendation classification
  -> top-level clusters
  -> SourceDiscoveryPlan
```

The implementation is isolated in `tessera/source_discovery.py`. The public
module-level boundary is `discover_sources(project_root, configuration=None)`
or `discover_sources_for_configuration(resolved_configuration)`. It returns
frozen, versioned data objects with `to_dict()` and performs no UI or mutation.

## Classification and clustering contract

`RECOMMENDED` and `SUPPORTED` are selectable Markdown candidates. `IGNORED`
represents explicit ignore rules, convenience exclusions, unsupported formats,
oversized or unreadable content. `FORBIDDEN` represents mandatory containment
or security exclusions and cannot be negated.

Root entrypoints remain file entries. Nested paths cluster by their real
top-level directory. Each cluster retains supported/recommended/ignored/
forbidden counts; a forbidden child makes the security state visible rather
than hiding it behind a recommended label. Candidate and cluster ordering is
classification priority (`RECOMMENDED`, `SUPPORTED`, `IGNORED`, `FORBIDDEN`)
then normalized relative path.

## Safety and policy

- scan scope is exactly one resolved project root;
- no ancestor, sibling, `$HOME`, registry, or external-v1-store enumeration;
- symlinks are never followed, including safe-looking internal aliases;
- `.git`, resolved `index.path`, and `.tessera_index` are mandatory exclusions;
- sockets/FIFOs/devices and other special entries are forbidden;
- private-key suffixes/names, credential files, `.env` variants, and `secrets/`
  are forbidden by conservative filename policy;
- example/template credential filenames remain unsupported, not secretly
  promoted;
- only `.md` is supported, preserving #69/#70 ownership;
- the 2 MiB size limit is checked from metadata before content parsing;
- `.tessera-ignore` is the only ordinary file read during discovery;
- config, sources, ignore bytes, mtimes, and index existence remain unchanged.

## `.tessera-ignore` contract

The optional UTF-8 root file supports comments, blanks, ordered `*`, `?`,
`**`, directory suffix `/`, and `!` re-inclusion. Empty negations, parent
traversal, and bracket classes are diagnosed. This is deliberately a familiar
subset, not full `.gitignore` compatibility. A negation can recover a safe
convenience-excluded file but never a mandatory exclusion.

## Configuration compatibility

Configured `sources` and discovered candidates are different states. Discovery
may recommend files outside the selected corpus but never appends them. Schema
v2 mappings remain byte/semantic stable. Schema-v1 migration still maps the
previous store to `store.path` and the sole source and does not activate project
discovery in Engine. `config doctor --json` exposes a plan only as read-only
diagnostic output.

## Evaluation record

Benchmark applicability: `SMOKE_ONLY`.

Benchmark rationale: source discovery changes candidate proposal and safety
only. Retrieval/ranking, selected corpus, Evidence Ledger, three drawers, and
mandatory-LLM behavior remain fixed. Deterministic sanity must remain Hit@1
`0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence `1.00`, and missing-evidence
passed. LongMemEval is not required unless held-constant retrieval changes.

Local candidate validation recorded for PR #175: the required focused set
passed `165` tests; the clean-worktree full suite passed `359` tests with 14
expected warnings; compileall and diff checks passed. Wheel and sdist builds
include `tessera/source_discovery.py`, exclude test/benchmark trees from the
wheel, and the installed-wheel discovery smoke passed. Sanity remained Hit@1
`0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence `1.00`, and missing-evidence
passed. Final candidate SHA, CI, Benchmark Ledger, and Issue
Evidence/Learnings/Decision links are recorded after final-head publication.
Until merge and a separate lifecycle reconciliation, #154 remains
`IN_PROGRESS`; #155/#118/#134 remain blocked and unstarted.

## Known limitations and non-goals

No content-based secret detector, complete `.gitignore` engine, non-Markdown
ingestion, semantic clustering, embeddings, model inference, picker, broad
renderer, config persistence, index build, or incremental indexing is added.
Unreadability is reported from deterministic filesystem metadata and safe scan
errors; platform ACL behavior remains platform-owned.
