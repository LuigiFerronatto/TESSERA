# 69 — Plain-text files are first-class knowledge sources

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
| Benchmark rationale | The default candidate-source set expanded, so the frozen retrieval gate verified that the added format did not regress retrieval or provenance. |
| Last audited | 2026-09-15 |

## In one sentence

TESSERA now discovers, indexes, retrieves, and incrementally maintains ordinary
`.txt` files as body-only sources with explicit provenance.

## What problem existed?

The product described itself as text-first, but project discovery and indexing
only admitted Markdown. A `.txt` file could not participate in the normal
source lifecycle, and the lower-level canonical path could incorrectly treat
Markdown-like delimiters in plain text as YAML frontmatter.

## How did TESSERA behave before?

```text
notes.md  -> discovered -> parsed as Markdown -> indexed
notes.txt -> unsupported / ignored
```

## What changed or is being tested?

A small deterministic source-format adapter now defines supported suffixes and
their parsing rules. Markdown retains YAML frontmatter semantics; plain text is
always the complete body. Discovery, initialization, configuration defaults,
indexing, evidence freshness, and incremental add/edit/move/delete handling all
use that shared boundary.

## How does it work now?

**VALIDATED ON `main`.** `.md` and `.txt` are supported source formats. A
plain-text source records `source.format: text`, remains byte-for-byte
unchanged, and receives stable document/evidence identity. Same-stem Markdown
and text files remain distinct documents. Successful writes remain
Markdown-only.

## Concrete example

```text
docs/notes.txt
  -> format=text
  -> deterministic document identity
  -> searchable content and evidence spans
  -> incremental edit/move/delete lifecycle
```

A `.txt` file beginning with `---` is still plain text; TESSERA does not parse
or invent frontmatter for it.

## How was it validated?

- acceptance tests cover body-only parsing, byte preservation, distinct
  same-stem `.md`/`.txt` identities, retrieval/evidence provenance, freshness,
  and add/edit/move/delete lifecycle;
- the clean full suite reported 551 passed and 5 skipped on the final candidate;
- wheel and sdist were installed and exercised outside the checkout, including
  `.txt` indexing and retrieval;
- CI on `ddc1ff3a` passed tests and distribution on Python 3.9/3.12, smoke,
  sanity evaluation, offline benchmark reporting, and required LongMemEval V1
  dev-50;
- the Maintainer Audit found no P0/P1 findings and recorded `KEEP` for that
  exact head.

## What improved?

- plain text participates in the same audited source lifecycle as Markdown;
- format parsing is explicit and shared instead of inferred inconsistently;
- evidence freshness hashes `.txt` using body-only semantics;
- the three semantic drawers remain unchanged.

## What remains unimplemented?

- general JSON, binary formats, encoding detection, and user-defined adapters;
- structure-aware segmentation of long documents (#70);
- adapter precedence and instruction resolution (#71/#72).

## What is unlocked next?

[#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) had its final hard
blocker satisfied and moves to `READY`. [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13)
and [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) still depend on
#70 and remain blocked.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) |
| Pull request | [#264](https://github.com/LuigiFerronatto/TESSERA/pull/264) |
| Merge commit | [`c815a684e4c8cbd426a0d717e243a7dfb0f04395`](https://github.com/LuigiFerronatto/TESSERA/commit/c815a684e4c8cbd426a0d717e243a7dfb0f04395) |
| Evidence/Learnings/Decision | Maintainer Audit `KEEP` on final candidate `ddc1ff3a`; PR #264 evaluation card |
| Benchmark record | `REQUIRED`; LongMemEval V1 dev-50 passed on `ddc1ff3a` |
| PR Evolution Audit | Recorded in the [PR #264 body](https://github.com/LuigiFerronatto/TESSERA/pull/264) |

## Evolution

```text
Markdown-only source discovery and indexing
-> #69 shared Markdown/plain-text format adapter
-> current state: .md + body-only .txt on main
-> next validated dependency: #70 structural segmentation
```
