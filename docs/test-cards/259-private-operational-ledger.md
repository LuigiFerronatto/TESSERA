# #259 — Inspect minimized operational events without recording conversations

| Field | Value |
|---|---|
| Issue | [#259](https://github.com/LuigiFerronatto/TESSERA/issues/259) |
| Record status | `IN_PROGRESS` mechanics; `BLOCKED` full session integration |
| Capability type | Experimental Python runtime mechanics |
| Pull request | Draft publication pending |
| Head commit | Exact candidate will be linked in the draft PR |
| Merge commit | Not merged |
| Decision | `PENDING`; proposed `ITERATE` for mechanics only |
| Benchmark applicability | `SMOKE_ONLY` — no retrieval/ranking/admission behavior changes |
| Last audited | 2026-10-02 |

## In one sentence

Test a small, explicitly enabled local ledger that explains operation outcomes
without storing conversation text or silently changing how memories rank.

## What problem existed?

A zero-result search and a failed operation can look alike without a bounded
operational record. Automatically retaining queries or entire tool payloads
would create a separate privacy problem.

## How did TESSERA behave before?

Baseline main `20814a47ec0f72d7bea0639e0b057df1ecf5cded` has the #120 MCP
runtime and #13 corpus diagnostics, but no dedicated operational interaction
ledger. Evidence provenance is already a different, source-derived contract.

## What changed or is being tested?

An independently implemented, default-OFF Python API accepts only bounded
structured summaries, explicit opaque identity and existing evidence IDs.
It adds deterministic transactions/deduplication, scoped inspection, aggregate
analytics, explicit export/retention/clear planning and stale-safe plan execution.
The module never installs runtime hooks, reads history, or edits configuration.

## How does it work now?

TARGET — NOT YET ON MAIN. A trusted caller explicitly enables one project-bound
SQLite file outside source roots. Fixed enums/counters and optional keyed query
fingerprints replace free-form content. Each append prunes bounded retention;
read-only views do not mutate anything. Clear/retention applies only an exact
ledger snapshot and cannot delete canonical memories or evidence.

## Concrete example

A synthetic search reports zero results and `cause='unmatched'`; a separate event
can report `cause='index_missing'`. Both retain project/run/session labels without
a transcript. Repeating the same event ID is a no-op; changing its payload is an
error. An exported one-event page explicitly states whether more events exist.
See the runnable [API example](../INTERACTION_LEDGER.md#minimal-synthetic-example).

## How was it validated?

- `tests/test_issue_259_interaction_ledger.py`: **81 passed**, synthetic temporary
  stores and fake secrets only; final full suite: **646 passed, 5 skipped**
  (the existing `gh-aw` extension-dependent checks), Python 3.12.14
- Coverage includes default-off/no-I/O, explicit identities, cross-project and
  policy rejection, schema/privacy bounds, concurrent initialization/writes in
  threads and processes, deterministic dedup/count windows, expiry, busy errors,
  arbitrary-file/linked-sidecar refusal, bounded ownership reads, unowned hot
  journal/WAL byte preservation, exact/stale/forged deletion plans, read-only
  export plans, corruption refusal, analytics denominators/nearest-rank percentiles,
  and unchanged Engine retrieval
- `benchmarks/operational/ledger_smoke.py`: 1,000 synthetic appends into a 250-row
  store, expected pruning, zero unexpected loss/duplicates, fake-secret scan,
  disabled/enabled overhead, storage growth and explicit clear. Final local
  sample: enabled append p50 **0.532 ms**, p95 **0.839 ms**, max **7.80 ms**;
  250-event analytics **13.84 ms**; database **221,184 bytes** at 250 appends and
  **229,376 bytes** at 1,000. Zero unexpected loss/duplicate rows/fake-secret
  findings; 750 expected prunes and 250 explicit clear removals. This is a local
  observation, not a production overhead SLA
- Deterministic sanity: Hit@1 **0.75**, Hit@3/5 **1.0**, MRR **0.875**, evidence
  hit rate **1.0**; missing-evidence check passed. Final wheel/sdist built and
  contain the exact reviewed ledger module; Python 3.9 grammar check passed
- Python 3.9 and production-filesystem behavior remain exact-head CI/review gates;
  local testing uses Python 3.12. No real user collection occurred

## What improved?

A bounded independently testable implementation can now distinguish supplied
operational causes and inspect retained activity. Privacy tests reject raw text
fields and path-bearing identifiers instead of relying on heuristic redaction.
The mechanics provide no measured retrieval-quality or end-to-end latency gain.

## What remains unimplemented?

Runtime wiring and verified lifecycle identity; full sessions/recent-session
views; compaction/resume/subagent lineage; context-packet integration; raw-content
logging; HTTP/hooks; settings UX; scope authorization; production overhead and
failure-classification accuracy; secure erasure, policy migration and WAL/hot-journal recovery. No proposal
here resolves #196/#177/#171 or closes #259. Logical deletion is explicitly not
backup/forensic erasure; idle stores require an explicit retention operation.

## What is unlocked next?

Review of the schema and standalone mechanics can proceed. Full integration
still requires #196/#177 validation and a separate runtime overhead/failure-policy
review; no dependent product capability is declared unlocked by an unmerged PR.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#259](https://github.com/LuigiFerronatto/TESSERA/issues/259) |
| Pull request | Draft publication pending |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Tests and smoke above; `PENDING` / proposed `ITERATE` |
| Benchmark record | `benchmarks/operational/ledger_smoke.py` (synthetic, SMOKE_ONLY) |
| PR Evolution Audit | #120 [PR #229](https://github.com/LuigiFerronatto/TESSERA/pull/229), canonical `b4ead4d7407b8caa2571e1e366616a468f2ef74f`; this candidate imports none of the unmerged lifecycle proposals |

## Evolution

```text
MCP runtime and evidence provenance, no operational ledger
→ isolated opt-in minimized-ledger mechanics in a draft
→ human review and exact-head CI; no merge/closure claim
→ lifecycle identity validation before real session integration
```
