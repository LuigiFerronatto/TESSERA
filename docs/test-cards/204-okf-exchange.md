# 204 — Test portable knowledge without replacing canonical memory

| Field | Value |
|---|---|
| Issue | [#204](https://github.com/LuigiFerronatto/TESSERA/issues/204) |
| Record status | `IN_PROGRESS` |
| Capability type | experimental exchange adapter and synthetic evaluation |
| Pull request | Draft candidate; linked from issue #204 |
| Merge commit | Not merged |
| Decision | `ITERATE` |
| Benchmark applicability | `SMOKE_ONLY` plus ROUND_TRIP |
| Last audited | 2026-10-02 |

## In one sentence

The candidate can inspect OKF knowledge and produce lossless supported-profile
exchange plans while keeping TESSERA's own canonical metadata authoritative.

## What problem existed?

Native Markdown had no isolated OKF exchange contract, so importing external
metadata risked confusing freshness with truth or losing typed relationships.

## How did TESSERA behave before?

At baseline 20814a47ec0f72d7bea0639e0b057df1ecf5cded, native ingestion worked,
but no pinned OKF adapter or reproducible OKF round-trip experiment existed.

## What changed or is being tested?

Read-only import/export plans, explicit source-copy/export transactions,
versioned JSON and human Markdown/Obsidian/CSV views with filters, a
namespaced canonical extension and a frozen
11-object synthetic experiment. No native Engine or ranking code changes.

## How does it work now?

**CANDIDATE — NOT YET ON main.** The opt-in Python module checks a bounded local
bundle and returns JSON candidates. An explicit destination and previously
reviewed plan hash can publish a new standalone source directory through the
existing security gate. It never registers/adopts those sources or executes
attestation code. Existing source formats continue on their unchanged path.

## Concrete example

`python -m tessera.okf plan tests/fixtures/okf_v02 --namespace synthetic-project`
returns ten canonical candidates. A stale_after date remains a freshness hint;
it does not become the time a fact stops being true.

## How was it validated?

The [A0–A4 experiment](../../benchmarks/okf_roundtrip/result.json) compares
10 external and one native object's semantic dictionaries, hashes, typed
relations and Engine evidence smoke. The separately frozen upstream concept
validator checks input/output concepts. Focused tests cover paths, collisions,
YAML ambiguity, untouched input bytes, namespace drift, stale extensions and
explicit no execution/network behavior. Exact commands are in the PR and
[adapter documentation](../OKF_INTEROPERABILITY.md).

## What improved?

The experiment supplies a measurable exchange contract and diagnoses mapping
ambiguity without weakening existing storage or silently inventing timestamps.

## What remains unimplemented?

Future evidence-aware admission (#19), accepted encryption/exposure integration
policies (#256/#257), user-corpus evaluation, complete independent conformance audit and
canonical merge remain open. Synthetic passes do not satisfy those gates.

## What is unlocked next?

Review the namespaced extension, identity policy and tested source-copy
transactions. Evidence-aware admission/exposure remain separate contracts;
ordinary explicit source conversion does not require inventing them.

## Technical provenance

The [spec is pinned](https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/ad30107c31c06aec8a7d5636e0d1058118604e6f/SPEC.md)
to a commit because v0.2 changed timestamp semantics without a version bump.
The [technical contract](../OKF_INTEROPERABILITY.md) lists exact mappings,
limits, preserved fields and remaining acceptance evidence.

## Evolution

Baseline main: 20814a47ec0f72d7bea0639e0b057df1ecf5cded. This is an isolated
new candidate, not a replacement for native ingestion or a claim of merged
capability. After any eventual authorized merge, record the canonical commit,
re-run gates and reconcile issue/roadmap status before promotion.
