# 263 — Truthful single-write outcomes and local repair

| Field | Value |
|---|---|
| Issue | [#263](https://github.com/LuigiFerronatto/TESSERA/issues/263) |
| Record status | `IMPLEMENTED` |
| Capability type | `runtime` |
| Pull request | [PR #290](https://github.com/LuigiFerronatto/TESSERA/pull/290) (merged) |
| Head commit | Final candidate `894464179c669d876f4d2f1f314f4699559ae49a` |
| Merge commit | `4b8606112d26b9294f295edcd988af41082ea415` |
| Decision | `PENDING` lifecycle adoption; proposed `KEEP` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-12 |

## In one sentence

A successful file save can now be distinguished from a failed index or ledger
update, and the missing derived state can be repaired without writing the note again.

## What problem existed?

Source replacement and derived updates were not a transaction. MCP could raise
an error after successfully writing a note, leaving callers unsure whether a
retry would write it again. Python/CLI did not perform the same derived stages.

## How did TESSERA behave before?

The gate returned admission and `persisted` fields. Python/CLI completed after
persistence; MCP refreshed afterwards without a durable per-operation receipt.
There was no single-write operation-ID recovery or inspection surface.

## What changed or is being tested?

An explicit operation ID selects a shared Python/CLI/MCP lifecycle, durable
content-free intent/receipt, source operation marker, local process/thread lock,
and separate index/ledger checkpoints. Existing calls keep their behavior.
Admission rules, retrieval scoring and canonical Markdown bodies are unchanged.

## How does it work now?

IMPLEMENTED ON `main`. The [receipt contract](../../reference/write-receipts.md) specifies
opt-in, outcomes, recovery, supported filesystems, journal retention and privacy.
A clean local repair bypasses stale in-memory state and pickle loading, then
rebuilds derived graph/index/manifest and evidence from canonical sources.
Doctor and receipt inspection expose incomplete or corrupt outcomes.

## Concrete example

A ledger failure after a successful save returns `persisted: true`,
`indexed: complete`, `evidence_ledger: failed`, `repair_required: true`.
`tessera receipt repair STORE --operation-id ID` rebuilds the missing state;
the exact canonical bytes and revision fingerprint stay unchanged.

## How was it validated?

- Runtime candidate `cc8f106a863c88dc5095a11b1430961f7cfc148f`: 599 tests
  passed and 5 existing gh-aw CLI tests skipped on Python 3.12.14; installed
  wheel passed all 19 MCP protocol checks outside the checkout. Offline
  wheel/sdist builds, compileall and whitespace checks passed. Exact-head
  remote CI remains distinct from this local evidence.
- `tests/test_write_receipts.py`: pre-source failures, journal/index/ledger
  failures, real process crashes after replacement and after indexing,
  independent-process concurrent retries, corrupt/missing state, exact CRLF
  bytes, request conflicts, superseded/deleted sources, secret-free diagnostics,
  read-only doctor, and Python/CLI/MCP parity
- `scripts/clean_room/check_mcp.py`: installed stdio write/retry/inspect/repair
  JSON-RPC contract and capability discovery
- `benchmarks/sanity/write_receipt_smoke.py`: 12 repair attempts, 12 successful
  repairs, zero false successes, zero duplicate writes/revisions;
  [local evidence](evidence/263-write-receipts-smoke.json)
- Local one-note median: persistence only 0.945 ms, legacy write+refresh
  5.724 ms, receipt write+refresh 7.817 ms; two-note repair 11.500 ms
- Deterministic sanity: Hit@1 0.75, Hit@3/5 1.0, MRR 0.875,
  evidence hit rate 1.0; missing-evidence check passed

Latency is informational for this temporary local filesystem, not a production
SLO. Full-suite and exact-head CI evidence belong in the PR. No provider was used.

## Canonical delivery and check evidence

[PR #290](https://github.com/LuigiFerronatto/TESSERA/pull/290) merged on 2026-10-12. Final candidate
`894464179c669d876f4d2f1f314f4699559ae49a` and canonical merge
`4b8606112d26b9294f295edcd988af41082ea415` are distinct identities for one delivery.

- Final-candidate [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203173850)
  and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203173845)
  completed successfully on `894464179c669d876f4d2f1f314f4699559ae49a`.
- Exact-canonical [CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203671135)
  and [Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38203671143)
  completed successfully on `4b8606112d26b9294f295edcd988af41082ea415`.

These are historical engineering checks, not newly run benchmarks. The reviewed
PR discussion has no final-head formal reviews or accepted final-head KEEP
record. Earlier automatic BLOCK comments concern older candidates and are not
current-head defects. Current governance does not require a positive human or
automatic AI review. This correction records delivery and available validation;
it does not invent a retrospective approval or a new capability-adoption decision.

## What improved?

Injected post-source failures retain the successful persistence truth. Real
crash/restart and concurrent duplicate retries preserve source bytes. Repair
reconstructs an equivalent evidence ledger with no duplicated records.

## What remains unimplemented?

The lifecycle is opt-in. Distributed transactions, multi-note atomic commits,
full revision history (#73), post-write hooks (#196), HTTP (#252), and
large-corpus incremental receipt-path optimization are excluded. Historical
idempotency needs retained operation history. Legacy/external writers do not
participate in the new lock. A superseded/deleted source is never restored.

## What is unlocked next?

The bounded receipt implementation is canonical. #92, #12 and #11 were its
prerequisites; it did not depend on then-unmerged PR #282. No downstream card
is promoted by this correction while its own scope and adoption remain separate.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#263](https://github.com/LuigiFerronatto/TESSERA/issues/263) |
| Pull request | [PR #290](https://github.com/LuigiFerronatto/TESSERA/pull/290) (merged) |
| Canonical base | `20814a47ec0f72d7bea0639e0b057df1ecf5cded` |
| Merge commit | `4b8606112d26b9294f295edcd988af41082ea415` |
| Evidence/Learnings/Decision | Failure-injection tests and smoke above; proposed KEEP, lifecycle adoption pending |
| Benchmark record | [Offline local smoke](evidence/263-write-receipts-smoke.json) |
| PR Evolution Audit | #108 write safety, #246 indexing, #229 MCP; PR #290 is the single canonical opt-in receipt delivery; this record only reconciles it |

## Evolution

```text
canonical file saved but derived outcome can be lost
→ opt-in operation ID and truthful stage receipt
→ canonical idempotent retry plus deterministic local repair
→ exact candidate/canonical checks passed; adoption remains pending
```
