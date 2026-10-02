# Frozen-evidence renderer controls (#28)

Experimental, repository-only capture/replay tooling. The candidate freezes
already retrieved evidence once and renders R0/R1/R2 offline with the same query,
order, scores, input policy and per-query input budget. It never invokes a
retriever, reader, judge, provider, or source-file resolver during replay.

**Decision: ITERATE.** The synthetic controls establish presentation mechanics,
not downstream QA, abstention, or retrieval benefit. No default Engine, CLI,
MCP, ranking, indexing, or canonical benchmark behavior changes.

## One reproducible offline experiment

Use the repository development environment (outside the checkout). From a clean
candidate checkout:

```bash
python -m benchmarks.rendering.cli fixture --output-dir /tmp/render-capture
python -m benchmarks.rendering.cli replay \
  --capture /tmp/render-capture/capture.json --input-token-budget 180 \
  --output-dir /tmp/render-180-a
python -m benchmarks.rendering.cli replay \
  --capture /tmp/render-capture/capture.json --input-token-budget 180 \
  --output-dir /tmp/render-180-b
cmp /tmp/render-180-a/inputs.json /tmp/render-180-b/inputs.json
cmp /tmp/render-180-a/summary.json /tmp/render-180-b/summary.json
python -m pytest -q tests/test_renderer_ablation.py tests/test_benchmark_reporting.py
```

Output directories must be new. Reruns never overwrite earlier attempts. Use new
names if these example paths already exist. Source-bearing output is allowed
only outside the checkout or under ignored `artifacts/rendering/<run>/`.
`--allow-dirty-worktree` is a development-only override; its manifest records
`repository_dirty: true` and `reproducible_source: false`. Do not present that run
as exact-commit evidence. The synthetic capture uses all-zero source commit IDs
to explicitly identify invented input, not a real TESSERA retrieval run.

`fixture.py` invents three cases: late selected evidence, a retrieved memory with
no selected span, and an empty retrieval. It contains no dataset or model output.
Repeating the experiment with budgets 512 and 10000 checks tight-budget versus
effectively untruncated controls without selecting a winning renderer.

## Capture real evidence once

Call `capture_evidence` immediately after existing, authorized retrieval, before
an evaluator joins labels:

```python
from benchmarks.rendering.frozen import capture_evidence, canonical_json

capture = capture_evidence(
    [{"query_id": stable_query_id, "query": query_text, "hits": engine_hits}],
    tessera_commit=exact_retrieval_commit,
    retrieval_contract_commit=exact_contract_commit,
    retrieval_configuration=frozen_configuration,
)
# Persist canonical_json(capture) outside Git, then reuse it for every renderer.
```

For multiple queries, pass all query records in their already frozen order.
The caller owns retrieval provenance; `capture_evidence` does not reconstruct or
verify a claimed source commit. Keep the original configuration alongside the
capture, and compare its recorded hash. Capture is a consistency/checksum
boundary, not cryptographic proof that an untrusted producer is truthful.

Alternatively, the `capture` CLI consumes a JSON object with exactly `queries`,
`tessera_commit`, `retrieval_contract_commit`, and `retrieval_configuration`, using
the same API. It writes a new `capture.json`:

```bash
python -m benchmarks.rendering.cli capture \
  --input /tmp/label-free-engine-hits.json --output-dir /tmp/frozen-capture
```

Never feed canonical LongMemEval `results.json` directly into this interface:
it contains evaluator labels and does **not** contain complete source/evidence
bodies. A later adapter must capture raw Engine hits while the existing
label-free source corpus is still alive. This candidate does not modify that
adapter or regenerate a dataset. It only tests compatibility with real current
Engine hits on an invented temporary corpus.

## Closed capture and isolation rules

- Snapshot query text/IDs, ordered memory/evidence IDs, exact numeric scores,
  full bodies, selected spans, direct related IDs, and existing evidence records
- Deep-copy nested data; reject duplicate query/memory/related IDs, non-finite
  scores, malformed evidence records and spans not present in their own bodies
- Check the capture checksum before every replay. Changed text, query order,
  IDs, scores, provenance or configuration hash invalidates it
- Do not pass frontmatter, score explanations, physical filepaths, categories,
  future temporal/conflict/sufficiency fields or arbitrary metadata to the reader
- Reject known evaluator-owned label keys recursively, even in metadata that
  would otherwise be discarded. JSON duplicate keys fail rather than overwrite
- Never put `query_id` into reader messages. Source IDs/paths and related IDs use
  stable SHA-256 aliases, so benchmark category names or `_abs` suffixes cannot
  leak through navigation. The local capture retains the exact audit mapping
- The structural guard cannot recognize an expected answer deliberately copied
  into free-form source prose. Use a trusted, label-free adapter, as required by
  #96/#103; label-bearing evaluator artifacts are not valid source inputs

