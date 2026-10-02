# 136 — Compare typed memory extraction without guessing quality

| Field | Value |
|---|---|
| Issue | [#136](https://github.com/LuigiFerronatto/TESSERA/issues/136) |
| Record status | `IN_PROGRESS` candidate mechanics / `BLOCKED` empirical decision |
| Capability type | Experimental runtime and benchmark preparation |
| Pull request | Dedicated draft candidate; not merged |
| Base commit | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Merge commit | Not merged |
| Decision | `PENDING`; no default adoption |
| Benchmark applicability | `REQUIRED` |
| Last audited | 2026-10-02 |

## In one sentence

A reviewer can now inspect draft labels and test one-call versus three-call
extraction mechanics, without pretending that stub outputs establish quality.

## What problem existed?

The legacy one-call prompt calls factual information immutable, even though a
concrete state or event can change. Its tolerant output parser does not enforce
a closed F/P/I schema. The issue requires human-reviewed atomic-unit labels
before provider comparisons; none were supplied in the issue or this checkout.

## How did TESSERA behave before?

The existing optional assisted decomposer makes one call and accepts supported
JSON wrappers. Provider errors fall back to the deterministic heuristic delivered
by #135 (PR #216, canonical merge `c324ac2f46d48f7b49769b2fea9df0a2a93b42de`).
Automatic extraction is explicit and writes pass through normal admission.

## What changed or is being tested?

**TARGET — NOT YET ON MAIN:** an explicitly imported candidate module exposes
D0 (unchanged heuristic), D1 (strict corrected one-pass F/P/I) and D2 (strict,
independent type-conditioned passes). The runtime prompt/default/CLI/MCP are
unchanged, including the known legacy wording defect, to isolate the experiment.
Corrected `fpi-v1` candidates recognize mutable facts, preference rationale and
supported user-specific transferable principles.

## How does it work now?

**TARGET — NOT YET ON MAIN:** The draft eight-case packet proposes units and acceptable types but records no
human approval. Provider capture and quality scoring fail closed on that draft.
Capture/replay retains exact input and prompt identities; metric scoring requires
separately reviewed, capture-bound output adjudication. No provider adapter,
credential resolution, model download or network CLI is introduced.

## Concrete example

If a user ordered vegetarian soup once, the candidate prompt asks for the concrete
choice event and rejects inferring a permanent vegetarian identity. Whether a
real provider obeys is **unmeasured**. Tests prove that a D2 preference pass
returning a factual item is rejected and the entire result falls back to D0,
with two attempted calls reported; no partial assisted memories are written.

## How was it validated?

- Candidate contract, strict-schema, provider-call, full-fallback, stable-dedup,
  default-preservation and all-three-types write-admission tests
- Draft-label rejection before a callback, hash-bound capture/replay, label
  non-leakage, metric arithmetic, telemetry validation and repeat comparison tests
- [Research packet and reproducible commands](../../benchmarks/typed_decomposition/README.md)
- Full local suite, built-artifact checks and retrieval sanity are recorded in
  the draft PR against its actual published head; synthetic mechanics checks are
  distinct from the blocked semantic/provider benchmark

## What improved?

The experiment now has executable, opt-in comparison mechanics and an actionable
annotation packet. Assertions cover closed schema, pass separation, fallback
truthfulness and existing write admission. No quality gain is claimed.

## What remains unimplemented?

Real human-reviewed labels, preregistered thresholds, provider-backed D1/D2
captures, blind human adjudication, empirical cost/quality comparison, and the
Test Card's KEEP/ITERATE/DROP decision. Eight draft development episodes cannot
establish general quality. The legacy prompt remains unchanged pending that
explicit decision. Supporting-turn lineage (#137 / PR #297), episode boundaries,
query planning and new drawers are outside scope; no dependency on that PR exists.

## What is unlocked next?

A human can review/edit the supplied fixture now. Provider comparison is not
unlocked until reviewed labels are frozen and approved. No downstream issue is
marked ready or complete; no issue is closed by this candidate.

## Technical provenance

- [Issue #136](https://github.com/LuigiFerronatto/TESSERA/issues/136): open research Test Card
- [#135 record](135-decomposition-fallback.md): canonical deterministic fallback
- [#74 decision](74-core-vs-optional-llm-boundary.md): optional-provider boundary
- [PR #284](https://github.com/LuigiFerronatto/TESSERA/pull/284): separate documentation correction; no runtime-prompt claim
- `tessera/typed_decomposition.py`: candidate contract/mechanics
- `benchmarks/typed_decomposition/`: draft labels, protocol and evaluation harness

## Evolution

Existing baseline → explicit candidate mechanics and draft packet → human label
review → authorized provider runs and output adjudication → empirical decision.
No merge, canonical delivery or changed default is asserted by this record.
