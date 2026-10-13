# Legacy enrichment: offline experiment protocol (#176)

Status: experimental, review-only, not a product default. Decision: **ITERATE**.
The semantic KEEP gate is still open. This slice prepares useful, independently
testable mechanics without pretending that synthetic captures establish AI quality.

## What is available

`python -m tessera.enrichment plan` accepts an explicit, bounded list of files,
reuses canonical #154 discovery/exclusions, reads only eligible selections, and
returns a JSON disclosure. `replay` checks already captured JSON against a fresh
plan. Neither command has model transport, write/admission, index mutation or
model-download code. Ordinary `tessera index`, retrieval, CLI and MCP defaults
are unchanged; A0 remains independently usable offline.

Selection is individual root-relative `.md`/`.txt` files. It does not accept a
whole directory, expand globs, inventory siblings, or traverse symlinks. The
optional `discover_sources(..., selected_paths=[...])` API uses the existing
policy walk on only those path components; default discovery behavior is
unchanged. Project configuration still identifies a custom derived-index path.
Unsafe, missing, ignored, oversized or malformed sources fail closed. Ignore
file diagnostics require review. Instruction documents and empty sources may
appear in a preview but receive no model work or memory proposals.

Source reads pin all directory/file descriptors with `O_NOFOLLOW`, reject
special files, enforce bounded reads, and compare read-time file metadata.
Platforms lacking descriptor-relative no-follow support fail closed. This
experimental entrypoint is currently POSIX-only; the existing core remains
cross-platform. Bytes are decoded as strict UTF-8 without newline normalization.
CRLF, foreign frontmatter, original metadata and raw source retrieval remain
unchanged. Path exclusions are **not a content-sensitivity classifier**: an
allowed Markdown path can still contain personal or confidential information.

## Prepare a preview

Create an explicit request outside the sources, for example:

```json
{
  "corpus_id": "reviewed-legacy-pilot-v1",
  "selected_paths": ["docs/legacy.md"],
  "profile": {
    "name": "candidate-profile",
    "version": "1",
    "mode": "A2",
    "provider_mode": "local",
    "provider": "chosen-local-runtime",
    "model": "chosen-model-version",
    "prompt_version": "pilot-v1"
  },
  "limits": {
    "max_sources": 4,
    "max_bytes_per_source": 65536,
    "max_total_bytes": 262144,
    "max_model_calls": 4,
    "budget_usd": null
  }
}
```

```bash
python -m tessera.enrichment plan --root /explicit/project --request request.json
python -m tessera.enrichment replay --root /explicit/project --request request.json --capture capture.json
```

Both print JSON to stdout; invalid input prints a JSON error to stderr and exits
2. They do not create an artifact, store, source or index. Save stdout only to an
explicit experiment-artifact location, never over an input source. JSON request
and capture readers reject symlinks, non-regular/FIFO inputs, excessive nesting/numeric ranges,
duplicate object keys, nonfinite values and artifacts
larger than 2 MiB. JSON is data; source instructions and candidate text are never
executed. Outputs contain source paths/metadata and replayed quotes, so keep them
private unless authorized to share them.

The preview exposes:

- Corpus ID, canonical source document IDs, paths, exact byte SHA-256 and sizes
- Canonical classification/origins/tags/entities plus #70 structural span IDs
- Profile/mode/provider/model/prompt fingerprints and a complete `plan_id`
- Separate selected, eligible and structural-segment counts
- One hypothetical whole-source call per eligible source, maximum input/output
  allowances and token-cost estimate when both prices are supplied
- Explicit local/remote destination and required consent/budget review
- Zero modified sources and zero admitted memories

The input allowance uses UTF-8 byte length plus declared prompt overhead; it is
not a provider tokenizer result. Pricing, when supplied, covers these token
allowances only, not route fees, taxes, retries or provider minimum charges.
Missing pricing/budget is reported as unknown/unapproved, never zero. An offline
plan can be prepared in this state; execution is unsupported regardless. Future
execution must verify its actual tokenizer, prompt and full route pricing.

A plan **never grants consent**, even when the mode says `remote` or a model is
already configured. Remote execution requires an explicit approval naming the
exact selected source-content hashes, actual provider/model destination and
complete run budget. A local route likewise requires intentional selection and
source review. This module does not obtain/store such approval, download a local
model or execute either route. A future transport must enforce that boundary.

## Capture schema and strict replay

The input envelope requires exactly these fields:

```text
schema_version: 1
plan_id: exact preview ID
profile_fingerprint: exact preview fingerprint
capture_kind: synthetic | provider_response
records:
  - cache_key: exact selected eligible source key
    status: success | error | refused | truncated
    usage:
      input_tokens: nonnegative bounded integer
      output_tokens: nonnegative bounded integer
      latency_ms: nonnegative finite number | null
      cost_usd: nonnegative finite number | null
    response:
      metadata: [...]
      claims: [...]
      relations: [...]
```

Each successful record requires all three response arrays. Failed/refused/
truncated records must use `response: null`; partial candidates cannot leak out.
Missing records are reported as incomplete; duplicate/unselected/skipped-source
records fail. Retry capture can cover only missing/failed sources; replay does
not merge runs or supply a checkpoint/cache engine. #192 owns that lifecycle.
Actual provider origin and usage are caller-reported capture metadata, not
cryptographic proof that a provider ran. `model_calls_performed` is always zero.
Unknown cost/latency remains null, including failures. Known reported costs that
already exceed budget fail even if another record's cost is unknown.