The current evidence schema is accepted strictly. Future schema expansion must
be reviewed and versioned instead of silently admitting unsupported signals.

## Exactly what varies

| Arm | Context payload |
|---|---|
| R0 | Complete raw body, behind the same neutral memory-reference header |
| R1 | Existing selected span, document and query-span provenance |
| R2 | R1 plus existing direct related IDs and full-memory reference |

R1/R2 use the full body with an explicit marker when no selected span exists.
The marker means “no span was selected”, not “this evidence is insufficient”.
No model summarizes or extracts additional text. Null exact source spans stay
null. R2 supplies no temporal-validity, authority, relation-confidence, conflict
winner, or sufficiency claims. The full-memory reference resolves through the
capture's identity mapping; replay does not follow it, read files, or retrieve
additional information. A later reader may not perform navigation calls in this
controlled arm without defining a separately registered experiment.

All arms use the same two-message input policy. Provenance is rendered by the
same text function for R1/R2, not as an additional JSON transport arm. IDs are
audit metadata; scores remain frozen in capture and are not shown as confidence.

## Budget policy

`input_token_budget` applies per query and arm to the combined system/user text.
The tokenizer is pinned to Unicode whitespace (`re.finditer(r"\S+")`). It is a
deterministic offline unit, **not model tokens**, billing usage, or a provider
context-window guarantee. Long hash references count as one whitespace unit;
model-token economics may therefore differ materially.

Reserve the identical full policy, question, wrappers and suffix first. If they
exceed the budget, fail without truncating the query. Render the ordered context,
then retain its prefix through the last complete token that fits. Do not
re-rank, select smaller later hits, use gold evidence to pack context, pad arms,
or silently change budgets. A provenance record may be partially cut; it counts
as complete only when every emitted field fits. The untruncated frozen capture
remains available for audit, but it is not additional reader input.

Provider execution requires a separately frozen real tokenizer and message
overhead policy, a new version/hash, and rerun controls before outcomes. The
current manifest deliberately leaves reader and judge configuration null.

## Artifacts and metric interpretation

- `capture.json`: local source-bearing immutable snapshot
- `manifest.json`: source, retrieval identity/order, query-order and policy
  hashes, input hash, exact renderer commit/environment and zero-call execution
- `inputs.json`: local reader messages and per-query presentation diagnostics
- `summary.json`: compact aggregate mechanics, no source/query text or IDs

The replay's `inputs_sha256` includes messages and their presentation metrics.
Each message set also has its own `input_sha256`. Stable aliases are one-way
references: auditors can recompute `neutral_reference(kind, original_value)`
from the capture to resolve them. Full original IDs and source paths are not
silently discarded, but intentionally remain outside reader messages.

Presentation metrics have explicit counts and denominators:

- Selected-span retention: fully retained whitespace tokens within the original
  selected span divided by its token count; no selected spans means null
- Complete-span retention: count of selected spans fully inside retained text
- First selected-span input token: first retained selected-span token across
  system/user text. This is not the ledger's first *gold-relevant retrieval rank*
- Selected-span density: retained selected-span tokens divided by context tokens;
  “selected” is a lexical extraction diagnostic, never gold correctness
- Provenance completeness: fully emitted document/query-span records divided by
  available records. Exact-span record counts are separately reported; null
  spans cannot become precise merely because their record was fully rendered
- Context/input counts, truncation, missing-span count, and raw context overhead

Repeated identical text elsewhere does not count as retaining a selected span
from a later memory. Locations are tracked within the owning memory. For repeated
occurrences inside the same raw body, the first occurrence is used only for the
presentation-position metric; ambiguous provenance remains null.

Retrieval metrics are not recalculated. QA/abstention accuracy, task success and
reader latency are null (`NOT_RUN`), not zeros. The replay summary is **not** a
LongMemEval dev-50 ledger record: the #100 schema is closed and retrieval-only.
Canonical ledger schema, baseline/forward records, comparison and CI stay intact.

## Quality blocker and dependency boundary

Offline controls are executable now. A defensible renderer choice is not yet
supported: no provider/model/revision or provider tokenizer is selected and
pinned, no bounded paid execution is authorized here, and no DEV/held-out reader
outputs or calibrated verdicts have been measured. No provider was attempted;
this is not a claim that credentials or service access are unavailable.

The [draft preregistration](preregistration.json) lists the missing run manifest
and proposed acceptance criteria. It is not permission to run. #103 still
requires #28's accepted frozen interface (plus #74/#96/#100), #104 still requires
the accepted #103 reader baseline, and #105 still requires both #103/#104.
Opening this candidate does not close or bypass any of those gates. #28's
downstream-benefit criterion remains open; maintainers must reconcile that
empirical criterion with the staged reader dependency before any final KEEP.
