# ADR 0008: MCP handshake is independent of index readiness

- Status: Accepted (owner decision recorded in PR #369 on 2026-10-12)
- Date: 2026-10-12
- Issue: [#361](https://github.com/LuigiFerronatto/TESSERA/issues/361)
- Amends: the startup contract delivered by #120 / PR #229 and documented in
  [`docs/MCP_RUNTIME.md`](../MCP_RUNTIME.md)

## Context

The MCP runtime contract from #120 says the lifespan "resolves/configures the
Engine and builds its derived index before tools can run", and that "fatal
startup failures exit 2 with a safe versioned `SERVER_FAILED` error". On
canonical `main` (7e7b20e) `TesseraMCP`'s lifespan awaits `runtime.start()`,
which runs `get_engine()` → `build_index()` in a worker thread. The stdio
session only answers `initialize` after that returns.

MCP clients put a short timeout on the handshake. Measured `initialize`
latency with `tessera-mcp --project .` (Python 3.12, local disk):

| Corpus | after `tessera index` | after touching one note |
|---|---:|---:|
| 0 notes (synthetic) | 3.85 s | 3.32 s |
| 500 notes (synthetic) | 5.28 s | 4.94 s |
| 2,500 notes (synthetic) | 7.43 s | 6.67 s |
| ~2,500 real notes, 18 MB, multi-root | 43.06 s cold | 13.19 s second start |

A profile of the real-corpus build (18.8 s) attributes 11.2 s to
`_iter_source_files` and 4.4 s to `_load_index_if_fresh` before it decides to
rebuild. With default timeouts, Gemini CLI 0.61.0 (`gemini mcp list`) and
OpenCode (`opencode mcp list`) report the server as disconnected/failed; both
connect after the per-server timeout is raised to 120 s. Corpus size therefore
decides whether an otherwise healthy server can be used at all.

Two further consequences follow from the blocking design. A source-level
failure, such as an explicit-ID collision (#350), kills the process with a
generic `SERVER_FAILED`, so the agent cannot even call `get_server_health` to
learn why (#356). And faster indexing cannot fix the problem by itself, because
any fixed handshake budget is eventually exceeded by a larger corpus.

## Decision

### 1. The handshake never waits for the index

`initialize`, `ping`, `tools/list`, `prompts/list`, `resources/list` and the
health tool/resource are served as soon as configuration is resolved.
Configuration-level failures that are cheap and deterministic — an invalid or
unreadable config, a store path that is not a directory, an unusable index
path — still fail startup immediately with exit 2, exactly as today, because
no useful server can exist without them.

### 2. Index readiness is background work

After the handshake, one background worker loads or builds the index. It uses
the existing single-engine concurrency rule: the worker holds the engine slot
while it builds, and a refreshed engine replaces the previous one atomically.

### 3. Readiness is an explicit state

The runtime `state` field already exposed by health gains these values:

```text
created → indexing → ready
                   ↘ failed        (no usable index; error code recorded)
ready → refreshing → ready         (rebuild requested; previous engine keeps serving)
ready|refreshing|failed → closed
```

Health adds `index_progress` (`{"processed": int, "total": int | null}`),
`last_index_error` (stable code and safe message from #356, or `null`) and
`index_diagnostics_count` (for example collisions under ADR 0006). Health is
always answerable, in every state.

### 4. Tool calls before `ready`

Decision (option A): read and write tools called while `state` is `created`
or `indexing` **wait for readiness up to the request timeout**, then fail with
the existing `NOT_READY` code, whose message and data now carry the state and
progress. In `failed`, they fail immediately with `NOT_READY` plus
`last_index_error`. During `refreshing`, reads are served by the previous
engine and writes queue behind the refresh.

Rationale: agents usually recall right after connecting; a bounded wait turns
the common case into one successful call instead of an error-and-retry loop,
while the timeout keeps the call bounded. Option B (fail immediately with
`NOT_READY`) is simpler but pushes polling logic into every consuming agent.

The owner chose option A.

### 5. Source-level failures do not kill the process

A failure while building the index moves the runtime to `failed` (or, for
admitted-with-diagnostics outcomes under ADR 0006, to `ready` with
diagnostics). The process stays alive so health can report the mapped error,
and `rebuild_index` can retry after the user fixes the corpus. This replaces
#120's "source-level failures still propagate and fail startup truthfully" for
source-level failures only; truthfulness is preserved through health and tool
errors instead of exit status.

### 6. Latency budget

`initialize` must answer in under 1 s at p95 independently of corpus size.
CI measures it with an `initialize` probe against a synthetic 2,500-note
corpus and asserts the budget; the measurement method is the probe recorded
in #361.

## Alternatives considered

1. **Keep blocking startup and make indexing faster.** Rejected as the
   primary fix: any fixed client timeout is eventually exceeded by a larger
   corpus, and failures stay invisible. Faster indexing remains worthwhile on
   its own.
2. **Lazy build on the first tool call.** Avoids a worker, but the first
   recall pays the full build latency inside its request timeout and may time
   out; background work after the handshake starts that build earlier.
3. **Ask users to raise client timeouts.** Rejected: it is per-client,
   undiscoverable, and some clients cannot configure it.

## Consequences

- Connection success no longer depends on corpus size; harness setup (#190)
  can rely on default client timeouts.
- `docs/MCP_RUNTIME.md` changes its startup paragraph in the implementation
  PR (#362): the derived index is built after the handshake, and only
  configuration-level failures exit at startup.
- Tool callers may observe `NOT_READY` with progress instead of a server that
  never connected.
- Concurrency between the worker, `write_memory` and `rebuild_index` needs
  dedicated tests (#362).

## Boundaries

This ADR does not change tool schemas other than health and the `NOT_READY`
payload, does not add file watching or multi-process index sharing, and does
not optimise indexing itself. It depends on ADR 0006 for how collision
outcomes are reported and on #356 for error codes. Implementation is owned by
#362.
