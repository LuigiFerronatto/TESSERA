# PR Evolution Audit — Issue #153 configuration v2 boundaries

Audited starting `main`: `0880ef3ec417735c105898039cc202450407af2b`,
the fetched `origin/main` when branch `test-card/153-config-v2` was created.
No open pull request overlapped Issue #153. Issue #153 was `READY`; #117 and
#93 were already `VALIDATED` through their canonical implementation and
lifecycle deliveries.

## Before architecture

```text
explicit / env / project / named-global selection
                     |
              StorageSelection
                     |
              storage_dir
              /     |     \
          writes  sources  .tessera_index
```

#93 intentionally made `storage_dir` the complete implicit corpus, preventing
ancestor and sibling leakage. #117 added safe selection and stable store
identity without changing that Engine boundary. Those protections are retained;
#153 adds explicit source breadth only when schema v2 says so.

## Final architecture contract

```text
configuration inputs
        |
ResolvedConfiguration (one runtime source of truth)
        |-------------------|------------------|
   store.path          sources.roots       index.path
   write only          read/index only     derived only
```

`storage_dir` remains a public compatibility spelling for `store.path`.
Direct `TesseraEngine(storage_dir=...)`, canonical/deprecated environment
selection, and the no-config MCP fallback retain a conservative single-root
corpus and `<store>/.tessera_index`. Configuration-aware CLI and MCP paths pass
the resolved object to Engine.

## Schema and migration

Project schema v2 contains closed `store`, `sources.roots[].{path,include}` and
`index.path` sections. New init remains conservative: the only initial source
is the selected store, while the project index is `.tessera/index`.

Loading schema v1 maps:

```text
old store.path -> write store
old store.path -> sole source root (**/*.md)
project/.tessera/index -> derived index
```

Serializing that loaded configuration writes schema v2 without adding README,
docs, research, ancestors, siblings, or `$HOME`. A v1 external absolute store
is permitted only as its own compatibility source. Named-global selection
likewise reads only its registered store and never absorbs the current project.

## Identity, evidence, and cache behavior

The explicit index directory owns `graph.pkl`, `graph.json`,
`identity_manifest.json`, and `evidence.json`. The cache key includes source
roots, include patterns, identity root, and index location, so a changed
boundary cannot reuse an unrelated graph. Source documents are read without
copy or rewrite. Generated-memory path validation continues to use only the
write store.

V1, direct legacy, and store-contained v2 memories keep store-relative
identities, preserving inferred IDs and Evidence Ledger source paths across a
conservative migration. Other explicit v2 sources use the physical project as
their identity base, producing stable, non-escaping paths such as `README.md`
and `docs/guide.md`. A generated store note remains `project/fact.md`, not a
new `memories/project/fact.md` identity.

## Safety and scope

- source root and include traversal are rejected;
- project source roots resolve under the physical project;
- symlink file/root escapes fail safely;
- the derived index is excluded even when a broad configured include matches it;
- writes remain descendants of `store.path` only;
- source readability does not imply writability;
- no home, ancestor, sibling, or registry-wide scan exists;
- #154, #155, #157, `.tessera-ignore`, source picking, segmentation, and
  incremental indexing are not implemented.

## Evaluation record

Benchmark applicability: `SMOKE_ONLY`, evaluated under Test Card #153.

Benchmark rationale: the configuration contract can explicitly select a wider
corpus, but ranking, graph expansion, conflict resolution, evidence projection,
and benchmark implementation are unchanged. For a held-constant corpus, direct
legacy and migrated-v1 retrieval results must be byte-equivalent after JSON
projection. LongMemEval is not required unless final evidence shows an
unexpected semantic change.

Local candidate evidence:

| Gate | Result |
|---|---|
| Focused #153 + #117 + #93 + retrieval + Evidence Ledger + path/write contracts | `209 passed` |
| Full suite, Python 3.9 | `317 passed`, 14 established write-ID warnings |
| Full suite, Python 3.12 | `317 passed`, 14 established write-ID warnings |
| Compile and whitespace | `compileall` green; `git diff --check` green |
| Held-constant legacy/v1 corpus | Exact structured retrieval equality, including conservative init migration |
| Deterministic sanity before | Hit@1 `0.75`; Hit@3 `1.00`; Hit@5 `1.00`; MRR `0.875`; evidence `1.00`; missing evidence passed |
| Deterministic sanity candidate | Hit@1 `0.75`; Hit@3 `1.00`; Hit@5 `1.00`; MRR `0.875`; evidence `1.00`; missing evidence passed |

