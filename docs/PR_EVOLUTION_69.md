# PR Evolution Audit — Issue #69 plain-text source ingestion

## Canonical lifecycle

- **Decision:** `KEEP`
- **Implementation PR:** [#264](https://github.com/LuigiFerronatto/TESSERA/pull/264)
- **Final candidate head:** `ddc1ff3a4394c89c7732357fc66168d6d599a2ac`
- **Canonical merge commit:** `c815a684e4c8cbd426a0d717e243a7dfb0f04395`
- **Lifecycle status:** `VALIDATED`
- **Implementation benchmark applicability:** `REQUIRED` (default candidate-source set expands)
- **Lifecycle correction benchmark applicability:** `NOT_APPLICABLE` (documentation/governance-only)
- **Final CI:** all jobs green at the merge commit — `test`/`distribution` (Python 3.9/3.12), `smoke`, `sanity-eval`, `benchmark-reporting` (offline)
- **Final Benchmark Ledger:** `longmemeval-v1-dev-50` ran green at the audited head, consistent with the `REQUIRED` rationale
- **Maintainer audit:** `KEEP` recorded on head `ddc1ff3a4394c89c7732357fc66168d6d599a2ac` (PR #264 review thread)

The final candidate head and canonical merge commit represent one plain-text
ingestion delivery, not two capabilities. This post-merge lifecycle sync is a
documentation/governance correction only; no runtime code is changed here.

## Capability lineage

| Issue | Canonical contribution retained by #69 |
|---|---|
| #3 | Canonical Metadata, stable document identity. |
| #6 | Evidence Ledger, source/version-aware provenance. |
| #101 | Markdown-only write-gate contract, unchanged by this PR. |
| #175 | Markdown-only discovery, now extended to admit `.txt`. |
| #210 | Source-aware `tessera init`, now offering `.txt` candidates. |
| #246 | Incremental add/edit/move/delete manifest lifecycle, reused for `.txt`. |
| #69 | Explicit Markdown/plain-text format adapters; `.txt` as a body-only source across discovery, init, indexing, evidence and retrieval provenance. |

## Before architecture

```text
source discovery / implicit config / Engine iteration -> `.md` only
canonical normalization -> labeled non-Markdown paths "text" but still
  parsed their contents through the Markdown frontmatter parser
```

## Validated architecture

```text
tessera/source_formats.py
  -> is_supported_source_path() / source_format_for_path()
  -> split_source(path, raw_text) -> (frontmatter, body)
       - format "markdown" -> parses YAML frontmatter
       - format "text"     -> always ({}, raw_text), no frontmatter parsing

canonical.py / engine_core.py / evidence.py / config.py / init_flow.py
  -> admit `.md` and `.txt` consistently across discovery, cache
     fingerprints, init plans, incremental lifecycle and evidence freshness
```

`.txt` is always treated as a body-only document, even if its content starts
with a `---` line that would look like YAML frontmatter in Markdown. Source
bytes are never rewritten.

## Safety and contract preservation

- the Markdown-only **write** contract (#94/#101) is unchanged — this PR only
  extends **read/index** admission;
- same-stem `.md`/`.txt` sources are assigned distinct, deterministic
  `document_id`s rather than colliding;
- explicit-ID collisions across formats still raise instead of silently
  overwriting a graphed node;
- evidence freshness hashing is format-aware, so `.txt` correctly treats the
  entire file as body when comparing `content_changed` vs `document_changed`;
- no new semantic drawer was introduced; `facts`/`preferences`/`insights`
  remain the only three.

## Evaluation record

Implementation benchmark applicability: `REQUIRED`.

- focused suite (`test_issue_69_text_ingestion.py` plus adjacent parity/init/
  discovery/indexing/evidence suites): `119 passed`;
- full clean-worktree suite: `551 passed, 5 skipped`;
- sdist/wheel rebuild and clean-room installed-artifact smoke: passed,
  including `.txt` provenance, relocation and security cases;
- CI at the canonical merge commit: `test`/`distribution` (3.9/3.12),
  `smoke`, `sanity-eval`, `benchmark-reporting` (offline) — all green;
- Benchmark Ledger: `longmemeval-v1-dev-50` ran green at the audited head, as
  required by the expanded default candidate-source set.

This lifecycle correction changes no runtime behavior, so it is
`NOT_APPLICABLE` for benchmark purposes.

## Post-merge routing

```text
#12 VALIDATED
  -> #69 VALIDATED
      -> #70 READY (structural segmentation; #12 and #69 both satisfied)
          -> #13 BLOCKED on #70
      -> #71 BLOCKED (depends on #69 AND #70; only #69 satisfied)
          -> #72 BLOCKED on #71
```

#69 no longer consumes executable WIP. #70 is the next Sources-lane
candidate under M2, but is not started by this lifecycle correction.

## Known limitations and non-goals (unchanged by this correction)

General JSON ingestion, binary formats, encoding detection, structure-aware
long-document segmentation (#70), and adapter precedence (#71/#72) remain
out of scope. A maintainer follow-up issue may be warranted to track the
competitive-audit acceptance requirements captured in the
[#69 comment thread](https://github.com/LuigiFerronatto/TESSERA/issues/69#issuecomment-5673804520)
(parser registry, capability-extra parser boundary, `.env`/keys always
forbidden, parser identity in cache keys) — this is flagged for a maintainer
to file as a new Test Card and is not implemented here.
