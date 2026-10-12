# Bounded historical information needs (#139)

This is an **opt-in experimental assisted contract**, not a validated N2 quality
improvement. Deterministic `TesseraEngine.retrieve_context()` and the default
N0 orchestrator path are unchanged. The provider remains application-owned.

## N0 / N1 / N2

- **N0** (default): existing one-sentence `information_need`, one planner query,
  existing store heuristic, deterministic retrieval and legacy state synthesis.
  Its serialized keys, callbacks and original-query fallback stay unchanged.
- **N1**: one structured need or an explicit empty outcome.
- **N2**: up to four independent needs (a caller can lower the cap), or an
  explicit empty outcome. Simple tasks can still produce only one need.

```python
from tessera import TesseraOrchestrator

result = TesseraOrchestrator(
    engine,
    llm_fn=my_bounded_provider_callable,
    information_need_variant="N2",
    max_information_needs=4,
).run("How did the preferred report format change, and why?", top_n=3)
analysis = result.to_dict()["information_needs"]
```

The callable still receives `(system_prompt, user_prompt)` and returns text.
It must enforce its own output-token limit, deadline, spend budget and retry
policy. TESSERA neither discovers credentials nor silently contacts providers.

For analysis without retrieval, use
`tessera.information_needs.identify_information_needs(task, llm_fn, variant="N2")`.
`parse_information_needs()` validates an already captured response offline.

## Strict generated schema

```json
{
  "status": "memory_required",
  "reason": "The question needs evidence from both periods and explaining feedback.",
  "needs": [
    {"id": "need-1", "description": "Earlier report preferences, if recorded", "purpose": "Establish the earlier position without assuming its value"},
    {"id": "need-2", "description": "Later report preferences and relevant feedback, if recorded", "purpose": "Establish whether and why a change occurred"}
  ]
}
```

Only `id`, `description`, `purpose` are accepted per need. Query text, stores,
retrieval operations, inferred answers, evidence types and temporal enums are
not added to this experimental schema. WHAT must be established is separate
from HOW to retrieve it. Unknown fields, missing fields, duplicate JSON keys,
non-text fields, invalid IDs and oversized lists are errors, not repaired plans.

- `memory_required`: nonempty needs
- `no_memory_needed`: exactly `needs: []`, with a reason
- `insufficient_context`: exactly `needs: []`, with a reason; an ambiguous
  referent must not silently become an invented person, event or preference

Both empty outcomes end the assisted run without planner, store access,
original-query fallback or inference. An empty result is therefore inspectably
separate from a search that found nothing. Existing callbacks are emitted with
empty values; the new `information_needs` callback comes first.

## Bounds and failure behavior

| Bound | Enforced by this contract |
|---|---|
| Task text | Nonblank, at most 16,000 characters before any need-provider call |
| Full serialized need prompt | At most 20,000 characters, including JSON escaping |
| Need-generation calls | Exactly one on a valid request; zero repairs/retries |
| Response | String, at most 8,192 characters before JSON parsing |
| Needs | N1: 1; N2: 1–4 configurable maximum |
| Fields | Description ≤600; purpose ≤300; reason ≤400 characters, nonblank |
| Identity | Ordered `need-1`, `need-2`, ... |
| Structured-run candidate cap | Integer `top_n` 1–50 |
| Retrieval fanout | Unchanged single query to at most three existing stores |

Character limits bound local handling, **not provider spend or latency**.
The callable boundary cannot forcibly cancel a remote request or observe hidden
provider retries. Applications must configure real token/time/cost limits. The
experiment capture interface passes explicit token/deadline limits to the
adapter and validates reported usage; it does not certify adapter enforcement.

`InformationNeedsError.code` is a stable machine-readable failure category;
provider exception details and raw invalid responses are not leaked in its
message. Invalid analysis fails before planning/retrieval, with no N0 fallback.
Callers can explicitly decide to use direct deterministic retrieval instead.

## Inspectability and duplication

`OrchestratorResult.information_needs` holds immutable need tuples. `to_dict()`
adds one `information_needs` object only for N1/N2, containing schema version,
variant, status, reason, needs and generation measurements. Tokens are `null`
because the legacy callable returns only text. Timing measures that call and
validation, not downstream planning/inference. Generated needs remain derived
hypotheses about evidence, never sourced facts or reconstructed state.

The provider is explicitly asked to merge semantically redundant facets in its
one response. The validator rejects identical descriptions after case/whitespace
normalization. **This is only lexical duplicate rejection**; paraphrases can
survive. `semantic_deduplication` reports the provider request as unverified.
Independent duplicate-need review is required before any N2 KEEP decision.

For compatibility, needs are projected to one description/purpose block for
the existing single-query planner and store heuristic. The original structured
needs remain intact in the result. N2 does **not** issue one query per need or
select stores from need metadata. Multi-query planning is #140; structured
state reconstruction is #141. No dependency is declared complete here.

## Evidence and adoption gate

See [the controlled experiment](../benchmarks/information_needs/README.md) and
[plain-language stage record](test-cards/139-bounded-information-needs.md).
Offline tests prove bounds, empty-outcome behavior and unchanged defaults.
They do not prove need coverage, semantic deduplication, downstream state
accuracy, or consumer-effort reductions. Keep N0 as the default; ITERATE on the
opt-in contract pending the authorized provider and independent-review gate.
