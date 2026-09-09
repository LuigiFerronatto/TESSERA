# #120 — Reliable MCP startup and transport

| Field | Value |
|---|---|
| Issue | [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` / MCP transport |
| Pull request | Implementation PR linked from #120; exact head in PR evidence |
| Merge commit | Not merged |
| Decision | Pending exact-head validation and independent audit |
| Benchmark applicability | `SMOKE_ONLY`; retrieval remains unchanged |
| Last audited | 2026-09-09; starting main `a88600b491528cddb746bf909a303aefabf01e45` |

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

Local candidate: 542 passed, 5 skipped; 17 real protocol scenarios passed from
a clean installed MCP wheel. Sanity quality metrics are unchanged.

Evidence and final counts are recorded in [PR Evolution Audit](../PR_EVOLUTION_120.md).

## What improved?

Startup, errors and persistence ownership become explicit, while typed retrieval
stops dropping traceability information already produced by the Engine.

## What remains unimplemented?

HTTP hosting/authentication, cross-process Engine coordination, transactional
rollback of a multi-note write, hard termination of arbitrary Python provider
threads, and semantic API #171 remain unimplemented. This card does not implement
#167 Working Context, #169 compiler, #121 Skills, ranking or release publication.

## What is unlocked next?

After human merge and lifecycle reconciliation, #121 can be reassessed. #171 still
requires its own semantic prerequisites. #134 remains blocked only by #87.

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
-> #120 IN_PROGRESS, Queue 5, isolated branch from current main
-> exact-head validation/audit -> human merge -> lifecycle reconciliation
```
