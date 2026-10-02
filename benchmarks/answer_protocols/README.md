# Reader, judge and full-500 preparation

**State: DRAFT / ITERATE. Benchmark applicability: SMOKE_ONLY.** This is
repository-only offline preparation for [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103),
[#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) and
[#105](https://github.com/LuigiFerronatto/TESSERA/issues/105). It does not execute
or accept any of those Test Cards. No reader or judge has been selected, no
human calibration label or quality threshold is accepted, and no full-500 run
has occurred. The accepted [#74 boundary](../../docs/adr/0001-core-vs-optional-llm-boundary.md)
continues to keep these concerns outside `tessera/` and base installation.

## Why this can be prepared before dependencies are accepted

The canonical #96/#100 track remains retrieval-only. #28 has a separate
[unmerged draft PR #315](https://github.com/LuigiFerronatto/TESSERA/pull/315),
head `85638e1320ca68bfdd15efbfaed14a1791218120`, with frozen capture/replay
interfaces. This work does not cherry-pick that branch, reproduce its renderer,
change the ledger, or treat synthetic presentation checks as accepted QA evidence.
It accepts the proposed renderer's opaque message row and hashes as an interface
fixture only. After #28 is accepted, its canonical interface must be reverified.

| Issue | Technical preparation delivered | Exact remaining execution/acceptance gate |
|---|---|---|
| #103 | Closed request/output/capture validation, immutable message hashing, evaluator-field guards, literal synthetic oracle responses, failed-attempt retention, write-before-mock-inference and persistence-before-label-join checks, J0 diagnostic metrics | Accepted #28/#74/#96/#100 contract compatibility; immutable real reader/model/tokenizer revision and prompt/configuration; authorized budget/retention/credentials flow; frozen dev-50 capture; two real passes with separate four-case abstention, citation, usage and repeatability reports |
| #104 | Eight unlabeled calibration coverage slots and independent two-reviewer/adjudicator review validation | Accepted #74/#100/#103; license-compatible fixed sample; independent real labels/rationales and accepted thresholds frozen before held-out evaluation; pinned real judge/prompt/rubric; traceable verdict parser/provider implementation; actual calibration, failure, agreement and sensitivity reports |
| #105 | Checksum-verified 500-ID/order manifest, draft preregistration and strict structural/readiness validator | Accepted #96/#100/#103/#104 (and compatible #28); canonical commits/artifacts/configs; reviewed thresholds, budget, attempts, exclusions, statistics and retention; explicit execution authorization; future checkpointed F0–F4 execution and complete reports |

No issue is closed, no KEEP decision is claimed, and no merge or runtime/default
change is included. `execute` is deliberately unavailable even if a caller fills
all preregistration fields. Review metadata is evidence to verify, not a security
capability or proof of actual human approval.

## Offline commands

From the checkout with its development environment active:

```bash
python -m pytest -q tests/test_answer_protocol_preparation.py
python -m benchmarks.answer_protocols.cli synthetic --output artifacts/answer-protocols/run-a
python -m benchmarks.answer_protocols.cli synthetic --output artifacts/answer-protocols/run-b
python -m benchmarks.answer_protocols.cli validate \
  --selection benchmarks/answer_protocols/full500-ids.json \
  --preregistration benchmarks/answer_protocols/full500-preregistration.json
```

The two synthetic summaries must match. They contain three successful mock
captures, one preserved mock provider failure, and one preserved parse failure
before a successful retry. Zero latency/tokens/cost are explicitly tagged
`synthetic_not_measured`, not claimed measurements. These are serialization,
provenance and failure-path controls, not TESSERA performance or calibration.
All inputs/answers are invented. There are no provider clients, network calls,
credential reads, model invocations, callable adapters or dataset retrieval here.

The existing full suite automatically tests these offline mechanics. No workflow,
provider secret, AI judging or mandatory paid CI job is added.

Expected negative execution check:

```bash
python -m benchmarks.answer_protocols.cli execute \
  --selection benchmarks/answer_protocols/full500-ids.json \
  --preregistration benchmarks/answer_protocols/full500-preregistration.json
# Exit 2: execution blocked; lists missing review/model/budget/dependency gates.
```

To reproduce the only full-dataset operation, use an already acquired official
file. This reads/validates its pinned bytes and projects IDs; it never indexes,
retrieves, renders, scores or generates responses:

```bash
python -m benchmarks.answer_protocols.cli prepare-ids \
  --dataset /path/outside/git/longmemeval_s_cleaned.json \
  --output /path/outside/git/reproduced-full500-ids.json
```

Dataset SHA-256:
`d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
ID/order canonical JSON SHA-256:
`a4849b8afda6b6ed31ead4fc28d00784d2d5fef945be87642f5ce3ab710b21c4`.
Order is the pinned file's original order. The immutable dataset revision here is
the content SHA, not an assertion that the remote `main` URL is immutable.
`upstream_code_revision` is the existing #96 source-code pin and is explicitly
not presented as the Hugging Face data repository revision. Selection validation
rejects ID substitutions/reordering even if a caller recomputes its local hash.
No source text, category labels, answers or provider outputs are versioned.

## Reader schemas and frozen transport boundary

`reader.py` contains closed schemas: unknown/missing fields, bool-as-integer,
non-finite values, duplicate JSON keys, duplicate citations and inconsistent
abstention/answer states fail. The proposed #28 input is precisely:

```text
query_id, renderer, messages, input_sha256, metrics
```

`make_request` verifies the unchanged system/user messages and their canonical
hash. It receives the expected frozen evidence and policy hashes separately.
The raw question ID is hashed to `question_ref`; it is never placed in provider
payloads, so `_abs` and benchmark category identities do not leak through IDs.
No evidence is selected, rendered, truncated, reordered or re-retrieved here.
The request retains:

```text
schema_version, question_ref, frozen_evidence_sha256,
reader_input_policy_sha256, renderer, configuration_sha256,
input_sha256, payload { messages, response_schema }, request_sha256
```

Only `payload` would be sent by a future reviewed provider adapter. Its response
schema permits only `answer` (string), `abstained` (boolean), `citations` (unique
string list). Additional semantic validation requires an empty answer on
abstention and nonempty text otherwise. This proposed output instruction/format
must be explicitly adopted and hashed with the real reader protocol; appending
an instruction to #28's messages silently is forbidden.

`reader-configuration-draft.json` includes all #103 identity, decoding, renderer,
tokenizer, question-membership, artifact and environment fields, all null.
The current mock runner rejects any real model configuration. This is intentional:
it cannot smuggle an unreviewed reader into an apparently pinned execution.

Each synthetic capture holds its request and contiguous numbered attempts.
Every attempt stores raw response and byte hash, parsed output, status, provider
error and explicitly synthetic usage. Status is `ok`, `parse_failure` or
`provider_failure`. Three attempts are the bounded plumbing fixture limit, not
an accepted provider retry policy. A successful output cannot be replaced by a
later attempt. A destination must be new; failed/partial directories are retained.

`run_scripted` writes `request.json` before parsing literal mock responses,
then writes each attempt exclusively, `capture.json`, and `complete.json` last.
`load_capture` verifies all copies, hashes, expected files and the final receipt;
missing, modified or extra attempts fail closed. `score_persisted` loads this
completed artifact before accessing evaluator references, and only joins a
matching question hash. This is local audit plumbing, not tamperproof storage
or safe resume of real provider work. A future real runner needs checkpointed,
append-only attempts and separately reviewed raw response retention.

## Isolation limits and J0

Structural label guards reject answers, evidence labels, `has_answer`, category,
verdict and rationale keys, including nested/discarded metadata. They cannot
identify labels hidden inside arbitrary prose, prove where an opaque hash came
from, or make an untrusted producer label-free. Do not pass #96 evaluator results
into this interface. A future real adapter must consume a reviewed label-free
capture producer and verify the complete #28 artifact/manifest before use.

J0 is evaluator-only `reader-j0-draft/1`: Unicode word tokenization, case folding,
normalized token equality and multiset F1, plus an explicit abstention correctness
flag. This is a declared mechanical diagnostic, not the official semantic metric
and not unsupported-claim detection. Provider/parse failures retain their status
and null metrics, never an incorrect-answer label or silent denominator removal.
There is no answer-quality field added to #100 retrieval ledger and no aggregate
LongMemEval score claimed.

## Independent-human judge review packet

See [human review instructions](HUMAN_REVIEW.md) and
`judge-calibration-draft.json`. The eight category slots are a sampling coverage
plan, not sampled examples or human judgments. All model identities, prompt/rubric
hashes, budget/threshold decisions, sample metadata and human labels remain null.
`validate_human_review` only checks the mechanics of two independent reviews,
retained disagreement and a distinct third adjudicator. Its unit tests use
explicitly synthetic identities and are not independent human review.

## Preregistration and execution control

`full500-preregistration.json` is structurally valid and intentionally not ready.
Closed nested shapes pin selection/data membership and require explicit retrieval,
renderer, reader, judge, calibration, metric, policy, budget, canonical-dependency,
review and authorization fields. Missing values and invalid hashes, mutable bare
aliases, nonfinite/negative budgets, invalid attempts and missing/reordered
dependencies cannot pass readiness. A REVIEWED status alone unlocks nothing.
A future revision must additionally verify actual immutable provider revisions,
review evidence, authorization scope and every referenced file's contents; string
shape cannot prove those facts. This PR has no execution implementation at all.

Freeze the final reviewed record before inspecting outcomes. Any later change
requires a new candidate record linked to the original; never overwrite a run.
F0 retrieval, F1 reader, F2 judge, F3 abstention and F4 official category analysis
must remain separate, with complete counts/denominators, failures, CIs under the
preregistered method, cost ceiling and artifact hashes. Full-500 contains dev-50
instances: it is a broader profile, not an entirely unseen independent holdout.
Do not tune against full-set outcomes or present these IDs as a completed run.

## Storage and rollback

Only compact ID/hash manifests, null drafts and invented fixture code belong in
Git. Runtime captures, source/question text, labels and provider outputs belong
in approved private experiment storage under a reviewed license/retention policy.
The default local `artifacts/answer-protocols/` path is ignored. No repository path
is a guarantee of access control; permission and license review remain gates.
Revert the preparation commit to remove these modules and docs; no source, memory,
index, runtime state, ranking/default, workflow, ledger or package schema migrates.
