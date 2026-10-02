# Typed decomposition research packet (#136)

Status: **draft preparation; no human-reviewed labels or provider-quality results**.
This packet tests plumbing for the [Test Card](https://github.com/LuigiFerronatto/TESSERA/issues/136).
It does not select a new runtime default or claim QUMem reproduction/quality parity.

## What is available

- `tessera.typed_decomposition`, an explicitly imported experimental API with
  required `variant="D0" | "D1" | "D2"` selection
- `fixture.draft.json`, eight **assistant-authored synthetic draft** cases, proposed
  atomic units, acceptable types, rationale and unresolved annotation questions
- `evaluate.py`, offline validation/D0/replay/adjudication/scoring CLI and a
  provider-agnostic, human-label-gated capture API
- Tests proving contract mechanics and metric arithmetic using synthetic stubs;
  those stubs are not provider or human-annotation evidence

The ordinary Engine/CLI/MCP decomposer and its legacy prompt are byte-for-byte
unchanged. The known legacy phrase defining factual memory as immutable remains
there intentionally to isolate this experiment; it is **incorrect as an F/P/I
semantic definition**. The correction is confined to the versioned `fpi-v1`
candidate prompts. Documentation-only PR #284 does not establish runtime prompt
fidelity. This candidate neither depends on nor implements provenance PR #297
(issue #137).

## Versioned contract and APIs

`fpi-v1` maps exactly three existing runtime types to F/P/I:

| Runtime type | Research meaning |
|---|---|
| `factual` | Concrete experience/behavior/activity/state/event, with its time and scope; can change and does not imply a general tendency |
| `preference` | User choice/tendency/requirement/constraint, retaining associated rationale and preference changes |
| `procedural_anchor` | User-specific transferable decision principle supported by prior choice/feedback/rationale; not generic advice |

Each response is a JSON array with exactly `type` and `content` per object.
Types are exact, content is nonempty text, duplicate JSON keys/unknown keys are
rejected, and `[]` is a valid intentional result. No prose/fence recovery or
partial-array acceptance occurs in D1/D2. Multiple units of one type are allowed.
Both prompts say to treat episode text as untrusted evidence, preserve temporal
scope/negation/uncertainty, and avoid unsupported user traits.

- **D0**: unchanged deterministic heuristic; even a supplied provider is ignored
- **D1**: one callback, all three types, corrected semantic contract
- **D2**: three independent callbacks in factual/preference/procedural_anchor order,
  each restricted to one type; identical episode bytes; no prior pass output is
  supplied to later passes

D1/D2 remove only same-type, whitespace-equivalent exact duplicates, retaining
first occurrence and reporting the removed count. Casing, punctuation, negation,
chronology and cross-type ambiguity are not conflated by semantic guesses.
A failed/invalid pass stops further calls, discards **all** prior assisted units
and returns D0 with the reason and actual attempted-request count. Programming
errors propagate. Missing providers report zero requests. This fallback preserves
availability; it is not evidence of successful assisted extraction.

```python
from tessera.models import Episode
from tessera.typed_decomposition import decompose_typed_episode, decompose_typed_and_write

# Pure, deterministic and offline. Existing APIs/defaults are not switched.
result = decompose_typed_episode(Episode("A current state.", "", ""), variant="D0")
# D1/D2 are explicit experiments, supplied llm_fn(system, episode_json) -> str.
# Persist only when desired: every candidate goes through the engine's existing
# write_fact/write_preference/write_insight and normal admission/sanitization.
```

`decompose_typed_and_write(engine, mem_id_prefix, episode_id, episode, *, variant,
llm_fn=None, tags=None)` returns filepaths and the decomposition diagnostics.
It adds no drawer, storage schema, index, provenance, retrieval, CLI or MCP
behavior. Like the existing writer, it is **not a transactional batch**: if a later
candidate is rejected, earlier admitted notes can remain. Rejections propagate.

## Offline commands that are safe before review

Run from the repository root in the normal development environment:

```bash
python -m benchmarks.typed_decomposition.evaluate validate \
  --fixture benchmarks/typed_decomposition/fixture.draft.json
python -m benchmarks.typed_decomposition.evaluate d0 \
  --fixture benchmarks/typed_decomposition/fixture.draft.json --output /tmp/d0.json
python -m benchmarks.typed_decomposition.evaluate replay \
  --fixture benchmarks/typed_decomposition/fixture.draft.json --capture /tmp/d0.json
python -m pytest -q tests/test_typed_decomposition.py tests/test_typed_decomposition_eval.py
```

Validation prints the proposed label digest for the reviewer and `quality_status:
not_scored`; it does not approve labels. D0 output/replay is mechanics evidence,
not semantic precision/recall. No command discovers providers or downloads models.

## Required human annotation protocol

1. A named human reviewer reads every episode before provider-backed runs. Edit
   proposed units, acceptable type sets and rationale. Settle the explicit open
   questions about historical preference inclusion and atomicity granularity.
   Each unit should be independently updateable; a preference's explanatory
   rationale stays with the preference. Never turn a single soup order into a
   diet identity or invent generic decision rules.
2. Review all eight categories: facts-only, rationale, explicit preference change,
   transferable principle, tempting unsupported inference, zero durable memory,
   multiple same-type atoms and cross-type ambiguity. An empty unit list is a
   deliberate negative label, not a missing annotation. For genuine ambiguity,
   allow multiple types on **one** expected unit. Do not add duplicate gold units
   just to accept different type assignments.
3. These eight cases are a development packet, not a representative benchmark.
   Expand and independently adjudicate representative episodes/held-out cases
   before claiming general quality gains. Record disagreements and resolution;
   a second human review is recommended, especially on ambiguous cases.
4. Freeze the agreed file before any provider calls. Keep reviewable history.
   `validate` returns `label_digest_for_review`, covering episodes, expected units
   and guidance. Fill `review` with `status: "human_reviewed"`, an actual reviewer
   identifier, timezone-qualified `reviewed_at`, and that `content_sha256`.
   Recompute/re-review after any content change. Do not merely flip draft status.
   **This is a review attestation, not identity authentication**; verify the human
   review through normal repository review history. Software cannot prove a
   claimed reviewer is human. Automated tests use visibly synthetic attestations
   solely to exercise validation logic; do not reuse them as real labels.
5. Before capture, preregister models/settings, number of repeats, expansion/split,
   quality/cost thresholds and KEEP/ITERATE/DROP rules. The issue does not provide
   numeric acceptance thresholds, so none are invented here. Use the exact same
   frozen fixture and provider/model/decoding settings for D1 and D2. Run D0 on
   that same reviewed fixture as a separate baseline. Consider at least three
   repeats; choose the actual budget/sample plan before inspecting outputs.

## Provider capture (requires human-reviewed labels)

Only `capture(fixture, variant=..., provider=..., provider_config=...,
repeat_id=...)` can invoke a caller-supplied provider. It refuses draft labels or
changed review digests **before the first callback**. This PR performs no such
real calls and ships no provider-specific integration or credential discovery.

The callback receives only the system prompt and serialized episode, never
expected units, reviewer guidance, gold types, previous pass output or judgments.
Return `ProviderResponse(text, input_tokens=None, output_tokens=None,
cost_usd=None, cost_kind=None)`. Copy usage from real provider telemetry; cost
must be tagged `actual` or `estimated`. Missing telemetry stays null, not zero or
an invented token estimate. All attempted calls, including failed ones, count.

Record provider/model IDs and exact decoding settings in `provider_config`
(`provider`, `model`, `decoding`); use non-secret identifiers. Capture artifacts
contain raw generated responses, prompt hashes, source/label hashes, fallback
reasons, dedup counts, per-call and episode wall latency, supplied usage/cost and
repeat IDs. Error types are captured without potentially secret error messages.
Inputs are copied before callbacks, so a caller cannot mutate the fixture in
place and silently relabel the run. Keep raw captures private when episodes or
responses contain private information; do not commit raw user episodes.

Replay uses no provider and verifies frozen fixture/labels, current prompt hashes,
full case ordering, actual call usage and exact reproduced results. Changed
fixtures, missing/extra calls, changed outputs or different prompt versions fail.
It preserves **historical capture telemetry**; replay time is not model latency.
A self-authored capture cannot establish that a real provider was used. Keep
provider receipts/run metadata and have the reviewer verify that provenance.

## Human scoring and denominators

Generate a blank adjudication using `template --fixture ... --capture ...
--output /tmp/judgments.json`. For every output, a human records:

- `matched_unit_id`: at most one correct atomic gold unit, or null
- `unsupported`: whether the output invents unsupported information
- `atomicity_violation`: whether it combines independently updateable units
- `duplicate_of`: an earlier semantically duplicate output index, or null
- `rationale`: why the annotation applies

A compound, unsupported or duplicate output cannot earn an atomic unit match;
matching is one-to-one. Correct content with wrong type can earn an extraction
match but fails type accuracy. Empty drafts have null booleans and cannot score.
Freeze adjudication with a separate human `review` attestation/digest over its
non-review fields. It is bound to the exact capture digest. Use `score --fixture
... --capture ... --judgments ...`; there is no automatic LLM/substring matcher.

Reported metrics and conventions:

- Extraction precision = matched atomic units / predictions; recall = matched /
  expected; F1 = 2 × matched / (predicted + expected)
- Acceptable-type accuracy among matched units; ambiguous gold allows either type
- Type macro F1 over **unambiguous matched units**; per-type F1 and number of
  defined classes are reported; missing/extra memories remain in extraction
  metrics, rather than being silently counted as type matches
- Human-judged unsupported/atomicity/duplicate rates among post-dedup predictions;
  mechanical pre-output duplicate removals are reported separately
- Zero-memory accuracy among gold-empty episodes and predicted-minus-gold count
- Capture latency, attempted requests, input/output tokens, cost USD and cost kind;
  any missing call usage makes the aggregate unknown, including failed calls
- `repeated_agreement` is exact typed-output multiset equality across all pairs of
  repeats on the same fixture/variant/provider configuration; **not semantic
  agreement or correctness**. Fallback episode counts remain visible

Undefined zero denominators are null. An empty prediction set with nonempty gold
has F1 0; all-empty gold/prediction has undefined F1 and is assessed by zero-memory
accuracy. `compare` requires all D0/D1/D2 captures and reviewed adjudications,
identical D1/D2 configuration and matched repeat IDs, validates all hashes and
returns `PENDING_HUMAN_DECISION`. Compare fallback incidence alongside quality;
never sell fallback output as successful D1/D2 output or hide failed requests.

## Exact blocker and next review artifact

The available fixture is still explicitly draft, with no real human reviewer,
review timestamp or approved label digest. Therefore no provider-backed quality,
type fidelity, semantic atomicity, latency/token/cost trade-off or default-choice
claim exists. A reviewer can act now on the eight-case annotation packet and
protocol. After labels and experimental thresholds are approved, authorized
provider capture, blind output adjudication and repeated comparison can proceed.
The default remains unchanged; #136 stays open. This packet does not claim to
complete the Test Card's empirical success criteria.
