# Experimental privacy-minimized operational ledger (#259)

This is an opt-in Python mechanics API. Ordinary Engine, CLI and MCP calls do
not create events, load this module, discover a ledger, or change configuration.
It does not provide sessions commands, HTTP, lifecycle adapters, implicit user
monitoring, semantic retrieval, ranking feedback, or access authorization.
Full session integration remains gated by validated #196/#177 lifecycle identity.
No unmerged #171, #177 or #196 interfaces are imported or emulated.

## Explicit ownership and event contract

Import `InteractionLedger`, `InteractionEvent` and `LedgerPolicy` from
`tessera.interaction_ledger`. The default policy has `enabled=False` and every
operation is a no-I/O empty view/no-op, except explicit deletion which reports
`ledger_disabled`. There is no environment variable or product setting.
Enabling this experimental API is an explicit application decision per project.

A trusted local caller supplies a dedicated ledger directory, opaque canonical
UUID strings for project, runtime session, run and event, and a policy. Identity
mapping is external; do not put names, paths or user information in identifiers.
Caller-supplied UUIDs are labels, not verified #196/#177 lifecycle identity or
proof of authorization. This is a same-user local API, not a security boundary
against an attacker who can read or replace filesystem data. A service must
separately authenticate and authorize callers before exposing any ledger view.

The schema accepts only fixed fields:

- `schema_version=1`; caller-supplied `occurred_at_ms` (UTC epoch milliseconds),
  finite nonnegative `duration_ms`, and explicit identity
- Runtime enum: `python`, `cli`, `mcp`; no HTTP/hook adapter is claimed
- Operation enum: `search`, `evidence`, `remember`, `inspect`, `index`, `doctor`
  These are reporting categories for existing capabilities, not new tool names
- Fixed `status`, optional `verdict` and diagnostic `cause` enums; bounded counts,
  optional query length/top-k and query fingerprint
- Up to 32 deduplicated evidence IDs in the existing `ev_<16 hex>` contract;
  memory IDs are omitted because they may contain source paths or private names
- `remember` can declare `written`, `rejected` or `no_write`; these are caller
  observations and do not perform a write or run the write gate

There is no field for raw query, transcript, payload, result body, error message,
path, model/provider credential or arbitrary metadata. Unknown fields and invalid
values fail closed. Validation errors contain bounded codes, never input values.
Raw-content logging is unsupported, even with opt-in. A future raw-content mode
would require its own protection, explicit notice and design review.

`fingerprint_query(query, project_id=..., key=...)` returns a project-separated
HMAC-SHA256. The caller owns a random 32–128 byte key, distinct from provider
credentials; this module neither creates, saves nor exports it. The query is
transient in this helper and is never passed into an event automatically.
Fingerprinting is optional, pseudonymous and linkable, not anonymization. Key
rotation changes repeated-query statistics. Fixed-format fields cannot prove
that a malicious caller has not deliberately encoded sensitive information.

## Minimal synthetic example

```python
from tempfile import TemporaryDirectory
from uuid import UUID
from tessera.interaction_ledger import InteractionEvent, InteractionLedger, LedgerPolicy

with TemporaryDirectory() as directory:
    project = str(UUID(int=1))
    ledger = InteractionLedger(directory, project_id=project,
                               policy=LedgerPolicy(enabled=True, max_events=100))
    event = InteractionEvent(
        event_id=str(UUID(int=10)), project_id=project, runtime="python",
        runtime_session_id=str(UUID(int=2)), tessera_run_id=str(UUID(int=3)),
        operation="search", occurred_at_ms=1700000000000,
        duration_ms=12, status="success", result_count=0,
        verdict="none", cause="unmatched",
    )
    assert ledger.append(event, now_ms=1700000000000) == "recorded"
    assert ledger.append(event, now_ms=1700000000000) == "duplicate"
    summary = ledger.analytics(now_ms=1700000000000)
    assert summary["zero_result_rate"] == 1.0
```

Use randomly generated identities in applications; deterministic IDs and the
clock override above are for repeatable tests. Cause classification is supplied
by callers, never inferred from an empty result. The enum distinguishes empty
corpus, denied scope, missing/stale index, unmatched query, unavailable provider
or capability, timeout/cancellation, configuration mismatch, server/transport
failure, malformed request, rejected write and unknown cause. This does not yet
validate end-to-end classification by runtime adapters.

## Storage, concurrency and retention

