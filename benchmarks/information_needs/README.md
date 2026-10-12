# #139 N0/N1/N2 controlled experiment

## Frozen design

`scenarios.json` freezes six scenarios: simple fact, preference evolution,
compound facts/preferences/insights, no memory, ambiguous referent, and broad
scope. It also freezes a six-note project-neutral corpus. All note metadata
dates are fixed to `2026-03-01T00:00:00Z`; temporal statements live in the note
text. Retrieval is the real Engine, `top_n=3`, one existing planner query and
unchanged store heuristic for all variants. There is no #140 fanout or #141
state contract. Proposed expected facets/evidence IDs are visible for review,
**not independently reviewed labels and never supplied to the real provider**.
The fixture hash is canonical sorted JSON SHA-256, emitted by every run.

```bash
python -m benchmarks.information_needs.run --mock --output /tmp/needs-mock.json
python -m benchmarks.information_needs.run --replay /path/capture.json --output /tmp/needs-replay.json
python -m benchmarks.information_needs.run --replay /path/capture.json --review /path/review.json --output /tmp/needs-reviewed.json
```

Mock mode deliberately uses the proposed facets as an oracle test double.
It checks schema, branching, bounded work and deterministic retrieval plumbing,
not the hypothesis. No empirical quality score is produced for mocks, and
passing a review to mock mode is rejected. `/tmp` reports contain prompts and
outputs and should not be published if a real provider used private context.

## Obtaining real captures, only with authorization

No provider credentials are available or required for the offline run. No paid
calls were made. The application that owns an authorized provider can call:

```python
from benchmarks.information_needs.run import run_experiment

report = run_experiment(
    capture_fn=my_provider_adapter,
    provider={
        "name": "actual provider name",
        "model_revision": "exact immutable model revision",
        "temperature": 0,
        "max_output_tokens": 1024,
        "timeout_s": 30,
        "captured_at": "actual ISO-8601 capture time",
        "adapter_revision": "exact adapter source revision",
    },
)
# Save report["provider_capture"] as capture.json for the offline CLI.
```

`my_provider_adapter(system, user, *, max_output_tokens, timeout_s)` must enforce
those transport limits, disable hidden retries and return:

```json
{"response": "actual response text", "usage": {"input_tokens": 400, "output_tokens": 80, "latency_ms": 1000}}
```

The numbers above illustrate the schema, not measured usage. Inputs consist
only of the fixed task, each variant's generated needs and actual retrieved
notes. The runner stores exact system/user prompt hashes and validates them on
replay. Wrong corpus, changed prompts, missing/extra calls, oversized replies or
invalid usage fail. Raw replies above 8,192 characters are rejected. The capture
budget is at most **54 generation calls** (6 scenarios × 3 variants × 3 stages),
at most 2,048 output tokens/call and at most 60 seconds/call as passed to the
adapter. This is not a dollar cap: the application must approve total input plus
output pricing before capture and enforce a total spend limit. There are no
repair/retry calls. A malformed generated need is a recorded failure, not a
successful skip. Provider transport/capture failures abort the capture.

## Independent review inputs and metrics

Before judging the hypothesis, an independent reviewer must approve or revise
(and refreeze if revised) each scenario's expected facets, critical facets,
expected evidence IDs, memory-dependency label and explicit ambiguity label.
Then review blinded N0/N1/N2 outputs. Keep the per-need-to-expected-facet mapping,
unsupported-need IDs, semantic duplicate groups, supporting evidence IDs and
state assertions with evidence citations as the review workpaper. Lexical
matching does not replace those judgments. Wrong or missing source assertions
must count against state accuracy even if the generated text is fluent.

The scoring JSON requires `fixture_sha256`, `report_sha256` (the canonical
`digest(report["runs"])`), reviewer identity, `status: independently_reviewed`,
and `runs` containing all 18 `scenario/variant` keys. Every entry has exactly:

- `need_coverage`: covered approved expected facets / expected facets
- `unsupported_need_rate`: unsupported proposed needs / proposed needs
- `duplicate_need_rate`: redundant semantic needs beyond first / proposed needs
- `evidence_recall_at_3`: reviewed expected evidence IDs in returned top 3 /
  expected evidence IDs; this is retrieval evidence, not answer accuracy
- `state_accuracy`: correct grounded state assertions / reviewed assertions
- `no_memory_needed_accuracy`: correctness of the explicit memory-dependency
  decision (review N0 free text and actual behavior; it has no structured flag)
- `missed_critical_facets`: count of approved critical facets not established
- `agent_authored_search_formulations`: actual consumer-authored memory search
  formulations before useful reasoning, from a frozen consumer task transcript
- `duplicate_formulations_across_repeated_runs`: duplicate formulations measured
  from separately captured repeated runs/subagents on the identical task

Use `null` for genuinely inapplicable or unavailable measurements, never zero.
The scorer retains applicable-run denominators. Consumer effort and repeated-run
metrics require independent consumer transcripts; this one-pass harness cannot
manufacture them. Record token counts and latency from actual `calls[].usage`;
local replay timing is nulled and is not provider latency. Publish model,
adapter, corpus, prompt, reviewer/workpaper and consumer-transcript identities
beside any empirical aggregate. Never label a test double a model evaluation.

## Predeclared decision

The offline mechanics gate must pass and deterministic baseline CI must remain
unchanged. Full N2 adoption remains **BLOCKED** until real captures, independently
reviewed expected facets, semantic duplicate review and consumer-effort traces
exist. Suggested decision criteria for the review meeting: N2 must beat N0 and
N1 on compound/temporal coverage and evidence recall without higher unsupported
need rate; ambiguous/no-memory decisions must be correct; N2 must not regress
simple-task quality; extra token/latency cost must be explicitly accepted.
State and consumer-effort measurements must support the chosen decision rather
than be inferred from better need counts. The six scenarios are a development
experiment, not sufficient evidence of generalization. Even completed review
produces PENDING, never automatic KEEP. Keep N0 default pending that decision.

The separate REQUIRED LongMemEval dev-50 job checks unchanged deterministic
retrieval on the exact candidate. It does not evaluate these assisted variants.
