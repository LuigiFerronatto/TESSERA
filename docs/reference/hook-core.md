# Experimental provider-neutral Hook Core (#196)

## Status and boundary

This is an unmerged experimental SDK candidate. It does not install hooks,
change provider settings, replace `TesseraTaskHook`, expose a new MCP tool, or
save canonical memory. The implementation has no Engine or model callback.

```
provider JSON -> frozen adapter -> LifecycleEvent -> HookCore
                                                  -> bounded RunBuffer
                                                  -> bounded context packet
                                                  -> candidate boundary signal
```

`provider hook event != TESSERA lifecycle event`. Only `EventType` drives core
semantics. Runtime names and wire decisions stay in `tessera.hook_adapters`.
The machine-readable envelope is
[`schemas/lifecycle-event-v1.json`](schemas/lifecycle-event-v1.json).

## SDK contract

```python
from tessera.hook_adapters import FrozenHookAdapter, Invocation
from tessera.lifecycle import (
    ContextCatalog, ContextSection, HookCore, ProjectBinding, RunBuffer,
    resolve_binding,
)

configured = ProjectBinding("project-notes", "/absolute/configured/project")
scope = resolve_binding([configured], cwd="/absolute/configured/project")
# The integration supplies correlation; IDs are not inferred from prompt text.
invocation = Invocation(
    delivery_id="delivery-001", sequence=0,
    occurred_at="2026-10-02T00:00:00Z", tessera_run_id="run-001",
    turn_id="turn-001",
)
adapter = FrozenHookAdapter("gemini")
normalized = adapter.normalize("BeforeAgent", {
    "session_id": "session-001", "hook_event_name": "BeforeAgent",
    "cwd": "/absolute/configured/project", "timestamp": "2026-10-02T00:00:00Z",
    "transcript_path": "/absolute/runtime/transcript.json",
    "prompt": "Find the documented release procedure.",
}, invocation, scope)
core = HookCore(RunBuffer("run-001", scope), catalog=ContextCatalog(
    scope.scope_id, (ContextSection("rules", "Check release evidence."),),
))
results = [core.receive(event) for event in normalized.events]
response = adapter.render_response(results[-1], "BeforeAgent")
# Send response.stdout/response.stderr and its exit_code to the runtime.
```

