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

## Candidate architecture

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

The implementation candidate was published as
[`53f772c`](https://github.com/LuigiFerronatto/TESSERA/commit/53f772cdd0fae369a2ed3954751667d5e4ea52c4)
in [PR #173](https://github.com/LuigiFerronatto/TESSERA/pull/173). CI run links
and the final PR head are recorded in PR evidence. Until canonical merge and
post-merge lifecycle sync, #153 remains `IN_PROGRESS`, and #154/#155 remain
blocked.
