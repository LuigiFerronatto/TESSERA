# Historical conversation source import (experimental, #191)

## What this candidate provides

Explicit files become inspectable, source-backed conversation evidence. Nothing
in this workflow discovers personal history, calls a provider, installs a runtime,
executes tool events, creates candidate memories, or admits durable memories.
The raw export is never rewritten. C0 source preparation is available; indexing
uses the existing, separately invoked Engine. C1–C3 are not implemented.

The interface deliberately requires a root, exact relative filenames, one adapter
revision, and an opaque project scope. It does not scan even the supplied root:
there are no glob patterns, home defaults, ancestor searches or background hooks.
Unsupported files and format details are visible errors, never best-effort dropped
turns. An unsupported file blocks the whole apply preflight.

## Preview, review, import, index

```bash
tessera conversations preview \
  --root ./exports --path session.jsonl \
  --adapter generic-jsonl-v1 --project-scope example-project

# Review the JSON totals, individual sessions, diagnostics, transformations,
# root/scope, limits and plan_hash. Copy that exact plan_hash to apply.
tessera conversations import \
  --root ./exports --path session.jsonl \
  --adapter generic-jsonl-v1 --project-scope example-project \
  --output ./conversation-evidence --plan-hash sha256:PREVIEW_HASH

# Optional, explicit follow-on indexing; no project configuration is changed.
tessera index ./conversation-evidence
tessera query ./conversation-evidence "calibration sample" --json
```

Repeat `--path` for additional exact files. All conversation commands emit JSON.
Exit 0 means a supported preview or successful apply; exit 2 reports an invalid
request, unsupported source, changed preview, or apply failure. `import --dry-run`
returns a fresh preview and never creates the output directory. The input and
output directories must be disjoint (neither can contain the other).

A preview includes source count, bytes successfully read, unique session/turn
counts, duplicates, unsupported reasons, redaction/attachment counts, and zero
candidate work. Unsupported/unreadable/oversized files have `size_bytes: null`
when no bounded payload could be read; those bytes are not presented as measured.
It does not print transcript content or arbitrary unknown-field names/values.
Apply repeats the preview and rechecks raw hashes before writing any source.
A changed input, policy, adapter, limits or plan invalidates the supplied hash.

## Declared input contracts

### `generic-jsonl-v1`

UTF-8 JSONL, one conversation header followed by ordered turn records. The header
requires `schema: tessera.conversation.v1`, `type: conversation`, `runtime`,
`session_id`, and `project_scope`. The scope must exactly equal the CLI scope.

```jsonl
{"schema":"tessera.conversation.v1","type":"conversation","runtime":"generic","session_id":"session-1","project_scope":"example-project"}
{"type":"turn","turn_id":"u1","role":"user","timestamp":"2026-01-01T00:00:00Z","content":"What is the sample code?"}
{"type":"turn","turn_id":"a1","role":"assistant","parent_turn_id":"u1","content":"The sample code is basalt-42."}
```

Each turn requires `type: turn`, unique `turn_id`, supported `role`, and `content`.
Supported roles are `user`, `assistant`, `tool`, and `system`. Missing timestamps
remain null; provided timestamps must be timezone-aware ISO 8601 strings and
retain their original representation. Physical record order is authoritative;
no timestamp sort or invented date occurs. An optional `parent_turn_id` must
reference an earlier turn in this export. Branch relationships are preserved.

`content` is a string or ordered blocks:

- `text`: a required string `text`
- `tool_use`: string `id` and `name`, and object `input`
- `tool_result`: string `tool_use_id`, string/text-or-attachment-block `content`,
  optional boolean `is_error`
- `image`, `document`, `audio`, `video`, `file`: excluded, with typed placeholders

Tool IDs and ordering are preserved; duplicate call IDs fail. Results referring
to an unavailable call produce `unresolved_tool_reference`, never a fabricated
link. Tools are data and are never invoked. Optional turn `attachments` is an
array whose items become exclusion placeholders, without their bytes or paths.
Unsupported block/record/role types fail the file. Unknown extra fields produce
line-numbered `unknown_fields_excluded` diagnostics; original values remain only
in the unchanged source export, addressable through its path, raw hash and line.

Identifiers are bounded, printable ASCII labels; paths used as project scopes
are opaque metadata and are never traversed. This v1 restriction is intentional;
unsupported identifiers fail rather than being coerced or replaced.

### `claude-code-linear-v1`

