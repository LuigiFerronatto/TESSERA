# 69 — Plain-text `.txt` sources as body-only documents

| Field | Value |
|---|---|
| Issue | [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) |
| Record status | `VALIDATED` |
| Capability type | `runtime` |
| Pull request | [#264](https://github.com/LuigiFerronatto/TESSERA/pull/264) |
| Head commit | Final candidate [`ddc1ff3a`](https://github.com/LuigiFerronatto/TESSERA/commit/ddc1ff3a4394c89c7732357fc66168d6d599a2ac) |
| Merge commit | Canonical merge [`c815a684`](https://github.com/LuigiFerronatto/TESSERA/commit/c815a684e4c8cbd426a0d717e243a7dfb0f04395) |
| Decision | `KEEP` |
| Benchmark applicability | `REQUIRED` |
| Benchmark rationale | The default candidate-source set expands to include `.txt`, so the frozen retrieval gate verifies no candidate or provenance regression. |
| Last audited | 2026-09-15 |

## In one sentence

`.txt` files are now a first-class, body-only source format: discoverable,
indexable, retrievable, incrementally maintained, and explicit in
`source.format: text`, without any source-byte mutation or new semantic
drawer.

## What problem existed?

TESSERA's scanner, implicit store configuration, and Engine iteration
admitted only `.md`. Direct canonical normalization labeled other suffixes
as `text` but still parsed their contents through the Markdown frontmatter
parser, so a `.txt` file starting with `---` could have spurious metadata
extracted from it.

## How did TESSERA behave before?

```text
notes.txt -> IGNORED / unsupported_format
```

or, where a caller bypassed discovery and pointed the Engine at it directly:

```text
notes.txt -> parsed as Markdown -> possible spurious frontmatter
```

## What changed or is being tested?

A dedicated `tessera/source_formats.py` module centralizes suffix admission
and format-aware splitting: Markdown gets frontmatter parsing, plain text
always returns `({}, raw_text)`. Source discovery, implicit store
configuration, `tessera init`, Engine iteration/fingerprints, incremental
lifecycle manifests, and evidence freshness hashing all became format-aware
consumers of this module.

## How does it work now?

**VALIDATED on `main`.**

```text
notes.txt -> SUPPORTED / format=text -> canonical index -> retrieval provenance
```

Same-stem `.md`/`.txt` sources are assigned distinct, deterministic
`document_id`s. Add/edit/move/delete lifecycle (from #12) works identically
for `.txt`. Evidence freshness correctly treats the whole `.txt` file as body
when comparing `content_changed` vs `document_changed`.

## Concrete example

```text
source:
  path: notes.txt
  format: text
  document_id: doc_...
evidence:
  span:
    start_line: 1
    end_line: 1
```

## How was it validated?

- focused suite (`test_issue_69_text_ingestion.py` + adjacent parity/init/
  discovery/indexing/evidence suites): `119 passed`;
- full clean-worktree suite: `551 passed, 5 skipped`;
- sdist/wheel rebuild and installed-artifact clean-room smoke: passed,
  including `.txt` provenance, relocation and security cases;
- CI at the canonical merge commit (`test`/`distribution` Python 3.9/3.12,
  `smoke`, `sanity-eval`, `benchmark-reporting` offline): green;
- Benchmark Ledger: `longmemeval-v1-dev-50` ran green at the audited head,
  consistent with the `REQUIRED` applicability;
- maintainer audit recorded `KEEP` on the final candidate head.

## What improved?

- `.txt` participates in discovery, init, indexing, retrieval and evidence
  like a first-class source;
- no fake frontmatter is ever extracted from `.txt`, even when its content
  looks like YAML frontmatter;
- same-stem `.md`/`.txt` documents remain distinct, retrievable identities.

## What remains unimplemented?

- general JSON/binary ingestion;
- structure-aware long-document segmentation (#70);
- adapter precedence across formats (#71/#72);
- the broader parser-registry/capability-extras acceptance requirements
  raised in the [#69 comment thread](https://github.com/LuigiFerronatto/TESSERA/issues/69#issuecomment-5673804520)
  (not yet filed as a separate Test Card).

## What is unlocked next?

- [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) (structural
  segmentation) had its only remaining hard blocker (#69) satisfied and
  moves to `READY`.
- [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) remains
  `BLOCKED` — it still depends on #70.
- [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) remains
  `BLOCKED` — it depends on both #69 and #70; only #69 is satisfied.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) |
| Pull request | [#264](https://github.com/LuigiFerronatto/TESSERA/pull/264) |
| Merge commit | [`c815a684e4c8cbd426a0d717e243a7dfb0f04395`](https://github.com/LuigiFerronatto/TESSERA/commit/c815a684e4c8cbd426a0d717e243a7dfb0f04395) |
| Evidence/Learnings/Decision | Maintainer audit `KEEP` on final candidate head `ddc1ff3a` (PR #264 review thread) |
| Benchmark record | `REQUIRED`; `longmemeval-v1-dev-50` ran green |
| PR Evolution Audit | [`PR_EVOLUTION_69.md`](../PR_EVOLUTION_69.md) |

## Evolution

```text
`.md`-only scanner; suffix-labeled but Markdown-parsed non-Markdown content
-> #69 explicit Markdown/plain-text adapters, `.txt` body-only across the stack
-> current state: `.txt` VALIDATED on main
-> next validated dependency: #70 (structural segmentation)
```
