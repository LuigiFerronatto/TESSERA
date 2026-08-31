# #114 — Make every delivery explain its history

| Field | Value |
|---|---|
| Issue | [#114](https://github.com/LuigiFerronatto/TESSERA/issues/114) |
| Record status | `VALIDATED` |
| Capability type | `governance contract` |
| Pull request | [PR #123](https://github.com/LuigiFerronatto/TESSERA/pull/123) |
| Merge commit | [`a79b5ae`](https://github.com/LuigiFerronatto/TESSERA/commit/a79b5aec661f0d401b00c2985eff3a5a24363943) |
| Decision | `KEEP` |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-08-31 |

## In one sentence

Every new task must show what existed before, exactly which merged work created it, what the candidate changes and what is still missing.

## What problem existed?

TESSERA already required hypotheses, measurements, plain-language explanations and decisions. A PR could still describe only its own diff, omit the merge commits that established the current contract, count superseded attempts as separate deliveries or leave the roadmap in a stale pre-merge state.

## How did TESSERA behave before?

Issue authors described the experiment, and PR authors described the candidate. Reconstructing the complete evolution still depended on a reviewer manually searching PR history, commits, changed files and benchmark records.

## What changed or is being tested?

The candidate makes that reconstruction a required part of both templates. It adds the exact audit table, delivery classifications, eight-part capability-state reconciliation and a post-merge lifecycle checklist.

## How does it work now?

**VALIDATED ON `main`.**

An Issue records current and target capability states before implementation. Its PR then verifies the relevant merged and superseded history, reports the candidate delta, and declares how canonical merge evidence will replace temporary head evidence after merge.

## Concrete example

```text
before: "This PR adds X."
after:  "PR A established Y at merge M; this PR changes Y to X;
         benchmark delta is D; Z remains unimplemented; roadmap row R changed."
```

Two PR records sharing one head/merge commit are one delivery, not two independent successes.

## How was it validated?

Contract tests assert the required columns, state reconciliation, delivery classifications, duplicate-delivery rule and post-merge lifecycle markers. PR #123 passed Python 3.9, Python 3.12, smoke, sanity and offline benchmark reporting/applicability.

## What improved?

The templates on `main` now make title-based inference, duplicate counting and stale completion claims visible contract violations.

## What remains unimplemented?

Templates cannot prove that a human or agent performed a correct audit; they make omissions visible and testable. Automated GitHub graph reconciliation and Project-board synchronization remain separate future work.

## What is unlocked next?

#115–#121 can use the same audit structure for repository architecture, packaging, configuration, onboarding, CLI, MCP and Skills.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#114](https://github.com/LuigiFerronatto/TESSERA/issues/114) |
| Pull request | [PR #123](https://github.com/LuigiFerronatto/TESSERA/pull/123) |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | [Issue comment](https://github.com/LuigiFerronatto/TESSERA/issues/114#issuecomment-5473270634) |
| Benchmark record | Not applicable; governance contract tests |
| PR Evolution Audit | PR #24 / merge `089590c`; PR #85 / merge `864a38e`; PR #97 / merge `3fdaa0d`; PR #102 / merge `39febe3`; PR #110 / merge `7f92dd9` |

## Evolution

```text
experimental Test Card template (#24)
→ stronger PR contract (#85)
→ operating model (#97)
→ benchmark applicability (#102)
→ plain-language records (#110)
→ full evolution audit and post-merge reconciliation (#114)
```
