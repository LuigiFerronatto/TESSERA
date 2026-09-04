# PR Evolution Audit — Issue #135 decomposition fallback integrity

## Candidate lifecycle state

- **Issue:** [#135](https://github.com/LuigiFerronatto/TESSERA/issues/135)
- **Decision:** `PENDING`
- **Lifecycle status:** `PLANNED`
- **Implementation PR:** pending publication
- **Candidate branch:** `fix/135-decomposition-fallback`
- **Starting canonical main:** `f57727b11977e9ba9619bd2202f5897fb20c334b`
- **Final candidate SHA:** pending publication
- **Canonical merge SHA:** not merged
- **Benchmark applicability:** `SMOKE_ONLY`

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

## Downstream routing

Before canonical merge, no downstream card is considered unblocked. After
merge and lifecycle reconciliation, reassess only #136 and #137 because they
explicitly declare #135 as a blocker. Do not change the canonical Queue or
promote all QUMem cards.