## Canonical delivery and lifecycle result

| Field | Canonical evidence |
|---|---|
| Implementation starting main | `0880ef3ec417735c105898039cc202450407af2b` |
| Runtime implementation commit | [`53f772cdd0fae369a2ed3954751667d5e4ea52c4`](https://github.com/LuigiFerronatto/TESSERA/commit/53f772cdd0fae369a2ed3954751667d5e4ea52c4) |
| Final candidate | [`72b2b0c44ecbdc6e5f45ed612f4eb9bb69c57cd4`](https://github.com/LuigiFerronatto/TESSERA/commit/72b2b0c44ecbdc6e5f45ed612f4eb9bb69c57cd4) |
| Implementation PR | [#173](https://github.com/LuigiFerronatto/TESSERA/pull/173) |
| Canonical squash merge | [`2508676d472088733702b6ed920fc829df9a7681`](https://github.com/LuigiFerronatto/TESSERA/commit/2508676d472088733702b6ed920fc829df9a7681) |
| Lifecycle status | `VALIDATED` |
| Decision | `KEEP` |
| Implementation benchmark applicability | `SMOKE_ONLY` |

The final candidate and canonical squash merge are two Git identities for one
delivery, not two features. The runtime commit is preserved separately because
the final candidate also contains its evidence and documentation corrections.

Exact PR #173 surfaces changed:

```text
CHANGELOG.md
README.md
docs/ARCHITECTURE.md
docs/OVERVIEW.md
docs/PR_EVOLUTION_153.md
docs/ROADMAP.md
docs/test-cards/153-configuration-v2-store-sources-index.md
docs/test-cards/README.md
tessera/cli.py
tessera/config.py
tessera/engine.py
tessera/engine_core.py
tessera/mcp_server.py
tests/test_architecture_boundary_docs.py
tests/test_issue_117_config_init_discovery.py
tests/test_issue_153_configuration_v2.py
tests/test_issue_95_runtime_boundary.py
tests/test_project_agnostic_runtime.py
```

Final-head CI was green at `72b2b0c44ecbdc6e5f45ed612f4eb9bb69c57cd4`:
[TESSERA CI 33545813964](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33545813964)
passed Python 3.9, Python 3.12, distribution, smoke, and sanity; [Benchmark
Ledger 33545813991](https://github.com/LuigiFerronatto/TESSERA/actions/runs/33545813991)
passed offline reporting and skipped LongMemEval under `SMOKE_ONLY`.

## Validated outcome and downstream routing

```text
store.path -> generated-memory write destination
sources    -> explicit read/index corpus
index.path -> derived, disposable, rebuildable state
```

Engine, CLI, and MCP consume the same resolved boundary. The path, symlink,
source-read-only, store-write-containment, identity, cache, and rebuild evidence
listed above remained green through the final candidate. Held-constant direct,
schema-v1, and conservatively migrated schema-v2 retrieval projections remained
exact, with sanity unchanged at Hit@1 `0.75`, Hit@3/5 `1.00`, MRR `0.875`,
evidence `1.00`, and missing-evidence passed.

Conservative migration remains:

```text
schema v1
-> previous store remains store.path
-> previous store remains the only source
-> no repository-wide discovery is activated
```

Known limitations and non-goals remain automatic source discovery,
`.tessera-ignore`, source clustering/picker UX, init UX, embeddings/models, and
incremental indexing. They were not implemented by #153.

Post-merge routing is therefore: #154 `READY` with no remaining hard blocker;
#155 `BLOCKED` on #154; #118 `BLOCKED` on #154/#155; and #157's #153 prerequisite
is satisfied, but #157 is deliberately `DEFERRED` under portfolio WIP. No
downstream implementation was started.
