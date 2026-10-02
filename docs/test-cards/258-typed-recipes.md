# 258 — Evaluate safe composition of public reads

| Field | Value |
|---|---|
| Issue | [#258](https://github.com/LuigiFerronatto/TESSERA/issues/258) |
| Record status | `IN_PROGRESS` |
| Capability type | Opt-in architecture/runtime experiment |
| Pull request | [#306](https://github.com/LuigiFerronatto/TESSERA/pull/306) |
| Head commit | Exact current head is recorded by PR #306 checks |
| Merge commit | Not merged |
| Decision | `ITERATE` (proposed) |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

## In one sentence

Two existing read operations can be composed safely, but the experiment has not
yet shown that its extra layer is simpler than direct calls.

## What problem existed?

Repeated orchestration could drift across callers. A closed typed catalogue and
inspectable sequential recipes might preserve current operations while reducing
duplication. This experiment asks whether that additional layer earns its cost.
It does not promote an agent-memory API or select downstream semantic workflows.
The live issue's design-readiness caveat remains relevant: two demonstrations
are not evidence for adopting a general workflow platform.

## How did TESSERA behave before?

Before this candidate, callers invoke the Engine and EvidenceLedger directly.

## What changed or is being tested?

After it, an explicit `tessera.recipes` import can plan/run two compositions over
an already initialized Engine. Existing defaults, Python methods, CLI and MCP
are unchanged. No package import, configuration discovery, hooks, or repository
opening executes a recipe.

## How does it work now?

**CANDIDATE — NOT YET ON MAIN.**

The closed `PrimitiveRegistry` has immutable descriptors and no register/import
method. Version 1 descriptors expose typed scalar arguments, named versioned
output contracts, owning cards and explicit read effects:

- `query`: `TesseraEngine.retrieve_context_contract`, owned by #68
- `query_store`: `TesseraEngine.retrieve_from_store`, parity owned by #120
- `ledger_for_memory`: `EvidenceLedger.for_memory`, owned by #11

The runner validates core typed output fields and preserves the entire original
result payload; it does not reinterpret scores, evidence, drawers, or authority.
Native YAML dates/datetimes remain unchanged in Python outputs and use the
existing CLI/MCP string convention only for byte budgets/hashes; unsupported
non-JSON objects fail safely.
Retrieval descriptors truthfully mark `deterministic=False`: the existing
`score_explain.recency_boost` depends on the Engine clock even with zero recency
weight. Repeatability requires unchanged inputs, index, source state and clock.

Built-ins:

1. `search_and_provenance`: query, then the ledger records for the first hit's ID
2. `compare_drawers`: the same query through facts and preferences retrieval

The first is a provenance lookup, not query-aware evidence expansion. If search
returns nothing, its second step fails with `REFERENCE_UNAVAILABLE`, retaining
the completed empty search in the structured result. A branch/empty-result
policy could improve ergonomics only in a later measured iteration.

## Concrete example

```python
from tessera.recipes import RecipeRunner, builtin_recipe

# engine was explicitly initialized/indexed by the caller, outside this recipe.
runner = RecipeRunner(engine)
recipe = builtin_recipe("search_and_provenance")
plan = runner.plan(recipe, {"query": "auditable memory"})  # dry-run, no reads/mutations
result = runner.run(recipe, {"query": "auditable memory"})
```

`plan()` reports recipe/source identity, versions and registry hash, input hash,
capabilities/effects, source roots, empty canonical effects, no network/provider,
call count and budgets, external trust gate, and cancellation/resume policy.
It never calls a primitive, builds an index, opens source files or writes a log.
An invalid/impersonated built-in fails both planning and execution.

External definitions are supplied as text, never filenames or remote URLs:

```python
from tessera.recipes import load_recipe

recipe = load_recipe(reviewed_yaml_text)
plan = runner.plan(recipe, {"query": "auditable memory"})
# Only after the application/user reviews and approves this fingerprint:
result = runner.run(recipe, {"query": "auditable memory"},
                    approved_fingerprint=approved_fingerprint)
```

The approval is the SHA-256 of normalized definition bytes. Whitespace and
comments are not executable changes; changed operations/inputs/versions produce
a new fingerprint. Nothing auto-approves a loaded document. Raw YAML text and
source paths are not used to execute code. A trusted Python application supplies
the Engine and can call direct APIs; this module is not a Python-code sandbox.

## Restricted grammar and safety

The root has exactly `name`, `version`, `inputs`, `requires`, `budgets`, `steps`,
`outputs`. Each step has `id`, `use`, `version`, `with`, `on_error: stop`.
Declared inputs are `text`, `integer`, `boolean` or the three-drawer enum.
References are closed objects with a `ref` field: `inputs.NAME` or the typed
`steps.PREVIOUS.hits.INDEX.id` field. Static validation rejects forward edges,
cycles, type mismatches, negative/oversized indexes and arbitrary attribute
access. Runtime validation catches unavailable hits and invalid resolved values.

- Maximum definition: 32 KiB, 2,048 YAML events, depth 12; duplicate keys,
  anchors/aliases, explicit tags, merge keys and non-JSON values are rejected
- Maximum 16 sequential steps, 16 scalar inputs, 4,096 characters per text,
  `top_n` 1–50, 30-second cooperative deadline, 256 KiB accumulated output
- Loops, conditionals, templates, dynamic imports/registration, shell/Python,
  environment/secret expansion and remote references are absent and rejected
- Exact declared effects must match resolved descriptors and caller capabilities
- Engine/store/source-root binding cannot change between steps; source paths
  must remain within those roots, without symlinks or special files
- An 8 MiB unique indexed-source size preflight is disclosed in the plan;
  repeated segment paths count once. These are not process memory/CPU limits
- No canonical writes, provider/network calls, index builds or persisted journals
- Output-size rejection occurs after a primitive returns; it does not claim the
  primitive did not run. `invoked`/`returned` distinguish those states

The caller must serialize access to its Engine and exclude adversarial concurrent
filesystem changes; path preflight is not a kernel sandbox and does not eliminate
TOCTOU races. Source content can legitimately be present in requested results.
The plan/journal never echo input values, results or exception text: they use
safe codes and hashes. An application must handle returned evidence as sensitive
source content rather than assuming a redaction system.

## Failure, cancellation and retry

Every result includes the plan, status, step journal, completed outputs, error
code, completed-step count, `canonical_mutations: 0` and `resumable: false`.
Stop-on-error preserves prior output. Callback failures also return a structured
partial result without leaking exception text. Cancellation and timeout are
checked before/after synchronous reads; an in-flight read is not preemptible.
A completed read remains journaled as completed even when cancellation/deadline
is observed immediately afterward. No write rollback is claimed.

`resume=` is rejected. No caller-supplied historical outputs are trusted or
silently reused. A fresh explicit replay reexecutes reads, cannot duplicate
canonical memories and may differ if source/index/clock state has changed.
Hashes plus versions identify records, but the in-memory journal is not a
signed receipt, durable checkpoint, or full source snapshot.

## How was it validated?

Run with an external virtual environment containing this checkout:

```sh
python -m pytest -q tests/test_issue_258_recipes.py
python -m pytest -ra
python scripts/experiments/evaluate_recipes.py
python benchmarks/sanity/ci_eval.py --output-dir /tmp/recipes-sanity
```

The synthetic offline experiment compares R0 direct calls to R2 recipes, 30
repeats each. The final local measured medians were 2.354/2.972 ms for direct/recipe
search+provenance and 4.667/5.333 ms for direct/recipe drawer queries. These are
local small-fixture observations, not performance guarantees; rerun on the
exact candidate. Both had zero parity/replay mismatches and zero filesystem
changes. Real CLI JSON and MCP Python adapter results match the recipe's query
payload without stripping evidence. Existing protocol tests remain in the full
suite; this does not add a recipe MCP tool.

## What improved?

The built-ins require 31 and 35 serialized YAML lines for two direct operations.
Production orchestration lines removed: **0**. Primitive calls saved: **0**.
Agent/tool calls saved: **0**. The experiment adds a substantial parser, planner
and safety surface to make these two small workflows declarative. Shared
mechanics and inspectability are demonstrated; meaningful production reuse and
lower maintenance cost are **not** demonstrated.

**Proposed decision: ITERATE.** Keep direct APIs/defaults, leave this candidate
opt-in and draft for maintainer judgment, and do not promote R1/R2/R3 as adopted.
Do not grow the grammar merely to manufacture reuse. DROP remains reasonable if
real callers do not justify the extra layer. No retrieval-quality benefit is
claimed; benchmark applicability is SMOKE_ONLY because only execution mechanics
wrap current operations. The unchanged deterministic sanity suite remains the
regression check.

## What remains unimplemented?

Canonical writes and candidate-producing operations fail as unavailable
primitives, even if YAML declares write/network effects. #19/#92 admission and
write safety are never substituted with recipe policy. Portable imports,
conversation digestion, learning and enrichment remain with #204/#191/#254/#176.
Unmerged #263 receipts, #73 revisions, #137 lineage, #166 CLI and #196 hooks are
not dependencies or copied implementations. #171 owns future semantic intents.
The experiment does not satisfy the issue's candidate/write/resume workflow
acceptance criteria; those remain gated, not silently marked complete.

Rollback: remove the isolated module, focused tests and experiment script/docs.
No data migration, source rewrite, persisted recipe state or default behavior
must be undone. After any merge, reconcile the canonical commit and decision
before describing this as implemented or using it as a dependency.


## What is unlocked next?

No dependent card is unlocked by an unmerged experiment. Maintainers can decide
whether a real caller warrants another bounded iteration; no grammar expansion
or default integration is selected here.

## Technical provenance

- Canonical base: `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Candidate: [PR #306](https://github.com/LuigiFerronatto/TESSERA/pull/306)
- Focused contracts: `tests/test_issue_258_recipes.py`
- Direct/recipe comparison: `scripts/experiments/evaluate_recipes.py`
- Existing canonical contracts: [output](../OUTPUT_CONTRACT.md),
  [write gate](../WRITE_GATE_CONTRACT.md), [MCP](../MCP_RUNTIME.md)
- Independent design; no upstream AGPL implementation copied
- Exact head CI and benchmark results are recorded on PR #306; merge not performed

## Evolution

Direct calls on canonical main -> isolated read-only candidate -> ITERATE
pending real reuse evidence. Candidate-producing and canonical-writing flows
remain with their separate unmerged owning cards. Post-merge reconciliation
is required before representing this as an adopted capability.
