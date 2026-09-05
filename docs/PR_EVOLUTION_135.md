# PR Evolution Audit — Issue #135 decomposition fallback integrity

## Candidate lifecycle state

- **Issue:** [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135)
- **Decision:** `KEEP`
- **Lifecycle status:** `VALIDATED`
- **Implementation PR:** [#216](https://github.com/LuigiFerronatto/TESSERA/pull/216)
- **Candidate branch:** `fix/135-decomposition-fallback`
- **Starting canonical main:** `f57727b11977e9ba9619bd2202f5897fb20c334b`
- **Validated implementation candidate:** `555a8354343bb8458c6f9650dd349eb28374d2f6`
- **Final candidate SHA:** `2bc281760dedbe71cfeca5b8a16296de29260980`
- **Canonical merge SHA:** `c324ac2f46d48f7b49769b2fea9df0a2a93b42de`
- **Benchmark applicability:** `SMOKE_ONLY`

## Post-merge lifecycle reconciliation

Benchmark applicability: NOT_APPLICABLE

This reconciliation changes documentation and portfolio routing only; it does
not change runtime, evaluation, retrieval, or decomposition behavior.
Project #9 was synchronized from the authoritative issue routing and portfolio
manifest; the verification dry-run reported `0` remaining changes.

The branch started only after Issue #155 merged as canonical commit
`4c112195f1572bf352d1cc6a1042c69711381da8` and its lifecycle reconciliation
merged as `f57727b11977e9ba9619bd2202f5897fb20c334b`. Issue #135 was then the next
canonical execution task (Queue #2).

## Audited root cause

`_decompose_via_llm()` used `None` for provider/parse failure, while a valid
empty response became `[]`. `decompose_episode()` returned the LLM result when
non-`None`, but returned a new empty list when it was `None`. The documented
`_decompose_via_heuristic()` still existed yet had no public call edge.

The canonical-main reproduction was:

```text
provider RuntimeError -> []
malformed JSON        -> []
direct heuristic      -> three deterministic candidates for the fixture episode
```

## Candidate contract

```text
episode
  -> assisted attempt
       valid list, including [] -> assisted result
       expected provider error  ┐
       parse failure            ├-> deterministic fallback result
       invalid root/schema      ┘
  -> candidates only
  -> canonical typed writers
  -> WriteGatingEngine
  -> durable Markdown memory
```

The compatibility methods retain their list outputs. A diagnostic result
records `assisted` or `deterministic_fallback` and a bounded fallback reason.
The provider boundary catches the RuntimeError-based current adapter taxonomy
plus timeout/connection failures; unrelated `AssertionError` and `TypeError`
propagate in focused tests.

## Behavioral delta

| Case | Audited main | Candidate |
|---|---|---|
| Valid non-empty supported payload | assisted memories | unchanged |
| Valid `[]` | `[]` | unchanged; fallback call count zero |
| Provider invocation failure | `[]` | deterministic heuristic candidates |
| Malformed/unparseable output | `[]` | deterministic heuristic candidates |
| Prose without structured JSON | `[]` | deterministic heuristic candidates |
| Wrong root or invalid item schema | `[]` or partial filtering | deterministic heuristic candidates |
| Durable write | canonical gate | unchanged |

The only additional explicit schema correction is that a mixed/invalid list is
treated as one invalid provider result instead of silently dropping invalid
items and accepting a partial extraction.

## Invariants and scope

- The fallback is local, deterministic, offline and provider-independent.
- It adds no retry, network call, model, embedding or graph retrieval.
- `decompose_episode()` remains pure and writes nothing.
- Assisted and fallback candidates use identical typed writers and the
  canonical write gate.
- Exactly three semantic drawers remain: facts, preferences and insights.
- #136 semantic fidelity/passes/ablation, #137 lineage, #138 episode
  construction and #145 tracking are excluded.
- Engine, Hook, CLI and MCP delegate to `tessera.decomposer`; no transport owns
  duplicate fallback logic.

## Evaluation plan

Benchmark applicability is `SMOKE_ONLY`: retrieval, ranking, evidence and
drawer semantics are unchanged. Required evidence is the focused decomposition
suite, relevant Engine/CLI/MCP and gate tests, the complete suite on Python 3.9
and 3.12, installed-artifact smoke, deterministic fallback equality,
deterministic retrieval sanity, compileall, diff checks, exact-head CI and an
exact-head Maintainer Audit. LongMemEval is not required for this contract
repair.

At implementation candidate `555a8354343bb8458c6f9650dd349eb28374d2f6`,
the focused decomposition/memory/write-gate suite passed `113` tests. Clean
full suites passed on Python 3.9 and 3.12 with `523 passed, 5 skipped` and 14
expected warnings on each version. Publication metadata is the only subsequent
repository change before the exact final-head rerun.

## Downstream routing

The canonical merge and this lifecycle reconciliation satisfy the declared
#135 blocker for #136 (also depends on #74, already `VALIDATED`) and #137
(depends only on #135). All declared hard blockers are therefore satisfied,
so both issues become `READY`; neither moves ahead of Queue #3 (#16). The
historical Queue #2 position remains attached to #135, and no other QUMem card
is promoted by this reconciliation.
