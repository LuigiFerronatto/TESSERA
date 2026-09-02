# PR Evolution Audit — Issue #154 safe source discovery

Audited starting `main`: `8f1c0c19a04ec4bde686b124389eb17a61856de0`,
the fetched canonical main when branch `test-card/154-safe-source-discovery`
was created. No open pull request overlapped #154. Live routing was #154
`READY`, #155 `BLOCKED` on #154, #118 `BLOCKED` on #154/#155, and #134
`BLOCKED` on #118 plus #87.

## Canonical lifecycle

- **Decision:** `KEEP`
- **Implementation PR:** [#175](https://github.com/LuigiFerronatto/TESSERA/pull/175)
- **Final candidate:** `06521763b4c3cf033c4d1e6a771ae105aad98e37`
- **Canonical squash merge:** `05ce0dd234a7756d4a5ba315b77e4a6ec33c9429`
- **Lifecycle status:** `VALIDATED`
- **Implementation benchmark applicability:** `SMOKE_ONLY`
- **Lifecycle correction benchmark applicability:** `NOT_APPLICABLE`
- **Final CI:** TESSERA CI `33633838687` — success
- **Final Benchmark Ledger:** `33633838753` — success

The final candidate and canonical squash merge are one source-discovery
delivery, not two capabilities. The post-merge lifecycle sync is a
documentation/governance correction only.

## Capability lineage

| Issue | Canonical contribution retained by #154 |
|---|---|
| #92 | Write admission/path containment remains independent from readable candidates. |
| #93 | One selected legacy store remains the complete implicit corpus across surfaces. |
| #95 | Generic runtime remains project-agnostic; legacy compatibility is explicit. |
| #117 | Physical project root and deterministic project/global configuration selection. |
| #153 | `store.path` writes, explicit `sources` read/index, and `index.path` derived state; canonical squash merge `2508676d472088733702b6ed920fc829df9a7681`. |
| #154 | Safely discover/classify additional project candidates without selecting them. |
| #155 | Display/select/confirm/persist/index workflow; now unblocked by validated #154 but still a separate delivery. |

#153, #154 and #155 remain separate deliveries:

```text
#153 = WHAT paths can be configured as store / sources / index
#154 = HOW project source candidates are safely discovered / classified
#155 = HOW a user selects and confirms those candidates
```

## Before architecture

```text
ResolvedConfiguration
  -> store.path
  -> explicit sources
  -> index.path

safe project-wide candidate proposal -> absent
```

## Validated architecture

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
forbidden counts. Classification and selectability are derived from safe
selectable children: a mixed cluster remains recommended or supported while
its forbidden count exposes excluded children, and a forbidden-only cluster
remains forbidden. Candidate and cluster ordering is classification priority
(`RECOMMENDED`, `SUPPORTED`, `IGNORED`, `FORBIDDEN`) then normalized relative
path.

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
convenience-excluded file, including through `**` below an ignored parent, but
never a mandatory exclusion.

## Configuration compatibility

Configured `sources` and discovered candidates are different states. Discovery
may recommend files outside the selected corpus but never appends them. Schema
v2 mappings remain byte/semantic stable. Schema-v1 migration still maps the
previous store to `store.path` and the sole source and does not activate project
discovery in Engine. `config doctor --json` exposes a plan only as read-only
diagnostic output.

## Evaluation record

Implementation benchmark applicability: `SMOKE_ONLY`.

Final candidate validation for PR #175:

- focused blocker/impacted set: `66 passed`;
- full clean suite: `363 passed`, 14 expected warnings;
- compileall and `git diff --check`: passed;
- wheel + sdist: built successfully;
- installed-wheel discovery smoke: passed;
- deterministic sanity unchanged: Hit@1 `0.75`, Hit@3/5 `1.00`, MRR `0.875`, evidence `1.00`, missing-evidence passed;
- TESSERA CI run `33633838687`: success;
- Benchmark Ledger run `33633838753`: success; LongMemEval correctly skipped under `SMOKE_ONLY`.

The held-constant retrieval contract was not changed by discovery. Source
selection remains explicit and separate from candidate proposal. This post-merge
lifecycle correction is `NOT_APPLICABLE` for LongMemEval because it only changes
documentation, roadmap routing and static governance assertions.

## Post-merge routing

```text
#153 VALIDATED
  -> #154 VALIDATED
      -> #155 READY
          -> #118 BLOCKED on #155
              -> #134 BLOCKED on #118 + #87
```

#154 no longer consumes executable WIP. #155 is the next release-critical
productization implementation candidate, but is not started by this lifecycle
correction.

## Known limitations and non-goals

No content-based secret detector, complete `.gitignore` engine, non-Markdown
ingestion, semantic clustering, embeddings, model inference, picker, broad
renderer, config persistence, index build, or incremental indexing is added.
Unreadability is reported from deterministic filesystem metadata and safe scan
errors; platform ACL behavior remains platform-owned.
