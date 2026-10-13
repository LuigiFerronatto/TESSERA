# 361 — The MCP server should connect instantly, then finish loading memory

| Field | Value |
|---|---|
| Issue | [#361](https://github.com/LuigiFerronatto/TESSERA/issues/361) |
| Record status | `IN_PROGRESS` |
| Capability type | `architecture decision` |
| Pull request | [#369](https://github.com/LuigiFerronatto/TESSERA/pull/369) (ADR 0008, Accepted) |
| Head commit | See the pull request |
| Merge commit | Not merged |
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

This stage records an architecture decision only. ADR 0008 proposes answering
the protocol handshake right away, building the index in a background worker,
exposing readiness and progress through the health tool, letting tool calls
wait for readiness within their timeout and then answer `NOT_READY`
(owner-confirmed), keeping
the process alive when indexing fails, and a sub-second budget for the
handshake. No runtime code changes in this stage.

## How does it work now?

TARGET — NOT YET ON MAIN. Until #362 merges, startup still blocks on the
index build.

## Concrete example

```text
target: initialize answered in < 1 s
        get_server_health → {"state": "indexing", "index_progress": {"processed": 1200, "total": 2500}}
        query_memories    → waits, then answers once state is "ready"
```

## How was it validated?

The current latency was measured on canonical `main` 7e7b20e with the
`initialize` probe and corpora recorded in
[#361](https://github.com/LuigiFerronatto/TESSERA/issues/361). The decision is
validated by review; documentation consistency is covered by the existing docs
test suite.

## What improved?

Nothing at runtime yet. The repository gains a binding startup and readiness
contract for #362.

## What remains unimplemented?

All runtime behaviour remains unimplemented and is owned by #362, including the
`docs/reference/mcp-runtime.md` update. Indexing speed itself is not addressed here.

## What is unlocked next?

Once this ADR merges, #362 is unblocked and #190 can rely on default client
timeouts.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#361](https://github.com/LuigiFerronatto/TESSERA/issues/361) |
| Pull request | [#369](https://github.com/LuigiFerronatto/TESSERA/pull/369) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Issue #361 Evidence section |
| Benchmark record | Not applicable (architecture decision) |
| PR Evolution Audit | Pull request body |

## Evolution

```text
#120 startup contract: build the index before tools can run
→ ADR 0008 proposed: handshake first, background indexing, explicit readiness
→ current state: Accepted in review, runtime unchanged
→ next validated dependency: #362 implementation
```
