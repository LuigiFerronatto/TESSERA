# TESSERA Write-Gate Contract

## Scope

The write gate is a deterministic, auditable policy for a small versioned set
of known hostile instruction patterns and suspicious tags. It is not a semantic
prompt-injection classifier and does not claim comprehensive State
Contamination protection.

## Pipeline and mutation boundary

```text
Markdown-only format validation
→ portable memory-ID and resolved-path containment validation
→ detection
→ optional deterministic transformation
→ admission decision
→ atomic Markdown persistence
→ derived registry / index / graph / Evidence Ledger updates
```

Admission is final before any write-specific durable mutation. `reject` and
`review` create or overwrite no memory file, update no registry/graph/ledger,
and trigger no index rebuild. Review means “return the decision to the caller
for external/manual handling”; TESSERA has no canonical quarantine store.

Path validation runs before warnings, timestamps, frontmatter, directory or
temporary-file creation, gate evaluation, and every canonical or derived
mutation. Canonical logical IDs are non-empty forward-slash-separated segments.
Absolute POSIX/Windows paths, drive/UNC forms, backslashes, NUL, empty/dot/dotdot
segments, repeated/trailing separators, non-NFC or platform-ambiguous segments,
and resolved destinations outside the resolved storage root are rejected with
`invalid_memory_id_or_path`. Existing symlinked parents are resolved, so an
escape through one is rejected. Containment uses path ancestry, not a string
prefix.

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
- `accept_sanitized` requires a changed candidate, no confirmed hostile pattern,
  and the versioned complete bounded transformation. The current evaluator does
  not emit this state; it rejects direct known hostile instructions.
- `reject` and `review` have `persisted_hash=null`, `persisted=false`, and no
  persistence candidate.
- Reasons are unique and deterministically ordered.
- The compatibility `sanitized`/`is_sanitized` value derives from
  `admission=accept_sanitized AND content_changed=true`.
- Unsupported persistence formats still fail before the gate and every side
  effect under the Markdown-only #94 contract.
- Persistence uses a same-directory temporary file, file flush/fsync, and
  `os.replace`; a failed write returns no false success result, cleans temporary
  files/new empty parents, and preserves an existing file. This is atomic
  replacement, not a claim of crash durability for the directory entry because
  the parent directory is not fsynced.

Impossible states are rejected by the result model, including unchanged
`accept_sanitized`, changed `accept`, successful rejected persistence, or a
sanitized candidate that still contains a known hostile pattern.

## Deterministic policy

| Input class | Admission | Mutation |
|---|---|---|
| safe non-empty content | `accept` | exact content persisted |
| known direct hostile instruction | `reject` | none |
| empty or whitespace-only content | `reject` | none |
| known hostile text in explicit quote/code/documentary context | `review` | none |
| suspicious tag without a direct pattern | `review` | none |
| invalid or escaping logical memory ID | `reject` | none |

`accept_sanitized` remains an explicit schema state for a future deterministic
rule, but construction currently requires the exact versioned whole-content
redaction candidate. Partial line removal, retained payload lines, or an
unversioned transformation is an impossible state. No current input is routed
to this admission by `WriteGatingEngine.evaluate()`.

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

## Limitations

The pattern list is deliberately small and deterministic. It is not a semantic
classifier, cannot prove general intent, and does not cover all paraphrases or
languages. Quote/code/documentary recognition is syntactic and conservative.
Path resolution rejects existing symlink escapes, but it does not defend
against a privileged concurrent actor swapping filesystem components between
validation and replacement. No quarantine store, LLM, network classifier,
State Contamination benchmark, or evidence-aware admission policy is included.
