# Durable single-write outcome receipts

This is the opt-in #263 candidate contract. A receipt is operational evidence;
Markdown remains semantic authority. A `persisted: true` result means the
canonical replacement occurred, not that indexing or provenance succeeded.

## Enable and consume

Python `write_memory_note_result(..., operation_id="request-unique-id")`, CLI
`tessera write STORE ... --operation-id request-unique-id --json`, and MCP
`write_memory(..., operation_id="request-unique-id")` use the same lifecycle and
return `write_receipt` alongside the existing gate fields. Omit the operation ID
to retain the existing persistence-only Python/CLI behavior and legacy MCP
refresh behavior. This explicit opt-in is the rollback/compatibility boundary.

Choose a unique, non-secret operation ID per intended write, and reuse it only
with the same arguments. IDs accept 1–128 ASCII letters, digits, `.`, `_`, `:`,
`-`, beginning with a letter/digit. Different arguments with an existing ID fail
before another canonical mutation. Request fingerprints include all write fields,
not just the body. Receipts do not store body, tags, entities, descriptions,
provider credentials, or exception strings.

```json
{
  "schema_version": 1,
  "operation_id": "request-unique-id",
  "memory_id": "project/note",
  "persisted": true,
  "source_revision": "sha256:<exact-canonical-file-fingerprint>",
  "source_state": "current",
  "indexed": "complete",
  "evidence_ledger": "failed",
  "hooks": [],
  "hooks_status": "not_applicable",
  "repair_required": true,
  "retry_required": false,
  "errors": ["evidence_update_failed"]
}
```

`source_revision` is an exact-byte SHA-256 fingerprint, not the revision-history
capability owned by #73. `indexed` covers registry, graph, lexical cache and
identity manifest; `evidence_ledger` is checked separately. States are
`complete`, `pending`, `failed`, `not_applicable`. Admission reject/review leaves
both not applicable and creates no operation journal or canonical file. A
pre-persistence storage failure returns `persisted: false`, with no applied
projection. An interrupted intent with no source has `retry_required: true`;
repair cannot reconstruct an unwritten body, so retry the original request.

Hooks have no implementation in this lifecycle: the list is empty and the
capability is `not_applicable`. There is no HTTP transport yet. #196 and #252
remain the owning cards; future adapters should reuse this versioned schema.

## Inspect and repair

- Python: `engine.inspect_write_receipt(id)`, `inspect_write_receipts()`, and
  `repair_write_receipt(id)`
- CLI: `tessera receipt inspect STORE [--operation-id ID]` and
  `tessera receipt repair STORE --operation-id ID`; output is JSON
- MCP: `inspect_write_receipt(operation_id)` and `repair_write_receipt(operation_id)`
- `tessera corpus doctor` reports incomplete/corrupt receipts without mutation

CLI writes exit `0` for a completed write, `2` for an unpersisted result, and `3`
for a persisted result requiring repair. Inspection/repair exit `3` while repair
or original-request retry is required. A JSON result is always available for
expected storage/projection failures. Malformed IDs, request conflicts and an
unrecoverable corrupt journal are argument errors, not false success receipts.

Repair performs a clean local source rebuild without reading the pickle cache,
recreating graph/index/manifest first, then ledger. It never calls a provider,
uses the network, rewrites a canonical source or creates a revision. Repeated
repair yields equivalent graph/evidence content. Timestamps and serialized
cache bytes may change. Component signatures detect missing/changed derived
files; inspection conservatively marks them pending, including a legitimate
external index rebuild. A repair refreshes a shared content-free projection checkpoint. This lets all
receipts whose source revisions are present converge after one complete corpus
rebuild, instead of invalidating earlier receipts whenever a later write runs.

If source bytes changed or disappeared after a confirmed operation, its
historical `persisted` truth remains true, `source_state` is `superseded` or
`missing`, and projection states become `not_applicable`. Repair never restores
an earlier source over a newer user edit. A retry returns the original outcome,
not a replacement of the newer source.

## Crash, concurrency and storage boundaries

1. Validate and admit before mutation
2. Acquire a store-wide process/thread lock
3. Persist a content-free intent in `STORE/.tessera_operations/`
4. Atomically replace the canonical Markdown with an operation marker
5. Reconcile actual source bytes and checkpoint persistence
6. Build/checkpoint index, then build/checkpoint ledger

The intent and receipt use temporary-file replacement with file and directory
fsync on POSIX. Source replacement is followed by directory barriers up to the
store. Windows uses file flush and replacement with an OS file lock; Python's
Windows API does not expose the POSIX directory-fsync guarantee. A crash after
replace but before acknowledgement is resolved from the canonical marker,
request fingerprint and exact source hash. A later protocol write reconciles a
pending predecessor before overwriting its source. Locks are released by the OS
on process death and are never broken using a time-based lease.

The operation directory is separate from the disposable index and must be
retained with the store. Deleting an index does not delete idempotency history.
A missing/corrupt receipt can be reconstructed only while the corresponding
canonical source marker is still present. A corrupt historical receipt without
that source fails closed. Deliberate deletion of both operation history and its
source removes the evidence required to recognize an old operation; callers
must not reuse IDs after discarding that history.

This is not a distributed transaction, a multi-note atomic commit, a full
revision archive, or protection from privileged concurrent filesystem mutation.
Cross-process serialization covers writers using operation IDs; legacy writers
and arbitrary external editors do not participate. Preserve the existing
source-write safety boundary and treat filesystem access controls as trusted.

## Validation and scope

`tests/test_write_receipts.py` injects pre-source, index, ledger and journal
failures; exercises real process crashes/restarts and concurrent duplicate
retries; checks corrupt/missing state, superseded/deleted sources, exact CRLF
bytes, privacy, parity and read-only doctor behavior. The installed stdio
protocol harness checks write/retry/inspect/repair against real MCP JSON-RPC.

Run `python benchmarks/sanity/write_receipt_smoke.py` for repeatable local
false-success/duplicate/repair checks and informational latency. Receipt mode
performs a full source rebuild per write to establish deterministic recovery;
large-corpus incremental optimization remains future work. Retrieval ranking
and admission policy are unchanged. Benchmark applicability is `SMOKE_ONLY`.
