# 93 — One configured store means one exact corpus everywhere

| Field | Value |
|---|---|
| Issue | [#93](https://github.com/LuigiFerronatto/TESSERA/issues/93) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | [#129](https://github.com/LuigiFerronatto/TESSERA/pull/129) |
| Head commit | [`ec4d624`](https://github.com/LuigiFerronatto/TESSERA/commit/ec4d624b8e19404cfb5470de85a2bc85fda2be59) audited runtime/test candidate; later evidence-only refresh does not change runtime |
| Merge commit | Not merged |
| Decision | `KEEP` candidate |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

Python, the CLI, MCP and quickstart now have an executable proof that one
configured TESSERA directory is the whole corpus, not merely the first folder
in a larger implicit project scan.

## What problem existed?

Issue #95 had already unified the configuration variable and precedence, but
there was no write-once/read-everywhere integration proof. The re-audit found
one smaller but real defect behind that missing proof: index construction could
silently add Markdown files from an ancestor, sibling `docs`, `experiments` or
`newsletters` directory. A configured path could therefore name one directory
while retrieval observed a larger corpus.

## How did TESSERA behave before?

On the audited main `5d43a2d4cdda0c17be6516f47920121070339d0f`:

```text
TESSERA_STORAGE_DIR=/tmp/audit/canonical-store
→ Python / CLI / MCP all report /tmp/audit/canonical-store
→ Engine also scans /tmp/*.md through its two-level ancestor heuristic
→ unrelated memories appear in all three result lists
```

The executable reproduction returned `issue-93/golden-parity` together with
unselected `../pr95_body` and `../issue95_evidence` memories.

## What changed or is being tested?

The existing #95 resolver is reused without alteration. A focused golden suite
tests the seven requested resolution scenarios, real CLI doctor execution,
actual MCP module startup, canonical quickstart output, warning channels,
provider-independent startup, corpus containment and lossless #68 retrieval
parity. The only runtime change removes implicit out-of-store discovery from
index bootstrap.

## How does it work now?

**CANDIDATE — NOT YET ON MAIN.** Resolution remains:

```text
explicit command/API path
→ TESSERA_STORAGE_DIR
→ deprecated LAO_MEM_DIR (one warning)
→ ./memories
```

After resolution, recursive indexing walks only that directory. Project/global
registry or adapter discovery remains future explicit work; it is not inferred
from the current working directory or a storage ancestor.

## Concrete example

```bash
export TESSERA_STORAGE_DIR="$PWD/project/memories"
tessera write --id issue-93/beacon --type factual --episode issue-93 \
  --content "One canonical corpus"
tessera query "canonical corpus" --json
```

The generated quickstart MCP block passes the same absolute directory under
`TESSERA_STORAGE_DIR`; Python, CLI and MCP return the same stable memory ID,
ordering and evidence object. A Markdown note beside `project/`, outside
`project/memories/`, is not indexed.

## How was it validated?

The focused suite contains 13 executable cases: seven cross-surface matrix
cases, four MCP bootstrap precedence cases, one containment regression and one
golden write-once/read-everywhere case. It uses real temporary stores and the
real CLI/MCP server code. An installed MCP transport is used directly; core-only
CI replaces only decorator registration while keeping storage resolution,
Engine construction and tools real. No provider or network is contacted.
Required regression suites, compile checks, the full suite, sanity before/after
and GitHub Actions are recorded in
[`docs/PR_EVOLUTION_93.md`](../PR_EVOLUTION_93.md) and the Issue evidence.

Deterministic sanity remains Hit@1 `0.75`, Hit@3 `1.00`, Hit@5 `1.00`, MRR
`0.875`, evidence hit rate `1.00`, missing-evidence check `passed`.

## What improved?

- The selected storage directory is now the complete source boundary.
- Generated quickstart configuration boots MCP against the same absolute path.
- Python, CLI and MCP preserve one result list, memory ID, order and evidence.
- Legacy-only use remains functional with one stderr warning and valid JSON.
- MCP deterministic import/startup remains independent of optional credentials.

## What remains unimplemented?

This card does not implement repository restructuring (#115), a project/global
registry or interactive initialization (#117), optional adapter/MCP lifecycle
architecture (#120), retrieval/ranking changes, graph expansion, temporal or
conflict behavior, Evidence Ledger semantics, write admission, persistence
schema, or benchmark changes. Those issues remain separate.

## What is unlocked next?

Nothing is promoted while this pull request is open. #67 remains `BLOCKED` on
the merge and lifecycle synchronization of #93 and on its own regression-gate
integration. #115, #117 and #120 are not started or absorbed.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#93](https://github.com/LuigiFerronatto/TESSERA/issues/93) |
| Pull request | [#129](https://github.com/LuigiFerronatto/TESSERA/pull/129) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | [Superseding KEEP evidence](https://github.com/LuigiFerronatto/TESSERA/issues/93#issuecomment-5483152212) |
| Benchmark record | `SMOKE_ONLY`; deterministic sanity only; LongMemEval not rerun |
| PR Evolution Audit | [`docs/PR_EVOLUTION_93.md`](../PR_EVOLUTION_93.md) |

## Evolution

```text
#83 canonical MCP name
→ #98 lossless retrieval parity
→ #108 contained writes
→ #126 shared resolver and generic quickstart
→ #127 #95 lifecycle synchronization
→ #93 exact-corpus containment + golden integration candidate
→ after merge/lifecycle sync, #67 loses only its #93 dependency
```
