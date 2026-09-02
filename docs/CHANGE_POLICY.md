# TESSERA Change Policy

## Executive takeaway

TESSERA separates five questions that are easy to blur together:

```text
CHANGELOG
→ what changed in the product?

DECISION TRACE
→ why did we choose this direction?

TEST CARD
→ what were we trying to prove?

PULL REQUEST
→ how was it implemented?

CI / BENCHMARK
→ what evidence says it behaved as expected?
```

These artifacts are linked, but they are not substitutes for one another.

## Why the changelog is curated

A raw commit list answers:

> what was committed?

The product changelog should answer:

> what should a user/integrator/reviewer know changed?

For that reason TESSERA starts with **manual, explicit changelog updates**. Automation may validate that a PR considered the changelog, but it should not fabricate product history from commit messages.

## When a PR MUST update `CHANGELOG.md`

Update `## Unreleased` when a PR changes any of the following:

- public Python API behavior;
- CLI behavior or flags;
- MCP behavior, payloads or configuration;
- supported source formats;
- indexing/retrieval/ranking behavior;
- metadata/schema/output contracts;
- persisted/cache/index schema users may observe;
- default behavior;
- user-visible installation or configuration;
- promoted capability or feature;
- deprecation/removal/breaking change;
- meaningful benchmark/evaluation contract.

## When a PR MAY mark changelog as N/A

Examples:

- typo-only docs edits;
- internal comments with no contract impact;
- test refactors that preserve behavior;
- repository-only visual assets that do not alter a product contract;
- purely historical research-note cleanup.

The PR must still state **why** the changelog is N/A.

## Categories

Use the smallest useful set:

### Added
New user-visible capability, interface or supported behavior.

### Changed
Existing behavior or contract changed without being purely a bug fix.

### Fixed
A documented/expected behavior was broken and is corrected.

### Experimental
A feature/contract is intentionally exposed as experimental and has not yet earned a stable KEEP decision.

### Deprecated
Behavior remains available temporarily but should no longer be used.

### Removed
Behavior/configuration/API was removed.

### Architecture Decisions
Short human-readable references to consequential architectural choices. Do **not** duplicate the full Decision Trace or Test Card here.

## How a PR should write an entry

Prefer one high-signal bullet:

```markdown
### Changed
- MCP retrieval now preserves the canonical structured evidence fields exposed by the engine. ([#123](...))
```

Avoid implementation-only wording:

```markdown
- refactored serialize_result helper
```

unless that refactor is the product-visible change.

## Experimental work

A Test Card can produce code without immediately becoming a stable product capability.

Use `Experimental` when users/integrators can actually observe or invoke the experiment.

If the work is benchmark-only and does not change product behavior, the PR may be changelog N/A and the evidence belongs primarily in the Test Card/benchmark results.

## Decision outcomes

A `DROP` or `REVERT` can still deserve a changelog entry if behavior was previously exposed.

A failed experiment that never reached the public surface normally belongs in:

```text
Test Card → Evidence → Decision Trace
```

rather than the product changelog.

## Release/version relationship

`Unreleased` is the landing zone for merged changes.

A future release process may move those entries into a version/date section. This policy does not require release automation yet.

Do not invent semantic-version bumps merely to satisfy the changelog.

## Agent-drafted changelog entries (narrow, evidence-gated exception)

TESSERA's `tessera-post-merge-lifecycle` agentic workflow (see
[`docs/AGENTIC_GOVERNANCE.md`](AGENTIC_GOVERNANCE.md)) may propose a
`CHANGELOG.md` entry **only** inside a reviewable pull request, and **only**
when every one of the following evidence sources grounds the entry:

- the linked Issue/Test Card;
- the actual canonical merged diff (not a PR title or commit message alone);
- the specific public/contract surfaces affected;
- the final recorded decision (`KEEP`/etc.);
- the canonical merge commit SHA.

This does not weaken the prohibition earlier in this policy: an AI agent must
never fabricate authoritative product history purely from commit messages,
PR titles, or `git log`. A proposed agent-drafted entry is always subject to
the same human/CI review as any other PR change to `CHANGELOG.md`, and the
lifecycle workflow must flag the required entry instead of writing one when
it lacks sufficient grounded evidence.

## Native Issue relationship synchronization

The audited projection in
[`docs/portfolio-relationships.yaml`](portfolio-relationships.yaml) maps the
roadmap and authoritative Issue routing blocks onto GitHub's native `Parent`,
`Blocked by`/derived `Blocking`, and `Relates to` relationships. It is not a
parallel roadmap and must follow this precedence:

```text
authoritative Issue routing
→ current Test Card
→ ROADMAP
→ current Issue body
→ live Issue state
→ conservative fallback
```

Run `python scripts/sync_portfolio.py relationships` for a read-only audit.
Mutation always requires the explicit `--apply` flag. `blocked_by` is the only
stored direction for dependencies; the inverse `blocking` view is derived.
Plain textual mentions are never promoted automatically.

## PR checklist contract

Every meaningful PR should declare:

```text
Changelog
[ ] Updated
[ ] N/A — rationale

Category
Added | Changed | Fixed | Experimental | Deprecated | Removed | N/A
```

The PR Contract v2 task (#66) owns the reusable template language. CI Quality Gate v2 (#67) may later validate that one of these states is present, but it must not auto-edit the changelog.

## Relationship to Decision Trace

Use [`docs/research/DECISION_TRACE.md`](research/DECISION_TRACE.md) for research/architecture provenance such as:

```text
source / paper / production signal
→ insight
→ Test Card
→ evidence
→ architecture decision
```

Use `CHANGELOG.md` for the user-facing consequence once that decision changes the product.