Only `<explicit directory>/interactions-v1.sqlite3` is used. Keep this directory
outside configured source roots and the canonical memory store. It is operational
derived state, not another semantic drawer. No ledger-to-index integration exists.
The module never opens source files, durable memories or evidence stores.
Only a new ledger may be initialized; unknown existing files/databases, linked
database/SQLite-sidecar paths and nonregular files are rejected. Directory ancestry is checked as well. These are cooperative-process
preflight checks, not protection against a filesystem owner racing path swaps.
Ownership metadata reads are limited to two 256-character values before exact
project/policy comparison. The fixed 100-byte database header is checked without SQLite first. WAL-mode
headers and existing `-wal`/`-shm` sidecars are unsupported and rejected before
connecting, because read-only SQLite access can still alter shared memory.
Ownership is then probed using a read-only connection before opening for writes,
so an unowned hot rollback journal cannot silently recover and mutate another
database. SQLite locking is retained; no connection uses `immutable=1`. A store that needs rollback-journal recovery
fails closed; separately authorized SQLite recovery is outside this API. A project/policy marker is checked before write
transactions, and an existing ledger cannot be reopened as another project or
silently assigned different retention limits. Use a separately authorized
migration or a new ledger if policy changes are required.

Defaults are 1,000 events and seven days; hard limits are 10,000 events, one year,
4,096 bytes per event, and one day for recorded duration. Individual inspection
pages are bounded to 1,000 events, and full exports to the 10,000-event ceiling.
Metadata and schema are fixed, with no user-controlled blob column.

Each enabled append uses one SQLite `BEGIN IMMEDIATE` transaction. Initialization
publishes a fully initialized database atomically without overwriting existing
files. Concurrent processes/threads serialize writes; the busy wait is 250 ms.
A storage failure returns `LedgerError('ledger_storage_unavailable')` without
logging it or retrying indefinitely. This is a lock-wait bound, not a hard wall
clock/I/O latency guarantee. The caller chooses an explicit fail-open/fail-closed
policy before wiring this into a real runtime; no integration exists today.

The event ID is an idempotency key while the row is retained. Reusing it with a
different normalized payload fails; ID order breaks timestamp ties. Appends
atomically prune events at or before the age cutoff and oldest count overflow.
Events older than the cutoff are rejected without opening storage; future-dated
events fail. A late event outside the count window is explicitly reported as
`outside_count_window`. After retention or deletion, its ID can be accepted again.
There is no unbounded tombstone set or exactly-once promise beyond retention.

Read-only views hide expired events but do not delete them. With no appends or
explicit cleanup, expired rows remain physically present. Count/age bounds apply
to logical rows, not secure erasure or a fixed filesystem-byte quota: SQLite free
pages, rollback journals, backups and filesystem snapshots have their own life.
No background timer, daemon, network sender or global store is introduced.

## Read-only inspection, exports and explicit deletion

- `events(limit=100, run_id=None)` returns newest events, ordered by timestamp
  then event ID; the optional run filter still stays in the bound project
- `analytics()` computes retained-window aggregates with explicit denominators
- `plan_export()` reports full retained export count, canonical JSON byte count
  and digest without writing a file or transmitting anything
- `export(limit=100)` returns minimized data in memory, including total eligible
  count and an explicit `truncated` flag; use the policy count ceiling for full
  export. The caller must separately authorize any file destination or recipient
- `plan_delete(action='retention'|'clear')` returns exact event IDs and a snapshot
  digest for this ledger only, including expired rows
- `apply_delete(plan)` explicitly applies that exact plan in one transaction;
  wrong-project, altered or stale plans fail. It does not delete source or
  evidence files and never creates storage solely for an empty plan

A plan is not an approval system. An integration must obtain whatever user
consent its environment requires before applying it. Exporting beforehand is
optional and explicit; the library cannot confirm an export was saved safely.
Deletion has no undo and is logical row deletion, not secure erasure. Clear does
not delete the ledger file or change permissions. There is no unbounded bulk
export, recursive filesystem deletion or policy-migration operation.

## Analytics semantics and limits

Zero-result rates use successful or partial searches, excluding failed,
cancelled and timed-out operations. Weak-result rates additionally exclude
missing/error verdicts, with `verdict_search_count` exposing that denominator.
Weakness is the caller's explicit verdict, and an absent verdict means unknown.
Repeated-query rate is `(fingerprinted searches - distinct fingerprints) /
fingerprinted searches`; missing fingerprints are excluded. Empty denominators
return `None`, not zero. Search latency includes all search statuses and uses
nearest-rank p50/p95. Operation/runtime/status/cause counts cover all events.
No query text, top topic inference or ranking/confidence adjustment is produced.
Rates describe only the retained window; truncation/retention is not event loss.

Run `python benchmarks/operational/ledger_smoke.py` and
`python -m pytest -q tests/test_issue_259_interaction_ledger.py` for reproducible
synthetic mechanics and overhead evidence. The benchmark prints observed local
latencies; it establishes no production overhead SLA or retrieval-quality gain.
Session resume/compaction, subagent lineage, context packets, HTTP parity,
end-to-end failure classification and diagnostic-time reduction remain untested
and gated. See the [stage record](test-cards/259-private-operational-ledger.md).
