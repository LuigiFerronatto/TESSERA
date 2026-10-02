# #191: Historical conversations become source evidence first

- Status: `IN_PROGRESS` (source-only draft candidate; not merged)
- Issue: [#191](https://github.com/LuigiFerronatto/TESSERA/issues/191)
- Baseline: canonical `20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Decision proposed: `ITERATE` full #191; retain the bounded C0 slice for review
- Canonical merge commit: none

## What problem existed?

Historical JSONL conversations could not enter the existing Markdown/plain-text
source index without manual transformation. Treating every message as a factual
memory would destroy the distinction between conversation evidence and truth.

## How did it behave before?

The source iterator supports text/Markdown and has no conversation-import or
preview contract. Live lifecycle events, decomposition and memory writes are
separate paths. No canonical historical session deduplication was provided.

## What is being tested?

An opt-in, exact-path importer prepares one independently inspectable source per
session, preserving turn roles, order, timestamps, parent/tool references and raw
source locators. It exposes generic normalized JSONL v1 and a strict linear Claude
Code subset; unsupported metadata shapes are diagnosed or rejected. The source
export remains unchanged. Indexing is a separately invoked existing Engine step.

## How does the candidate work?

Preview reports sessions, sizes, turns, duplicates, exclusions and a plan hash.
Apply revalidates it, uses bounded no-follow reads, applies a declared heuristic
redaction/attachment policy and writes non-memory source envelopes atomically.
A manifest supports integrity checks and interrupted-run retries. Stable identity
uses declared runtime, project scope and session ID rather than path or hash.

## Concrete example

A four-turn export containing user, assistant, tool and system records becomes
one `conversation` source with `drawer: null`. A second import reports unchanged.
An appended turn updates that same source. A symlink, malformed record or
conflicting duplicate fails visibly; no provider or memory writer is invoked.

## How was it validated?

The focused suite covers read-only previews, exact plan application, malformed/
partial/deep/large inputs, traversal/symlinks/hardlinks/FIFOs, secret/attachment
exclusion, role/tool/time retention, duplicate/conflicting sessions, append/move,
output tampering, crash retries, lock contention and CLI behavior. The synthetic
benchmark uses 24 sessions / 96 turns and checks query visibility, turn retention,
null drawers, unchanged exports and byte-identical retries. Full regression,
packaging/installed-wheel checks, sanity and exact-head CI are recorded in the PR;
only clean, tested published heads are release evidence.

## What improved in the candidate?

Previously unindexed generic conversation JSONL can become queryable source
evidence without becoming memory. Preview, bounded scope and visible format
failures reduce the risk of accidental personal-history ingestion. Full raw
source reconstruction requires retaining the original export, as intended.

## What remains unimplemented?

Automatic/onboarding discovery; complete Claude, Codex, Gemini, ChatGPT and Slack
adapters; Windows safe-I/O equivalents; multi-file atomic transactions; delta
parsing and immutable revisions (#73); supporting-turn derivation receipts (#137);
structural episodes (#138); live/history convergence (#177/#196); enrichment
(#176); semantic admission (#19/#92). Redaction is heuristic, not comprehensive
PII detection or semantic prompt-injection defense. Full #191 remains open.

## What is unlocked next?

Independent source-envelope review and broader synthetic adapter experiments.
After shared contracts are merged and reviewed, prove exact live/history
identity and supporting-turn derivations without collapsing delivery IDs,
provider session IDs, memory identities or source-version hashes.

## Evidence, rollback and lifecycle

- [Contract and commands](../CONVERSATION_IMPORT.md)
- [Offline synthetic experiment](../../benchmarks/conversations/README.md)
- [Official Claude reader](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/sessions.py)
- [Issue acceptance additions](https://github.com/LuigiFerronatto/TESSERA/issues/191#issuecomment-5673813458)

Rollback: revert the candidate code, retain original exports and normalized
source files, and rebuild derived indexes. Existing text ingestion is otherwise
unchanged. No configuration mutation or migration of original exports occurs.
Human review and exact-head required gates remain necessary; the issue is not
closed and no PR is merged by this work.
