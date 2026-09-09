# #120 — Reliable MCP startup and transport

| Field | Value |
|---|---|
| Issue | [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) |
| Record status | `VALIDATED` |
| Capability type | `runtime` / MCP transport |
| Pull request | [#229](https://github.com/LuigiFerronatto/TESSERA/pull/229), merged 2026-09-09 |
| Final candidate | `09dff4d0fdeda0e761e3f9a4d6cb7d66a3b0f211` |
| Merge commit | `b4ead4d7407b8caa2571e1e366616a468f2ef74f` |
| Decision | `KEEP`; independent exact-head audit and green canonical CI/ledger |
| Benchmark applicability | `SMOKE_ONLY`; retrieval remains unchanged |
| Last audited | 2026-09-09; canonical merge `b4ead4d7407b8caa2571e1e366616a468f2ef74f` |

## In one sentence

An external MCP client can start the configured memory server, retain all Engine
evidence and distinguish a completed operation from a failed assisted request.

## What problem existed?

Importing the server created a store and built an index. Typed retrieval removed
evidence fields. The adapter did not define request deadlines, cancellation,
concurrent Engine access or versioned errors, and its packaging check only imported
FastMCP rather than exchanging protocol messages.

## How did TESSERA behave before?

The nine tools and two resources called synchronous functions against one eager
module-global Engine. Direct query already preserved #68 evidence; `query_store`
projected only five fields. Doctor reconstructed configuration from the writable
store path and lost the configured read-only sources/index. Optional backend
probing had already been removed by #95: the re-audit does not re-claim that fix.

## What changed or is being tested?

A lazy server factory owns an explicit canonical configuration and provider
selection. A lifespan starts the Engine; the stdio adapter validates requests,
versions responses/errors, serializes Engine access and isolates assisted work
before any commit. Existing tools remain; one operational health tool/resource is
added. `query_store` uses the same lossless projection as direct retrieval.

## How does it work now?

Requests carry the existing arguments and receive contract `1.0` in text and
structured content. `data` contains the existing result. Reads and assisted work
have deadlines; queued writes can be cancelled. A started synchronous write
finishes under the Engine lock. Cancellation is not rollback. An abandoned
provider has no continuation that can write notes. Python/CLI decomposition keeps
#135's deterministic fallback; remote assisted failure returns an error before
any fallback persistence.

## Concrete example

Start `tessera-mcp --project /absolute/project`. Initialize the MCP session and call
`query_store` with `{"query":"SQLite", "store":"facts"}`. The response's `data`
retains the same ordered IDs, scores, evidence and provenance as the Engine.
Calling an assisted tool without a selected provider returns
`PROVIDER_NOT_CONFIGURED`, with no memory write.

## How was it validated?

Required acceptance gates, fixed before final validation:

- Import/factory: no store/index mutation, provider construction or network call.
- Real subprocess stdio: initialize/version/capabilities, schemas, every existing
  tool/resource, malformed arguments, unknown targets and continued healthy use.
- Canonical v2 configuration: same selected corpus, IDs/order/evidence; doctor
  retains sources/index; source hashes remain unchanged.
- Provider failure/invalid output/timeout/cancellation: structured failures and no
  late writes; deterministic retrieval remains available.
- Concurrency: serialized Engine mutation; queued cancellation prevents writes;
  started commits finish and never report a false pre-commit timeout.
- Build sdist then wheel; install `[mcp]` outside the checkout and run the same real
  protocol experiment against installed `site-packages`.
- Base Python 3.9/3.12 regression suite and unchanged deterministic sanity metrics.

Local candidate: 542 passed, 5 skipped; 18 real protocol scenarios passed from
a clean installed MCP wheel. Sanity quality metrics are unchanged.

Evidence and final counts are recorded in [PR Evolution Audit](../PR_EVOLUTION_120.md).

The candidate and canonical merge have the same tree and count as one runtime
delivery. [Canonical CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34389760629)
and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/34389760516)
passed after merge. Downloaded installed-artifact/protocol reports are summarized
in [canonical evidence](../evidence/120-mcp/canonical-merge.json).

## What improved?

Startup, errors and persistence ownership become explicit, while typed retrieval
stops dropping traceability information already produced by the Engine.

## What remains unimplemented?

HTTP hosting/authentication, cross-process Engine coordination, transactional
rollback of a multi-note write, hard termination of arbitrary Python provider
threads, and semantic API #171 remain unimplemented. This card does not implement
#167 Working Context, #169 compiler, #121 Skills, ranking or release publication.

## What is unlocked next?

#121 is READY with all its declared dependencies satisfied. It remains LATER /
Queue 43, unselected; implementation starts only from fresh main after this
lifecycle reconciliation merges. #171's MCP prerequisite is satisfied, but its
semantic prerequisites remain unresolved. #134 remains blocked only by #87.

## Technical provenance

| Item | Evidence |
|---|---|
| Canonical prerequisite | #118/#225 `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d` |
| Lifecycle gate | #227/#228 `a88600b491528cddb746bf909a303aefabf01e45`, green main CI/ledger |
| Runtime | `tessera/mcp_server.py`, `mcp_runtime.py`, `mcp_transport.py` |
| Transport contract | [MCP runtime](../MCP_RUNTIME.md) |
| Protocol experiment | `scripts/clean_room/check_mcp.py` |
| Benchmark | `benchmarks/sanity/ci_eval.py`; `SMOKE_ONLY` |

## Evolution

```text
#116 packaging + #117/#153 configuration + #118 clean installed onboarding
-> #227/#228 lifecycle merged, gate satisfied
-> #120 candidate 09dff4d... validated/audited KEEP
-> #229 human merge b4ead4d... -> canonical CI/ledger passed
-> #120 VALIDATED / KEEP, historical Queue 5 (one runtime delivery)
-> #121 READY / LATER / Queue 43; no downstream implementation selected
```
