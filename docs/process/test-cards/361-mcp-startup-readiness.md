# 361 — The MCP server should connect instantly, then finish loading memory

| Field | Value |
|---|---|
| Issue | [#361](https://github.com/LuigiFerronatto/TESSERA/issues/361) |
| Record status | `IMPLEMENTED` (architecture decision only) |
| Capability type | `architecture decision` |
| Pull request | [#369](https://github.com/LuigiFerronatto/TESSERA/pull/369) (ADR 0008, Accepted) |
| Head commit | `5e004f1e26a305ad09d5c3eda86a275fde7eefef` (final candidate) |
| Merge commit | `6228ecb4f88deff1e1c445b10c29250108a8ccb6` |
| Decision | `KEEP` (ADR accepted; runtime not implemented) |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-10-12 |

## In one sentence

Agent tools should be able to connect to the TESSERA MCP server immediately,
while the server loads the memory index in the background and reports how far
it has got.

## What problem existed?

The server builds the whole index before it answers the first protocol
message. On a real 18 MB corpus that took 43 seconds on a cold start, longer
than several agent tools wait, so they reported the server as disconnected even
though nothing was wrong. When building failed, the process exited with a
generic message and the agent could not ask why.

## How did TESSERA behave before?

```text
tessera-mcp --project .   (18 MB corpus)
→ first protocol answer after 43 s
→ gemini mcp list / opencode mcp list: disconnected with default timeouts
```

## What changed or is being tested?

This stage records an architecture decision only. ADR 0008 adopts answering
the protocol handshake right away, building the index in a background worker,
exposing readiness and progress through the health tool, letting tool calls
wait for readiness within their timeout and then answer `NOT_READY`
(owner-confirmed), keeping
the process alive when indexing fails, and a sub-second budget for the
handshake. No runtime code changes in this stage.

## How does it work now?

The ADR is accepted and merged on `main`; its runtime target is not implemented. Until #362 merges, startup still blocks on the
index build.

## Concrete example

```text
target: initialize answered in < 1 s
        get_server_health → {"state": "indexing", "index_progress": {"processed": 1200, "total": 2500}}
        query_memories    → waits, then answers once state is "ready"
```

## How was it validated?

The baseline observations above were recorded in issue #361 on `main`
`7e7b20e`; they are historical evidence, not a new runtime measurement.
The [owner decision](https://github.com/LuigiFerronatto/TESSERA/issues/361#issuecomment-6118667212)
records `KEEP`. PR #369's merge and final candidate were verified against
GitHub and the merge's second parent; the candidate and merge trees match.

[Final-candidate CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38217397451)
passed.
[Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38217397400)
passed with documentation-only `NOT_APPLICABLE` applicability. This record
uses `IMPLEMENTED`, not a claim that the proposed runtime or its performance
has been validated. No new human approval is inferred from merge or CI.

## What improved?

Nothing at runtime yet. The repository gains a binding startup and readiness
contract for #362.

## What remains unimplemented?

All runtime behaviour remains unimplemented and is owned by #362, including the
`docs/reference/mcp-runtime.md` update. Indexing speed itself is not addressed here.

## What is unlocked next?

The ADR prerequisite for #362 is satisfied. #362 still must coordinate with
#355/#356 and prove the latency and concurrency gates. #190 cannot rely on
default-timeout startup until that runtime delivery is validated.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#361](https://github.com/LuigiFerronatto/TESSERA/issues/361) |
| Pull request | [#369](https://github.com/LuigiFerronatto/TESSERA/pull/369) |
| Merge commit | `6228ecb4f88deff1e1c445b10c29250108a8ccb6` |
| Evidence/Learnings/Decision | Issue #361 Evidence section |
| Benchmark record | Not applicable (architecture decision) |
| PR Evolution Audit | [Verified delivery](../../history/pr-evolution/361.md) |

## Evolution

```text
#120 startup contract: build the index before tools can run
→ ADR 0008 proposed: handshake first, background indexing, explicit readiness
→ current state: Accepted and merged on main, runtime unchanged
→ next implementation: #362 implementation
```
