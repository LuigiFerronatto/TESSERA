# Pinned V2 protocol audit

Audit date: 2026-10-02. Owning issue: #106. Decision: ITERATE, offline preparation
only. No full Test Card criterion or canonical dependency is accepted here.

## Sources and license

The official [repository at `2cc8c540bdb87fe6761629b585e727e1c4704520`](https://github.com/xiaowu0162/LongMemEval-V2/tree/2cc8c540bdb87fe6761629b585e727e1c4704520)
was read, never imported or executed. Its LICENSE is Apache-2.0. `protocol.json`
records per-file Git blob identities. No upstream implementation, dataset prose,
trajectory, screenshot or model output is vendored; fixture/code are original.

Dataset revision is [`f152293e235517d504809563c833d7190b8c713b`](https://huggingface.co/datasets/xiaowu0162/longmemeval-v2/tree/f152293e235517d504809563c833d7190b8c713b),
Apache-2.0 according to the published metadata. The fetched SCHEMA.md digest
matches its published checksum. The checksum listing itself is hashed. All
corpus/archive checksums are **expected metadata, not verified file bytes**.
Archive digests in the pin file come from LFS metadata; they are absent from the
text checksum listing. No data/license conclusion authorizes redistribution.
Paper `2605.12493` is identified by upstream; its revision was not audited and
is null. This audit makes no paper-dependent reproduction claim.

## Mapping to the pinned source

| Contract | Source | Preparation / pending boundary |
|---|---|---|
| `Memory.insert(trajectory)` consumes full selected trajectory objects | `memory_modules/memory.py`; `evaluation/harness.py` insertion loops | Complete invented public-form snapshot retained; every state indexed; legacy `content` form unsupported |
| Public trajectories have domain/environment/goal/outcome/start_url and ordered states | Dataset SCHEMA.md; `memory_modules/trajectory_store.py:prepare_trajectory_insert` | Strict supported public form; unknown fields fail explicitly rather than disappearing |
| Public question text plus image becomes runtime `question={text,image}` | `data/public_data.py:materialize_runtime_questions` | Projection accepts runtime shape only; it does not silently treat public top-level image as a runtime image |
| Query receives text and optional image only | `evaluation/harness.py:build_prompt_row`; `Memory.query` | Sentinel/Engine-spy tests exclude ID, type, answer, raw metadata, evaluator config and trace from retrieval |
| Context items are `{type: text/image, value: string}` | `harness.py:validate_memory_context_items` | Nonempty text and existing synthetic PNG paths; exact-key rule and corrupt-image rejection are stricter local controls |
| Token counting uses multimodal processor input IDs | `harness.py:get_memory_context_processor/count_memory_context_tokens` | Unsupported until immutable processor revision and optional environment are approved; synthetic counts explicitly non-token |
| Budget truncates ordered whole-item prefix, not characters or within text | `harness.py:truncate_memory_context` | Local counter-injected mechanical check; non-monotone or malformed counts fail closed |
| Query invocation context is thread-local and cleared in `finally` | `memory.py:set/get/clear_query_context`; `harness.py:build_prompt_row` | Mechanical scope tests, no semantic use; not concurrent Engine certification |
| Shared identical haystacks reuse memory; nonshared haystacks get fresh instances | `harness.py:all_haystacks_shared/build_prompt_row_with_per_question_memory/main` | Separate instance per fixture haystack; same-haystack questions may repeat, insertion sealed after first query |
| Optional post-query and persistence hooks | `Memory.post_query_hook/_save_backend/_load_backend` | Audit available separately before clear; persistence unsupported; no fake successful save |

## Exact counting and reader implications

The pinned harness loads `AutoProcessor.from_pretrained("Qwen/Qwen3.5-9B")`.
It converts source images with Pillow to RGB, builds one user message containing
text/image content parts, applies the processor chat template with
`tokenize=False` and `add_generation_prompt=False`, then obtains the length of
`processor(text=..., images=..., return_tensors="pt")["input_ids"]`.
Its CLI default context limit is 200,000. It loads all images and counts the
full sequence before selecting a fitting item prefix. These are protocol facts,
not a selected run budget or a claim that the mutable processor is reproducible.

The final reader prompt additionally includes a domain system prompt, a memory
heading, the question text and optional query image. The memory budget therefore
is not the complete reader request budget. V1/PR315 whitespace units, per-image
flat guesses and generic tokenizer estimates are not compliant substitutes.
This preparation tests synthetic budget overflow and order only. It neither
builds nor transmits an official reader request.

## Domains, tiers and metrics

The dataset schema declares web and enterprise. Small maps each domain's
questions to a shared 100-trajectory haystack; medium generally maps to 500,
with some smaller web haystacks. No membership/count was verified by loading
those large/content-bearing files here. The advertised 451-question total is
an upstream statement, not this synthetic fixture's question count.

The [pinned leaderboard contract](https://github.com/xiaowu0162/LongMemEval-V2/blob/2cc8c540bdb87fe6761629b585e727e1c4704520/leaderboard/README.md)
combines complete web/enterprise runs with example-count weighting. It records
`overall_full_set`, gotchas/static/dynamic/procedure accuracies and mean memory
query latency. LAFS gain uses `overall_full_set * 100` and mean query seconds
against the fixed tier reference frontier. The harness also separates
abstention categories and reports query/post-query latency and usage/context
counts. These differ from V1 retrieval Recall/MRR and must stay separate.

The packaging checks include supported reader/judge model-name matching, common
method/tier/haystacks/question IDs and complete per-question logs. A name check
alone does not establish immutable model identity or TESSERA quality acceptance.
No official metrics, LAFS, baseline comparisons or leaderboard package were run.

## Gates preserved

#74/#100 architecture/ledger contracts remain intact. #103/#104/#105 canonical
acceptance remains required, along with a reviewed immutable model/processor
configuration, provider/resource authorization, real image support and an
upstream integration review. Only then can full V2-B compliance and V2-C/D be
measured. V2-E/medium requires its separate readiness/cost decision. This audit
and synthetic fixture neither change routing nor close #106.