A deliberately strict subset of Claude Code JSONL, selected explicitly. It is
based on the field names and chain semantics in Anthropic's official
[session reader](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/sessions.py)
and the documented ordered user/assistant message shape in the
[session-browser cookbook](https://platform.claude.com/cookbook/claude-agent-sdk-05-building-a-session-browser),
checked on 2026-10-02. The adapter revision is TESSERA's contract, not a claim
that Anthropic guarantees the internal transcript format is permanently stable.
No provider implementation or private transcript is included in fixtures.

Every record must be `user` or `assistant`, with `uuid`, `sessionId`, `cwd`,
`parentUuid` and `message: {role, content}`. Session ID and cwd must match across
the file; cwd must exactly equal the explicitly supplied project scope. The
first parent must be null and each later parent must equal the preceding uuid.
The same content-block rules apply. User-wrapped tool results remain `user`
turns, preserving the provider's participant semantics. Their blocks retain tool
references; the importer does not relabel them as tool-role turns.

Sidechains, team branches, meta messages, compaction summaries, progress/system
records, broken/branched chains and unknown content variants fail visibly. This
is **not** a complete Claude history importer or automatic runtime detection.
Export/normalize unsupported sessions into the generic contract only after
separately verifying their semantics. Codex, Gemini, ChatGPT and Slack formats
are not advertised or guessed. No actual history directory was accessed to
implement or validate these adapters.

## Inspectable source and derived manifest

Each session is one UTF-8 Markdown source named `conv_<64 hex>.md`. Its
JSON-compatible YAML frontmatter contains the complete normalized conversation
and provenance; its body is a human-readable, ordered projection for the current
source/segment index. The document type is `conversation` with `drawer: null`.
Conversation is a source facet, not a fourth semantic drawer. The index schema
is bumped so old caches cannot retain a prior drawer interpretation.

The envelope stores:

- runtime, original session ID, explicit project scope, adapter and policy revision
- stable source identity, original file paths and exact SHA-256 raw-byte hashes
- ordered turn IDs, positions, roles, timestamps, parent IDs and original line numbers
- ordered text/tool blocks, attachment exclusions and transformation diagnostics
- first/last available timestamp in transcript order (`started_at` / `ended_at`)

The raw hash is an integrity locator, not a decryption or source-reconstruction
mechanism. Keep the original export if exact pre-redaction bytes are required.
A raw-line reference is not a canonical #137 memory derivation or a span in the
normalized Markdown. Engine evidence spans refer to the normalized source; the
nested envelope separately identifies the raw export. These identities are not
silently presented as interchangeable.

The human projection escapes square brackets to prevent historical Markdown
links from synthesizing graph relations. The normalized frontmatter preserves
those brackets, subject only to the explicit redaction policy. All transcript
content remains untrusted evidence, including historical system instructions.
Retrieval relevance supplies no instruction authority or truth guarantee.

`conversation-manifest.json` is bounded derived bookkeeping. It records artifact
and raw/normalized hashes, source identity and turn count. It is not automatically
indexed and does not contain raw transcript text. Deleting it does not destroy
the independently inspectable source. Reimport can recover an identical orphan
artifact and rebuild the manifest; differing unmanaged artifacts fail closed.

## Identity, updates and interruption

`source_identity(runtime, project_scope, session_id)` hashes a canonical JSON
array of those three labels, not a file path or content hash. A renamed/moved
export keeps one session filename. The same session ID under a different runtime
or scope remains distinct. This helper is the compatible future live/history
boundary, not proof of equivalence. Integrations must first prove that they mean
the same provider session and scope; #196 delivery event IDs are separate.

Exact reimports preserve source bytes and mtime. Identical duplicate sessions in
one batch collapse, retaining the supplied source locators. Conflicting versions
of the same identity in one batch fail. A later edited/appended source replaces
the complete current normalized snapshot under the same identity; this version
does not claim delta parsing or immutable revision history (#73).

Writes use exclusive, no-follow temporary files and atomic replacement. A lock
serializes importers. Each session file is atomic; the batch is not a filesystem
transaction. Interruption after source replacement but before manifest update is
recoverable by retrying the same inputs. Previously completed sessions are not
duplicated. Manually edited/corrupt sources are never overwritten; an artifact
hash mismatch blocks the run. A stale lock fails closed and requires an operator
to verify the prior importer has stopped before explicitly removing it.

## Bounded safety and redaction policy

Default bounds: 1,000 explicit files, 4 MiB/file, 32 MiB successfully read per
preview, 512 KiB/JSONL record, 10,000 turns/session and JSON depth 12. Python
callers may provide positive `ImportLimits`. No archive unpacking is supported.
Duplicate JSON keys, nonfinite numbers, malformed/truncated JSON and invalid
UTF-8 fail; a complete final JSONL record need not end with a newline.

Reads reject symlinks at every path component, hardlinks and non-regular files.
Descriptor-relative no-follow reads pin ancestors and compare file metadata
before/after reading. Output writes also use pinned directory descriptors. The
current safe I/O implementation requires POSIX no-follow/dir-fd primitives; other
platforms return `secure_io_unavailable` instead of silently weakening the policy.
This is a known Windows limitation pending a verified equivalent implementation.

The versioned heuristic redacts common API-token prefixes, private-key blocks,
Bearer values, textual password/key/secret assignments and sensitive keys in
structured tool inputs. It excludes attachments without opening paths, fetching
URLs or copying embedded bytes. It is **not** comprehensive PII/secret detection,
semantic prompt-injection defense or permission for remote processing. No remote
processing path exists here. Review exports and restrict output directory access
before importing sensitive material; permissions on existing directories are not
silently changed. Normalized artifacts and manifests are newly written mode 0600.

## Evidence and remaining gates

Run the synthetic adapter suite and deterministic source/retrieval experiment:

```bash
python -m pytest tests/test_conversation_import.py -ra
python benchmarks/conversations/evaluate.py --output /tmp/conversation-evaluation.json
python benchmarks/sanity/ci_eval.py --output-dir /tmp/conversation-sanity
```

The experiment measures 24 synthetic sessions / 96 ordered turns, raw-JSONL
baseline visibility, source/role/time retention, query Hit@1, null drawers,
source integrity, retry identity and local cost. It makes no answer-quality or
competitive-memory-system claim. Full LongMemEval dev-50 remains the required
exact-head CI gate under [the benchmark contract](BENCHMARK_CI.md).

Full #191 remains open: complete validated first-party runtime adapters and
onboarding detection; #177/#196 live/history integration fixtures; #138 episode
construction; #137 supporting-turn derivations; #176 enrichment; #19/#92 admission;
and #73 immutable revisions are separate work. This candidate imports source
only, does not close #191 and cannot justify KEEP for the expanded scope.
