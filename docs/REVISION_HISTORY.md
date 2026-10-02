# Opt-in observed source revision history (#73)

## Decision and boundary

The candidate implements **R2: stable document identity + durable observed source
revisions**, behind `TesseraEngine(..., revision_history=True)`. The default
remains R0. The proposed decision is **KEEP the opt-in R2 baseline**; adoption as
a default, retention policy and temporal validity are separate decisions.

Current source text remains authoritative for current retrieval. The archive
records what was observed; it does not establish what was true, valid, preferred,
authoritative or in force at a time. Revision order is observation order, not
`valid_from`/`valid_until`. A new document with `supersedes` is still a separate
memory, while a revision shares the same `source.document_id` and normally the
same memory identity. Changing an explicit memory ID is retained as an explicit
identity change on the same document, not silently merged with an independent
source.

## Usage

```python
from tessera import TesseraEngine

engine = TesseraEngine("./memories", revision_history=True)
engine.build_index()
hits = engine.retrieve_context("browser capture")
evidence_id = hits[0]["evidence"]["evidence_id"]
document_id = hits[0]["provenance"]["source"]["document_id"]

# After source edits, index rebuilds or complete derived-index deletion:
engine = TesseraEngine("./memories", revision_history=True)
resolved = engine.revision_history.resolve_evidence(evidence_id)
print(resolved["revision"]["raw_text"])
print(resolved["evidence_text"])  # None when the original span was unprovable
print(engine.revision_history.list_revisions(document_id))
```

`resolve_evidence` returns `None` for an unknown ID. Existing IDs return the
original evidence record, full archived source text and its exact line span
when known. `status: archived` means the bytes are available in history; it
makes no assertion that the version is current or temporally valid. For the
same version/span, path changes and extraction methods can reuse an evidence
ID; history preserves the first recorded path/method and separately records
observed path transitions. Both document-level and actually issued
query-specific evidence IDs are durable.

This is a Python opt-in experiment. CLI, MCP and configuration schemas do not
silently enable it. The same constructor option works with an explicitly
resolved v2 configuration, capturing only its already selected source roots.

## Storage, indexing and write policy

- `store/.tessera_history/revisions.sqlite3` is **durable historical source
  storage**, not a derived index. Back it up with the source store
- `index.path`, graph snapshots, manifests and the current Evidence Ledger
  remain disposable and rebuildable. Index and history paths may not overlap
- Full normalized UTF-8 source text, its document/content hashes, observed
  identity/location and evidence records are retained atomically in SQLite
  transactions with `synchronous=FULL`. Canonical parsing normalizes CRLF to LF;
  this is a text history, not byte-for-byte binary preservation
- Revisions and evidence are insert-only; SQLite triggers reject UPDATE and
  DELETE. Repeated observation of unchanged text at the same path emits no new
  transition. A -> B -> A records three observations and stores two full bodies
- The archive is excluded from indexing, discovery and corpus diagnostics,
  including explicitly selected archive roots. Historical revisions never
  become duplicate live memories or participate in ranking
- Indexing snapshots parsed versions, including seeding history on an existing
  cache hit. Renames retain identity using observed identities even if the
  derived identity manifest is subsequently removed
- Rejected/reviewed/invalid-format writes produce no archive. For accepted
  writes, the existing body is committed to history **before** `os.replace`;
  the new body is captured only after replacement succeeds. A failed replace
  cannot create a fictional committed new revision
- A failure preserving the old version prevents replacement. A failure
  archiving the new version after replacement raises `RevisionHistoryError`
  with `source_committed=True`; the old revision remains durable, the new source
  exists, and the caller must repair history by a successful index/capture
  before treating the operation as fully archived. There is no rollback claim
- Reading archived evidence verifies source hashes and evidence fingerprints;
  corrupt/unavailable archives fail visibly. History mode does not silently
  fall back to destructive R0 behavior
- After a source changes without reindexing, query evidence spans use the exact
  archived version represented by the graph. Call `build_index()` to retrieve
  the new current version. This does not introduce an implicit live-source
  refresh or reinterpret evidence freshness

## Reversibility and limitations

Disable the constructor option to return to the unchanged R0 behavior; no
history is deleted or sources rewritten. Re-enabling captures then-current
sources and retains prior records, but cannot reconstruct changes made while
capture was disabled. No migration, automatic retention/deletion or restore-to-
source command is provided. Restoring an old source is an explicit user write.

Only **observed** versions can be preserved. External edits/deletions before the
first capture, or multiple external versions between indexing runs, cannot be
reconstructed. There is no filesystem watcher, process-wide writer lock,
external-editor transaction or tamper-proof signature. Serialize writes and
indexing for the same store; a concurrent external writer between capture and
replacement is outside the guarantee. Backups, disk health, filesystem durability
and explicit access control remain operator responsibilities. Archive text may
include information deliberately removed from the live source; treat the
archive with the same privacy controls as the original corpus.

The post-commit error boundary is intentionally explicit and does not depend on
unmerged write-receipt work (#263). Durable idempotent receipt recovery should
compose with it, but is not claimed in this PR. Full temporal state, conflict
resolution and admission remain downstream #15/#16/#19 work. No authority or
“latest wins” semantics are introduced.

## Evaluation

Run `python benchmarks/revisions/lifecycle.py --output /tmp/revisions.json`.
The [benchmark record](../benchmarks/revisions/README.md) compares R0/R1/R2 and
a benchmark-only R3 current-hash pointer. R3's pointer offers no extra
reconstructability or retrieval accuracy on this fixture and adds another
coordination surface. Full R3 temporal validity is deferred to #15; this result
must not be described as a temporal-state implementation.