This prepared context catalog is a bounded, caller-supplied read snapshot. It is
not Working Context (#167), the Context Compiler (#169), a query planner or a
retrieval-quality claim. The integration owns refresh and supplies only trusted
sections from the selected project. It must propagate normalization diagnostics
as well as core diagnostics; unsupported events and unknown tool outcomes are
not successful feature execution.

### Project and identity ownership

The resolver only considers at most 64 explicitly configured bindings. It uses
explicit scope, exact provider root, nearest configured enclosing root, then an
explicitly named global scope. It resolves physical paths on the executing host,
checks containment and rejects ambiguity. There is no filesystem search, git or
language assumption, environment-selected fallback, `$HOME` scan or implicit
project merge. An unmatched provider root yields no project. An out-of-scope
explicit binding fails. An unbound event is not captured.

A session, turn, provider task, TESSERA run, episode and subagent have separate
fields. A missing turn is not replaced by a session ID. The integration must
supply missing native turn/tool IDs and a stable delivery ID, sequence and time
for replay. A repeated identical user prompt with a new delivery ID is a new
event. Sequence numbers allocate four ordered slots per provider invocation.
There is no inference of task completion or episode identity from Stop.

For child lifecycle events, the integration supplies a child run ID and the
parent turn; the native child ID is retained. Where the provider only supplies
a name, a unique externally correlated ID is mandatory. A parent RunBuffer can
retain child events linked to that parent. Explicit `evidence_origin_id` ties a
child report to its parent tool echo: one episode-input group preserves both
observations and all event/lineage references. Equal text alone is not lineage.
The later #137 durable artifact contract remains separate.

### Capture, checkpoint and learning

RunBuffer is append-only in memory, with 256 events and 1 MiB as defaults. Limits
are configurable within hard upper bounds. Overflow rejects new evidence and
reports degradation; it does not silently evict earlier evidence. Events are
immutable and payload access returns a copy. Retried safe events are idempotent;
conflicting retained content/metadata or reordered new events are rejected.

Content capture defaults to omission. The opt-in `CapturePolicy(include_content=True)`
retains text only after recursive credential-field/value redaction. This is
best-effort scrubbing, not a general DLP guarantee: integrations handling unknown
sensitive content should keep omission enabled or enforce stronger upstream
policy. Redaction precedes journal append, deduplication fingerprints and
checkpoint generation. Raw transcripts, paths and compact summaries are never
read. Provider raw blobs are not retained.

`checkpoint()` returns bounded sanitized bytes; `restore()` revalidates and
reapplies capture policy. No disk file is created. The integration must explicitly
choose secure ephemeral storage, serialized ownership, restart behavior and
retention. This SDK does not promise recovery after an uncheckpointed crash.

Every accepted event emits `CAPTURE_EXPERIENCE`. Startup/resume/before-reasoning
can emit `READ_BEFORE_REASONING`. Turn/session end emit candidate boundary signals
for #138 and quiescent/closed run states. They never emit `WRITE_AFTER_LEARNING`.
Episode inputs are evidence groups, not selected episodes or memory candidates.
No result can claim `persisted=True`; no admission or writer is invoked.

### Bounded execution and degradation

The core's synchronous path only performs bounded validation, redaction, append
and prepared-section rendering. It cannot call arbitrary retrieval callbacks,
start subprocesses, download models, enrich content or build an index. Defaults:
128 KiB per event, 64 context sections/1 MiB catalog, 50 ms cooperative execution
budget, 8 KiB output and an 8,192 conservative token upper bound. UTF-8 byte count
is used as an explicit conservative token bound, not a model tokenizer or a
billing estimate. This is bounded work with deadline checks, not hard real-time
OS scheduling or preemptive cancellation.

Sections that exceed either output limit fall back to an evidence pointer when
it fits. `omitted_sections` names every omitted full section; `pointer_sections`
names each fallback. No partial text is silently truncated. Deadline exhaustion
drops late context and reports omissions. Capture/context failures continue by
default; explicit `raise` policies let the embedding integration handle them.
They do not grant provider blocking authority. Wire failures return nonblocking
exit 1 and code-only stderr, never exit 2 or a blocking/rewrite decision.

## Frozen provider profiles

Version `2026-10-02.v1` records documented subsets, not universal runtime version
support. `describe()` returns mappings, capabilities, source URL and limitations.
Native runtime version is caller-supplied metadata, never fabricated. Synthetic
fixtures use invented content and documented fields, not captured sessions.

| Profile | Prompt boundary | Response boundary | Material limitation |
|---|---|---|---|
| Claude | UserPromptSubmit | Stop | prompt_id availability varies by version |
| Codex | UserPromptSubmit | Stop | opaque tool output has unknown outcome |
| Gemini | BeforeAgent | AfterAgent | no native subagent/post-compaction pair in frozen subset |
| Copilot CLI camelCase | userPromptSubmitted | agentStop | command prompt output ignored; stop lacks inline final text |

Claude and Codex receive event-named `hookSpecificOutput.additionalContext` only
on supported events. Gemini uses its supported hook-specific context object and
strict JSON. Copilot uses top-level context only on supported events. All adapter
stdout is one JSON object; diagnostics are on stderr. Permission and blocking
capabilities are advertised conservatively and never exercised by memory logic.

Codex MCP output can provide explicit `isError`; opaque Bash text is not parsed
into invented success. Gemini normalizes documented response errors; Claude and
Copilot use separate failed-tool events. Copilot subagent names do not replace
unique child IDs. Additional provider events return an unsupported diagnostic
until reviewed. No transcript reading fills capability gaps silently.

Official references verified on 2026-10-02:
- [Claude hooks](https://code.claude.com/docs/en/hooks)
- [Codex hooks](https://developers.openai.com/codex/hooks), currently redirected to the official ChatGPT Learn reference
- [Gemini hooks](https://geminicli.com/docs/hooks/reference/)
- [Copilot hooks](https://docs.github.com/en/copilot/reference/hooks-reference)

## Evidence and limitations

`python -m benchmarks.hooks.run --output artifacts/hooks-parity.json` runs an
actual canonical/journal/milestone comparison, not just transport smoke. Equivalent
Claude/Codex runs include user input, successful and failed tools, subagents, a
parent echo, compaction, final learning text and session end. Fourteen strict
gates compare canonical semantics, episode inputs, lineage, load timing,
boundary signals, duplicate origin count, checkpointing and repeatability.
Negative controls corrupt Stop mapping and remove evidence. Reports identify the
measured commit, source/fixture hashes and dirty state. CI checks out the exact
PR head, runs the experiment and uploads its report.

The candidate decision is ITERATE. End-to-end memory-candidate, admission/LTM,
and actual Working Context outcomes are explicitly NOT_EXECUTED. Zero durable
writes proves a safety invariant, not a memory-quality improvement. Gemini and
Copilot have separately tested mappings; full equivalent-run parity is not
claimed across their missing capabilities.

Expanded issue comments also request real index self-heal, relevant-write
frontmatter/link validation, hygiene/drift reports, OS command/interpreter plans
and execution failure diagnostics. Actual maintenance/validation/hygiene handlers,
Windows/macOS/Linux provider installations, command selection/preflight and a
persistent generic CLI/MCP receiver remain unimplemented. Returned deferred-effect
codes make those gaps visible. #177/#190 retain trust review, inspectable dry-run,
installation/uninstall and OS-specific command ownership. No dependent issue is
marked unblocked or delivered by this candidate.

Rollback: remove the additive modules/workflow/docs. Existing Hook, CLI, MCP,
source text, three drawers, retrieval and durable writes remain unchanged.
