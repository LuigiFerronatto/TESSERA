# MCP runtime contract 1.0

The validated #120 implementation (PR #229) exposes the existing TESSERA tools over **stdio**. The Python
Engine remains the source of retrieval, evidence and write admission. Semantic
agent-memory API #171 is separate. This candidate is not yet canonically merged.

## Start and configure

Install the wheel's `[mcp]` extra on Python 3.10 or later; the certified optional
artifact check runs on Python 3.12. The base library remains Python 3.9 compatible.
The adapter requires MCP Python SDK `>=1.30.0,<2.0.0`; version 1.30.0 is the tested
minimum for the structured-result and lifecycle integration.

```sh
python -m pip install './dist/tessera_agent_memory-0.0.3-py3-none-any.whl[mcp]'
tessera-mcp --project /absolute/project --request-timeout 60
# Or an explicit writable store (takes precedence over environment):
tessera-mcp --store /absolute/memories
```

`--project`, `--store` and `--global NAME` are mutually exclusive selectors passed
to the canonical #117 resolver. Its existing precedence remains: explicit path,
canonical/deprecated storage environment, project discovery, selected global
registration. Consequently, unset storage overrides when selecting project/global
configuration. With no selectors the historical runtime fallback remains
`./memories` when no environment/project configuration exists. Schema v2 retains
the writable store, selected read-only sources, independent index and stable store
identity. Explicit `ResolvedConfiguration` injection bypasses ambient discovery.

Importing `tessera.mcp_server` and creating a server do not resolve ambient
configuration, create directories, index files or construct a provider. Startup's
lifespan resolves/configures the Engine and builds its derived index before tools
can run. Startup may create the writable store/derived index; it does not rewrite
selected sources. `--help` has no store side effect. Stdio stdout contains only
protocol messages; logs belong on stderr. Fatal startup failures exit 2 with a
safe versioned `SERVER_FAILED` error on stderr, without an alternate store.
EOF shuts down the server.

Applications select an optional provider at construction, outside tool arguments:

```python
from tessera.config import ConfigurationResolver
from tessera.mcp_server import create_server

configuration = ConfigurationResolver(environ={}).resolve(project="/absolute/project")
server = create_server(configuration, provider=application_owned_callable,
                       request_timeout=60)
server.run()
```

The callable has signature `(system_prompt, user_prompt) -> str`. Alternatively,
`provider_options` supplies explicit keyword arguments to the existing
`resolve_llm_fn` compatibility bridge and must include `backend`; resolution is
lazy. No provider is inferred from credentials or probed at startup. Provider
secrets/options are never returned in health or exception messages. A provider is
trusted application code; Python execution is not sandboxed by this adapter.

## Negotiation, requests and results

The SDK handles MCP `initialize`, protocol negotiation, `notifications/initialized`,
`ping` and cancellation notifications. Server info reports `tessera` and the package
version, independently of the MCP protocol version and TESSERA envelope version.
The current protocol probe offers `2025-11-25`; unsupported offers receive the
SDK's supported version, which the client must accept or disconnect. Tools and
resources advertise no subscription/list-change support. No HTTP authentication,
subscriptions or roadmap semantic capability is implied.

`tools/list` advertises per-operation request schemas with a versioned `$id`,
`_meta["tessera/schema_version"] = "1.0"`, an output schema and conservative tool
annotations. Existing argument names/defaults remain; `top_n` is an integer from
1 to 100, typed store is `facts`, `preferences` or `insights`, and unknown arguments
are rejected rather than silently ignored. Provider/configuration selection is
server-owned, never accepted through a memory tool request.

Every tool result uses the following object in both `structuredContent` and JSON
text `content`. Clients migrating from the old text result must read `data`:

```json
{"schema_version":"1.0","operation":"query_memories","data":[],"error":null}
```

Success keeps the existing result inside `data`; both direct and typed retrieval
preserve every Engine field, ordering, ID, score and provenance without computing
new semantics. Failure has `data: null`, an error with stable `code` and safe
`message`, and MCP `isError: true`. Invalid/malformed JSON-RPC itself remains an SDK
protocol error. `memories://{id}` still returns raw Markdown; missing/changed
resources raise protocol errors with a versioned TESSERA object in error `data`.
`graph://index` and `server://health` contain versioned JSON envelopes.

Errors include `INVALID_ARGUMENT`, `UNKNOWN_TOOL`, `NOT_FOUND`, `SOURCE_CHANGED`,
`NOT_READY`, `PROVIDER_NOT_CONFIGURED`, `PROVIDER_FAILED`, `PROVIDER_BUSY`, `TIMEOUT`,
`WRITE_FAILED`, `STORAGE_ERROR` and `INTERNAL_ERROR`. Raw provider/storage exception strings are
not exposed. An error never contains a fabricated successful generated context.

## Concurrency, deadlines and cancellation

Each server owns one Engine and one serialized queue for graph reads/mutations.
Blocking Engine operations run in a worker thread so protocol ping/cancellation
can proceed. Coordination is per process; multiple writers in independent server
processes are not coordinated by this adapter.

- The request deadline covers queue waiting. Cancellation/deadline before a write
  starts prevents that commit. Once a synchronous write starts, it is drained
  under the lock and reports its completed outcome, even beyond the deadline.
  A client that cancels or disconnects during that commit must inspect persistence
  before retrying; cancellation is not rollback.
- Reads run under the same lock and discard overdue results after the synchronous
  read returns. They are cooperative, not a hard interruption of Python code.
- Assisted work runs on disposable inputs: decomposition prepares candidates;
  the pipeline uses an Engine snapshot. Its timeout/cancellation abandons the
  result, with no continuation that can later commit. One provider slot remains
  occupied until the underlying call actually exits; further assisted calls
  return `PROVIDER_BUSY`, while ordinary retrieval remains available.
- Decomposition persists only after all provider activity succeeded and the
  request reacquired the Engine lock within its deadline. Canonical typed writers
  and write gating remain responsible for admission. Python/CLI #135 fallback
  is unchanged; failed remote assistance does not persist fallback notes.
- Multi-note writes do not provide transactional rollback. A later gate/storage
  failure can leave earlier admitted notes; inspect the returned paths or index
  before retrying. Hard termination of arbitrary provider threads is not offered.

## Operations and validation

`get_server_health` and `server://health` report runtime state, selected canonical
configuration, package/envelope versions, provider-selection presence, deadline
and concurrency policy without a provider call. `run_doctor` retains that full
configuration unless its explicit storage override is provided. Doctor performs
its existing temporary write/read probes. Quickstart remains a dry run unless
`apply=true`; write/rebuild/apply operations are serialized.

`scripts/clean_room/check_mcp.py` is a standalone JSON-RPC subprocess client. CI
installs the built wheel's MCP extra into a fresh venv, changes outside the
checkout, removes `PYTHONPATH` and runs the protocol experiment there. It records
the imported package path, interpreter, SDK version, source hashes and checks.
The base artifact proof remains separate and requires MCP/provider dependencies
to be absent.

Protocol mechanics follow the official [MCP lifecycle specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
and [cancellation specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation).
The adapter uses the [official Python SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0),
not the separately evolving v2 interface.
