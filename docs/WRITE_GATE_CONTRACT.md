# TESSERA Write-Gate Contract

## Scope

The write gate is a deterministic, auditable policy for a small versioned set
of known hostile instruction patterns and suspicious tags. It is not a semantic
prompt-injection classifier and does not claim comprehensive State
Contamination protection.

## Pipeline and mutation boundary

```text
detection
→ optional deterministic transformation
→ admission decision
→ atomic Markdown persistence
→ derived registry / index / graph / Evidence Ledger updates
```

Admission is final before any write-specific durable mutation. `reject` and
`review` create or overwrite no memory file, update no registry/graph/ledger,
and trigger no index rebuild. Review means “return the decision to the caller
for external/manual handling”; TESSERA has no canonical quarantine store.

## Canonical result

```yaml
threat_detected: true | false
content_changed: true | false
admission: accept | accept_sanitized | reject | review
reasons: [stable_machine_readable_reason]
original_hash: sha256:<64 lowercase hexadecimal characters>
persisted_hash: sha256:<64 lowercase hexadecimal characters> | null
persisted: true | false
filepath: string | null
is_sanitized: true | false
```

Hashes cover the exact UTF-8 content payload passed to the gate and the exact
accepted content payload placed after the fixed Markdown frontmatter separator.
TESSERA performs no trimming or Unicode/newline normalization between that
decision and persistence.

## Invariants

- `content_changed` is true exactly when an accepted candidate's original and
  persisted hashes differ.
- `accept` has an unchanged candidate and `is_sanitized=false`.
- `accept_sanitized` requires a changed candidate and no confirmed hostile
  pattern remaining in it.
- `reject` and `review` have `persisted_hash=null`, `persisted=false`, and no
  persistence candidate.
- Reasons are unique and deterministically ordered.
- The compatibility `sanitized`/`is_sanitized` value derives from
  `admission=accept_sanitized AND content_changed=true`.
- Unsupported persistence formats still fail before the gate and every side
  effect under the Markdown-only #94 contract.
- Persistence uses a same-directory temporary file and atomic replacement; a
  failed write returns no false success result and preserves an existing file.

Impossible states are rejected by the result model, including unchanged
`accept_sanitized`, changed `accept`, successful rejected persistence, or a
sanitized candidate that still contains a known hostile pattern.

## Deterministic policy

| Input class | Admission | Mutation |
|---|---|---|
| safe non-empty content | `accept` | exact content persisted |
| known direct hostile instruction that can be removed | `accept_sanitized` | transformed content persisted |
| empty or whitespace-only content | `reject` | none |
| known hostile text in explicit quote/code/documentary context | `review` | none |
| suspicious tag without a transformable direct pattern | `review` | none |
| detected pattern that remains after attempted transformation | `review` | none |

Quoted/documentary handling is deliberately conservative: recognized quote,
code, or security-analysis contexts are not silently destroyed, but they are
also not admitted to the canonical corpus. General intent classification is out
of scope.

## Public surfaces

- Python: `write_memory_note_result()` returns the canonical `WriteResult`.
- Compatibility Python API: `write_memory_note()` returns a filepath for an
  accepted write and raises `WriteGatingViolationError` carrying the result for
  reject/review.
- CLI: `tessera write ... --json` emits the canonical result and exits `2` for
  reject/review.
- MCP: `write_memory()` returns the canonical fields, rebuilds only after
  accepted persistence, and keeps `mem_id` as a compatibility alias.
- Markdown: accepted source frontmatter records the same decision and hashes.

No surface may infer or report stronger protection than this canonical result.