Every proposed annotation requires `confidence` in [0, 1], an `uncertainty` array
and 1–16 `supporting_spans`. Each span contains `start_line`, `end_line`, `quote`:
1-based inclusive full-source lines whose quote must match exactly, including
line endings. Unknown fields are rejected. Proposal kinds:

- `claims`: `claim` text and exactly one existing `drawer` (`facts`,
  `preferences`, `insights`); permitted in A2/A3 only
- `metadata`: `field`, `value`; fields are document_type, tags, entities,
  state_key, valid_from, valid_until; permitted in A1/A2/A3
- `relations`: `type`, `target_source_document_id`; permitted only in A3,
  only to an eligible selected source, and only supports, contradicts,
  supersedes_candidate, derived_from, related_to, caused_by

Relation types remain suggestions; `supersedes` is rejected. No co-occurrence
relation is synthesized. Metadata proposals do not overwrite explicit or
foreign author values; differences produce review diagnostics. Only capture
origin is `ai_inferred`/`ai_proposed`; synthetic fixtures are labeled `synthetic`.
No annotation can claim `human_confirmed` or `validated` on input.

Valid candidates retain corpus ID, source document/path/hash, exact supporting
spans, profile fingerprint, deterministic candidate ID and `review_required`.
This is an **experiment-side envelope**, not a replacement for canonical episode
lineage (#137). The ID suppresses only identical validated claims with the same
versioned source spans, drawer, confidence, uncertainty, origin and profile.
Case, whitespace or annotation differences remain separate review candidates. It does not establish semantic equivalence
across differently worded claims, independent source files or corpus IDs.
Cross-source duplicates and evidence independence remain review work. Source IDs
come from standalone canonical parsing in the explicit corpus namespace. This
offline protocol does not load an index's persisted move history; a moved source
requires a new preview/identity reconciliation rather than inferred cache reuse.

Exact quotes prove location, **not entailment**. A fabricated claim paired with
a real quote can pass structural validation and must remain review-only. The
suite explicitly tests this case. Unsupported-claim/hallucination rates,
atomicity, precision and recall remain null until independent human labels
exist. Invalid proposals are counted separately from durable-memory rejection;
`memories_admitted`, `memories_deduplicated`, `memories_rejected` and validated
relations remain zero. Existing explicit/deterministic relation counts are null
because capture replay does not independently reclassify existing core origins.

## Frozen offline evidence

```bash
python -m pytest -q tests/test_issue_176_enrichment.py tests/test_issue_154_source_discovery.py
python -m benchmarks.enrichment_176.run_experiment
python -m pytest -ra
```

`benchmarks/enrichment_176/synthetic-v1.json` is checksum-frozen, agent-authored
synthetic data, **not reviewed gold**. The runner materializes it only in a fresh
temporary directory, exercises A1/A2/A3 captures and verifies repeatability,
source-byte preservation and absence of new source/index files. It never sends
sources anywhere. The versioned `synthetic-result-v1.json` records:

- 8 source documents, 2 canonical structural segments, 7 eligible captures
- A1: 6 metadata proposals, no memory candidates
- A2/A3: 11 claim proposals, 1 exact duplicate, 1 invalid span, 9 review candidates
- A3: 1 synthetic relation proposal, 0 validated relations
- 0 source modifications, provider calls, model downloads or admitted memories

E0 raw source and E1 structural counts are provenance mechanics, not retrieval
scores. E2 is deliberately aggressive synthetic capture; E3 admission and E4
validated-relation consumption remain blocked. Real E0–E4 Recall/MRR/nDCG,
context/state quality, hallucination, tag/entity/relation precision, atomic
boundary recall, evidence independence and local/cloud cost are **unmeasured**.
The REQUIRED regression/semantic benchmark is not waived by these smoke results.
LongMemEval's frozen external dev-50 corpus is separate from this synthetic set.

## Ownership and promotion gates

1. #176: obtain an authorized frozen legacy corpus; independent human labels;
   chosen local/remote route, approved prompt and budget; compare E0–E4 with
   quality, noise, duplication and cost metrics. Stop on source mutation,
   unsupported promotion, implicit upload or failed deterministic fallback
2. #192: consume corpus/source-ID/source-hash/profile-version/profile-fingerprint
   cache keys; own resumability, incremental reuse, batching, retries, checkpoints
   and measured cost telemetry. No cache savings are claimed here
3. #137: integrate canonical episode/supporting-turn lineage after its contract
   is merged. This PR neither imports nor copies optional unmerged PR #297
4. #136/PR #313: run-end decomposition remains a separate optional experiment;
   this PR does not depend on its runtime
5. #19: validate semantic admission and global dedup. Existing #92 write safety
   cannot substitute for this decision. No narrow acceptance mode is enabled
6. #15/#16: validate temporal/conflict truth; relation/state proposals never
   resolve conflicts here. #168 receives durable memory only after these gates

The issue remains open; the product default remains A0. Reverting this optional
module and selected-path discovery option needs no source migration or rebuild.
