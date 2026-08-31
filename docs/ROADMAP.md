# TESSERA — Experimental Roadmap

TESSERA is an **agent-agnostic, text-first memory and evidence layer**. It hides storage, indexing, relations, temporal metadata and retrieval mechanics while preserving enough **evidence, provenance and navigation** for the consuming agent to reason for itself.

> **TESSERA abstracts memory architecture away from the agent. It does not replace the cognition of the agent.**

## Executive takeaway

The current Foundation already proves **stable identity, explainable retrieval, query-aware evidence, provenance and deterministic CI**. Before adding more intelligence, the next cycle hardens the public/product contract, makes indexing incremental and measurable, and starts external evaluation early.

Recent research refines later experiments without changing the product boundary:

```text
GraphMemix → query-aware graph expansion + evidence budget
CaSKG      → relation origin/confidence/validation
MemToC     → evidence arbitration + four-state evidence status
RENDER     → retrieval quality ≠ renderer quality
```

Those are **research signals and Test Cards**, not implemented capabilities.

---

# Product invariants

- Source text is the source of truth; index/cache/ledger are derived and rebuildable.
- TESSERA returns **structured evidence**, not the final answer for the consuming agent.
- Exactly **3 semantic drawers** remain: `facts`, `preferences`, `insights`.
- `document_type`, harness, scope, temporal state, authority, confidence, relations, quality and utility are facets/metadata — not new drawers.
- TESSERA is text-first and auditable; source code is not primary memory.
- No generative LLM is mandatory in the basic path.
- Retrieval relevance ≠ confidence ≠ authority ≠ relation confidence ≠ temporal validity ≠ utility.
- User source files are never silently rewritten during indexing.
- A relation existing ≠ the relation being trustworthy ≠ the relation being useful for the current query.
- A conflict being detected ≠ the conflict being resolved.
- Public docs, examples, fixtures and CI must remain project-agnostic.

---

# Delivery model: Issue → Test Card → PR → Evidence → Decision

Every meaningful change starts as a hypothesis, not as a presumed feature.

1. Open one **Issue/Test Card** for one unit of work or decision.
2. Record hypothesis, baseline, experiment, metrics and failure signals before implementation.
3. Open a linked PR (`Closes #...` when applicable).
4. Explain the PR at three levels: **Executive takeaway**, **plain language**, **technical implementation**.
5. Record real outputs, CI/benchmark evidence and learnings.
6. Update the changelog or explicitly mark the change as N/A according to #65/#66.
7. Record a decision: **KEEP / ITERATE / REVERT / DROP / DEFER**.
8. Follow-up work becomes a new Issue instead of a hidden TODO.

Templates:
- `.github/ISSUE_TEMPLATE/test-card.md`
- `.github/pull_request_template.md`

Documentation/governance tracker: **Issue #38**.

Plain-language stage records: [`docs/test-cards/`](test-cards/). Each meaningful
Test Card keeps an understandable before/after explanation alongside its
technical PR Evolution Audit. Open work remains explicitly planned or
in-progress until merge and validation evidence exist.

---

# Authoritative execution portfolio — audited 2026-08-31

This portfolio was reconciled through merged [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126)
and documentation Test Card [#109](https://github.com/LuigiFerronatto/TESSERA/issues/109)
against GitHub issue state, authoritative routing blocks, merged pull requests,
merge commits, evidence comments, versioned benchmark records, and the code on
`main` at `6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599`. Historical prose and emoji
markers are not status evidence.

## Status contract

| Status | Meaning |
|---|---|
| `IMPLEMENTED` | A merged runtime or contract exists on `main`. |
| `VALIDATED` | The implementation exists and its required tests or benchmark passed. |
| `READY` | Dependencies are closed and the Test Card satisfies Definition of Ready. |
| `IN_PROGRESS` | An active, unmerged pull request exists. |
| `BLOCKED` | An explicit dependency or owner decision remains unresolved. |
| `DEFERRED` | Work is intentionally postponed even though dependencies are satisfied. |
| `TRACKER` | Epic or coordination issue without a direct implementation PR. |
| `DROPPED` | The card was explicitly rejected. |
| `SUPERSEDED` | A newer issue, contract, or audit replaced the record. |

No open card currently qualifies as `DEFERRED` under the strict definition:
cards historically labeled deferred still have unresolved dependencies and are
therefore `BLOCKED` here.

## Reconciliation matrix

| Issue | Roadmap status | GitHub state | Routing status | Implementation evidence | Benchmark evidence | Corrected status |
|---|---|---|---|---|---|---|
| [#7](https://github.com/LuigiFerronatto/TESSERA/issues/7) | implemented | closed | historical Foundation | [PR #1](https://github.com/LuigiFerronatto/TESSERA/pull/1), [merge `83d716c`](https://github.com/LuigiFerronatto/TESSERA/commit/83d716c372b5cb7d7245f6f84fe959f4d6c4ee00), [decision](https://github.com/LuigiFerronatto/TESSERA/issues/7#issuecomment-5466934812) | contract tests | `VALIDATED` |
| [#8](https://github.com/LuigiFerronatto/TESSERA/issues/8) | implemented | closed | historical Foundation | [PR #2](https://github.com/LuigiFerronatto/TESSERA/pull/2), [merge `5590b1d`](https://github.com/LuigiFerronatto/TESSERA/commit/5590b1dfaf1fa29664b5ec497c1919f11876fcb0), [decision](https://github.com/LuigiFerronatto/TESSERA/issues/8#issuecomment-5466935654) | sanity fixture | `VALIDATED` |
| [#9](https://github.com/LuigiFerronatto/TESSERA/issues/9) | implemented | closed | historical Foundation | [PR #3](https://github.com/LuigiFerronatto/TESSERA/pull/3), [merge `4cbc585`](https://github.com/LuigiFerronatto/TESSERA/commit/4cbc5850960412e2e0f22970dd37225401eed563), [decision](https://github.com/LuigiFerronatto/TESSERA/issues/9#issuecomment-5466936601) | contract tests | `VALIDATED` |
| [#10](https://github.com/LuigiFerronatto/TESSERA/issues/10) | implemented | closed | historical Foundation | [PR #4](https://github.com/LuigiFerronatto/TESSERA/pull/4), [merge `6d9b194`](https://github.com/LuigiFerronatto/TESSERA/commit/6d9b194fa98817dda547002067ab7ab533b1bf86), [decision](https://github.com/LuigiFerronatto/TESSERA/issues/10#issuecomment-5466937517) | sanity fixture + CI | `VALIDATED` |
| [#11](https://github.com/LuigiFerronatto/TESSERA/issues/11) | implemented | closed | historical Foundation | [PR #6](https://github.com/LuigiFerronatto/TESSERA/pull/6), [merge `b3a1501`](https://github.com/LuigiFerronatto/TESSERA/commit/b3a1501eb193f379daaa57dcd18f896b36110982), [decision](https://github.com/LuigiFerronatto/TESSERA/issues/11#issuecomment-5466938428) | contract tests | `VALIDATED` |
| [#62](https://github.com/LuigiFerronatto/TESSERA/issues/62) | stale in-progress marker | closed | completed governance card | [PR #79](https://github.com/LuigiFerronatto/TESSERA/pull/79), [merge `aa02fad`](https://github.com/LuigiFerronatto/TESSERA/commit/aa02fad31935c3ec22d23b2099af269ae900d4ac), PR evidence/decision | not applicable | `IMPLEMENTED` |
| [#63](https://github.com/LuigiFerronatto/TESSERA/issues/63) | stale planned marker | closed | completed documentation card | [PR #82](https://github.com/LuigiFerronatto/TESSERA/pull/82), [merge `ffe76b3`](https://github.com/LuigiFerronatto/TESSERA/commit/ffe76b3cbabaf5ebe4978c03bdf7ea8bbb64a8f1), PR evidence/decision | not applicable | `IMPLEMENTED` |
| [#64](https://github.com/LuigiFerronatto/TESSERA/issues/64) | stale planned marker | closed | completed documentation card | [PR #81](https://github.com/LuigiFerronatto/TESSERA/pull/81), [merge `75eae59`](https://github.com/LuigiFerronatto/TESSERA/commit/75eae59d33bccbe1be51b31f33221e626e5e8264), PR evidence/decision | not applicable | `IMPLEMENTED` |
| [#65](https://github.com/LuigiFerronatto/TESSERA/issues/65) | stale planned marker | closed | completed governance card | [PR #84](https://github.com/LuigiFerronatto/TESSERA/pull/84), [merge `9012786`](https://github.com/LuigiFerronatto/TESSERA/commit/9012786e2112bf65a68892202fe34f3aef58d062), PR evidence/decision | not applicable | `IMPLEMENTED` |
| [#66](https://github.com/LuigiFerronatto/TESSERA/issues/66) | stale planned marker | closed | completed governance card | [PR #85](https://github.com/LuigiFerronatto/TESSERA/pull/85), [merge `864a38e`](https://github.com/LuigiFerronatto/TESSERA/commit/864a38e12277498b56eb9245b31a75dfc71b3b5e), PR evidence/decision | PR-contract tests | `VALIDATED` |
| [#68](https://github.com/LuigiFerronatto/TESSERA/issues/68) | planned | closed | stale “running” | [PR #98](https://github.com/LuigiFerronatto/TESSERA/pull/98), [merge `fb23012`](https://github.com/LuigiFerronatto/TESSERA/commit/fb23012ba4b2fddc3912d7cb593391a04fe45ae7), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/68#issuecomment-5471122707) | parity fixture + CI | `VALIDATED` |
| [#75](https://github.com/LuigiFerronatto/TESSERA/issues/75) | stale in-progress marker | closed | previous roadmap sync | [PR #76](https://github.com/LuigiFerronatto/TESSERA/pull/76), [merge `32a2aa6`](https://github.com/LuigiFerronatto/TESSERA/commit/32a2aa63db0024497cdee4cf16911cc3634770ca), PR evidence | not applicable | `SUPERSEDED` |
| [#92](https://github.com/LuigiFerronatto/TESSERA/issues/92) | M0 planned | closed | completed by [PR #108](https://github.com/LuigiFerronatto/TESSERA/pull/108); no dependencies | [merge `9ab03f7`](https://github.com/LuigiFerronatto/TESSERA/commit/9ab03f7a52bb63ef8942cc8bf292a51ea90e5b05), [KEEP Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/92#issuecomment-5479001151), [plain-language record](test-cards/92-write-gate-integrity.md), [PR Evolution Audit](PR_EVOLUTION_92.md) | `SMOKE_ONLY`; 241 local tests plus Python 3.9/3.12, smoke, sanity and reporting CI passed | `VALIDATED` |
| [#93](https://github.com/LuigiFerronatto/TESSERA/issues/93) | M0 active Test Card | open | [PR #129](https://github.com/LuigiFerronatto/TESSERA/pull/129); reconciled onto latest main `055a35f` (including canonical #115 architecture merge `b475f1c`); no dependencies | [plain-language record](test-cards/93-storage-configuration-parity.md), [PR Evolution Audit](PR_EVOLUTION_93.md), [KEEP evidence](https://github.com/LuigiFerronatto/TESSERA/issues/93#issuecomment-5483152212), 13-case golden/matrix suite; original `5d43a2d` hidden out-of-store scan reproduced | `SMOKE_ONLY`; 276 local tests; fresh PR checks required; LongMemEval skipped | `IN_PROGRESS` |
| [#94](https://github.com/LuigiFerronatto/TESSERA/issues/94) | planned | closed | completed bug card | [PR #101](https://github.com/LuigiFerronatto/TESSERA/pull/101), [merge `467ba64`](https://github.com/LuigiFerronatto/TESSERA/commit/467ba649f53312cedcecf40caf548af5f766c67b), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/94#issuecomment-5471509112) | smoke-only contract validation | `VALIDATED` |
| [#95](https://github.com/LuigiFerronatto/TESSERA/issues/95) | M0 candidate | closed | completed by [PR #126](https://github.com/LuigiFerronatto/TESSERA/pull/126); no dependencies | [canonical merge `6d4a32b`](https://github.com/LuigiFerronatto/TESSERA/commit/6d4a32b021dba7cbd7ac40244eaf6a6f7ce99599), [KEEP Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/95#issuecomment-5480777109), [plain-language record](test-cards/95-remove-legacy-runtime-coupling.md), [PR Evolution Audit](PR_EVOLUTION_95.md) | `SMOKE_ONLY`; 257 local tests; Python 3.9/3.12, smoke, sanity and reporting passed; LongMemEval dev-50 correctly skipped | `VALIDATED` |
| [#96](https://github.com/LuigiFerronatto/TESSERA/issues/96) | planned | closed | completed benchmark card | [PR #99](https://github.com/LuigiFerronatto/TESSERA/pull/99), [merge `812c3aa`](https://github.com/LuigiFerronatto/TESSERA/commit/812c3aa37b59a3e99135a9d8b39245aeb71356d0), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/96#issuecomment-5471323841) | [historical dev-50 record](../benchmarks/results/longmemeval-v1-dev-50/baseline.md) | `VALIDATED` |
| [#100](https://github.com/LuigiFerronatto/TESSERA/issues/100) | absent | closed | completed measurement card | [PR #102](https://github.com/LuigiFerronatto/TESSERA/pull/102), [merge `39febe3`](https://github.com/LuigiFerronatto/TESSERA/commit/39febe36f016997f0c54ede9824f15dec04cc1ee), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/100#issuecomment-5471939801) | [forward dev-50 record](../benchmarks/results/longmemeval-v1-dev-50/forward.md) + conditional CI | `VALIDATED` |
| [#67](https://github.com/LuigiFerronatto/TESSERA/issues/67) | planned | open | #92 and #95 are satisfied; still depends on #93 and regression-gate integration | test shell may start; final gate absent | reporting CI exists, full Quality Gate v2 does not | `BLOCKED` |
| [#74](https://github.com/LuigiFerronatto/TESSERA/issues/74) | planned | closed | completed architecture decision | [PR #107](https://github.com/LuigiFerronatto/TESSERA/pull/107), [merge `0c0b638`](https://github.com/LuigiFerronatto/TESSERA/commit/0c0b6385f67ff5451d8a6884f3b7764cb4b7e4e2), [accepted ADR 0001](adr/0001-core-vs-optional-llm-boundary.md), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/74#issuecomment-5472168701) | not applicable; docs/contract only | `VALIDATED` |
| [#109](https://github.com/LuigiFerronatto/TESSERA/issues/109) | absent | closed | completed documentation/governance card | [PR #110](https://github.com/LuigiFerronatto/TESSERA/pull/110), [merge `7f92dd9`](https://github.com/LuigiFerronatto/TESSERA/commit/7f92dd95584aa1f3adf57d47080853bf2e289087) | not applicable | `IMPLEMENTED` |
| [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) | untracked runtime branding defect | closed | completed branding correction | [PR #113](https://github.com/LuigiFerronatto/TESSERA/pull/113), [merge `a80a5f1`](https://github.com/LuigiFerronatto/TESSERA/commit/a80a5f19671a002e6ec2ed1846d041afb090b7a2), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/112#issuecomment-5473210880) | Python 3.9/3.12 + smoke + sanity + reporting | `VALIDATED` |
| [#114](https://github.com/LuigiFerronatto/TESSERA/issues/114) | absent | closed | completed governance contract | [PR #123](https://github.com/LuigiFerronatto/TESSERA/pull/123), [merge `a79b5ae`](https://github.com/LuigiFerronatto/TESSERA/commit/a79b5aec661f0d401b00c2985eff3a5a24363943), [Evidence/Learnings/Decision](https://github.com/LuigiFerronatto/TESSERA/issues/114#issuecomment-5473270634) | contract tests + Python 3.9/3.12 + smoke + sanity + reporting | `VALIDATED` |
| [#115](https://github.com/LuigiFerronatto/TESSERA/issues/115) | absent | closed | completed by [PR #128](https://github.com/LuigiFerronatto/TESSERA/pull/128); [ADR 0002](adr/0002-repository-layout-and-distribution-boundary.md) accepted with `KEEP` | [canonical squash merge `b475f1c`](https://github.com/LuigiFerronatto/TESSERA/commit/b475f1cd805f86cc8ad9526e563e3c6fb8409ff1), [post-merge audit](https://github.com/LuigiFerronatto/TESSERA/issues/115#issuecomment-5483321070), [plain-language record](test-cards/115-repository-layout-architecture.md), [PR Evolution Audit](PR_EVOLUTION_115.md); architecture accepted, migrations unimplemented | implementation `SMOKE_ONLY`; lifecycle synchronization `NOT_APPLICABLE` | `VALIDATED` |
| [#116](https://github.com/LuigiFerronatto/TESSERA/issues/116) | absent | open | #74, #95 and canonical #115 are satisfied; packaging hardening may start after this lifecycle synchronization lands | #115 proves benchmark packages are accidentally shipped and tests are partially in sdist; no packaging migration has started | smoke-only when executed | `READY` |
| [#117](https://github.com/LuigiFerronatto/TESSERA/issues/117) | absent | open | depends on #94, #115 and #116 | no project/global discovery schema or `tessera init` contract | smoke-only when executed | `BLOCKED` |
| [#118](https://github.com/LuigiFerronatto/TESSERA/issues/118) | absent | open | depends on #116 and #117 | checkout CI exists; clean wheel install/bootstrap gate absent | smoke-only when executed | `BLOCKED` |
| [#119](https://github.com/LuigiFerronatto/TESSERA/issues/119) | absent | open | depends on #112, #116 and #117 | banner corrected; complete CLI UX/output audit absent | smoke-only when executed | `BLOCKED` |
| [#120](https://github.com/LuigiFerronatto/TESSERA/issues/120) | absent | open | depends on #68, #74, #92, #116 and #117 | direct-query parity exists; eager optional initialization and protocol gaps remain | smoke-only unless retrieval changes | `BLOCKED` |
| [#121](https://github.com/LuigiFerronatto/TESSERA/issues/121) | absent | open | depends on #68, #92, #116, #117 and #120 | bundled Markdown library exists; official versioned integration Skills absent | smoke-only when executed | `BLOCKED` |
| [#16 containment](https://github.com/LuigiFerronatto/TESSERA/issues/16) | one undifferentiated planned card | open | containment has no dependencies | current silent heuristic is documented; containment PR absent | regression fixture required | `READY` |
| [#16 full](https://github.com/LuigiFerronatto/TESSERA/issues/16) | one undifferentiated planned card | open | depends on #15, #73 and #96 | existing heuristic is baseline only | dev-50 available | `BLOCKED` |
| [#18](https://github.com/LuigiFerronatto/TESSERA/issues/18) | planned capability | open | active epic; tracks #96, #100, #28, #103–#106 | no direct implementation PR by design | V1 dev-50 is available through children | `TRACKER` |
| [#28](https://github.com/LuigiFerronatto/TESSERA/issues/28) | planned | open | stale “blocked”; authoritative dependencies #68 and #96 are closed | evidence renderer evaluation not started | frozen retrieval baseline available | `READY` |
| [#103](https://github.com/LuigiFerronatto/TESSERA/issues/103) | absent | open | depends on #28, #74, #96 and #100 | no implementation PR | dev-50 retrieval inputs available; renderer/ADR pending | `BLOCKED` |
| [#104](https://github.com/LuigiFerronatto/TESSERA/issues/104) | absent | open | depends on #74, #100 and #103 | no implementation PR | judge protocol not implemented | `BLOCKED` |
| [#105](https://github.com/LuigiFerronatto/TESSERA/issues/105) | absent | open | depends on #96, #100, #103 and #104 | no implementation PR | full-500 not run | `BLOCKED` |
| [#106](https://github.com/LuigiFerronatto/TESSERA/issues/106) | absent | open | depends on #74, #100, #103, #104 and #105 | no implementation PR | V2 not installed or run | `BLOCKED` |
| [#12](https://github.com/LuigiFerronatto/TESSERA/issues/12) | planned | open | depends on #67 and #94 | current rebuild/cache behavior is only the baseline | dev-50 available | `BLOCKED` |
| [#69](https://github.com/LuigiFerronatto/TESSERA/issues/69) | planned | open | depends on #94 and #12 | Markdown-only contract exists; broader text ingestion absent | dev-50 available | `BLOCKED` |
| [#70](https://github.com/LuigiFerronatto/TESSERA/issues/70) | planned | open | depends on #12 and #69 | structural segmentation absent | dev-50 available | `BLOCKED` |
| [#13](https://github.com/LuigiFerronatto/TESSERA/issues/13) | planned | open | depends on #12, #69 and #70 | installation doctor is not corpus doctor | benchmark reporting exists | `BLOCKED` |
| [#73](https://github.com/LuigiFerronatto/TESSERA/issues/73) | planned | open | depends on #12 and #94 | source hashes exist; revision history absent | dev-50 available | `BLOCKED` |
| [#14](https://github.com/LuigiFerronatto/TESSERA/issues/14) | planned capability | open | epic for #25 and #26 | no direct implementation PR by design | dev-50 available | `TRACKER` |
| [#25](https://github.com/LuigiFerronatto/TESSERA/issues/25) | planned | open | dependency #96 is closed, but operational DoR is incomplete | current one-hop/DWPR is the baseline; exact executable baseline/rollback gate still needs owner confirmation | dev-50 available | `BLOCKED` |
| [#26](https://github.com/LuigiFerronatto/TESSERA/issues/26) | planned | open | depends on #96 and frozen #25 baseline | edge-confidence candidate absent | dev-50 available | `BLOCKED` |
| [#15](https://github.com/LuigiFerronatto/TESSERA/issues/15) | planned | open | depends on #73 and #96 | temporal fields are baseline, not validated temporal semantics | dev-50 available | `BLOCKED` |
| [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) | planned | open | depends on #69 and #70 | adapter registry absent | synthetic fixtures pending | `BLOCKED` |
| [#32](https://github.com/LuigiFerronatto/TESSERA/issues/32) | planned | open | depends on #71 | policy candidate absent | benchmark pending | `BLOCKED` |
| [#72](https://github.com/LuigiFerronatto/TESSERA/issues/72) | planned | open | depends on #71 and #32 | deterministic resolver absent | benchmark pending | `BLOCKED` |
| [#27](https://github.com/LuigiFerronatto/TESSERA/issues/27) | planned | open | depends on #15, #16, #32, #72 and #96 | arbitration absent | dev-50 alone is insufficient | `BLOCKED` |
| [#20](https://github.com/LuigiFerronatto/TESSERA/issues/20) | planned | open | depends on #15, #16, #27 and #96 | sufficiency/abstention classifier absent | abstention retrieval metric only | `BLOCKED` |
| [#19](https://github.com/LuigiFerronatto/TESSERA/issues/19) | planned | open | #92 is satisfied; still depends on #13, #16 and #73 | truthful deterministic write gate exists; evidence-aware admission absent | admission benchmark pending | `BLOCKED` |
| [#17](https://github.com/LuigiFerronatto/TESSERA/issues/17) | planned/deferred | open | depends on #20, #74 and #96 | current hard-coded intent heuristics are baseline | dev-50 available | `BLOCKED` |
| [#21](https://github.com/LuigiFerronatto/TESSERA/issues/21) | planned/deferred | open | depends on #19, #20 and #96 | utility-feedback runtime absent | benchmark pending | `BLOCKED` |
| [#38](https://github.com/LuigiFerronatto/TESSERA/issues/38) | active documentation program | open | epic/tracker | child documentation PRs only | not applicable | `TRACKER` |

## Completed and validated capabilities

- `VALIDATED` — Foundation output, canonical identity, explainable ranking,
  evidence extraction, deterministic CI, and Evidence Ledger (#7–#11).
- `VALIDATED` — lossless Engine/CLI/MCP direct-query parity (#68).
- `VALIDATED` — Markdown-only persistence contract with pre-mutation rejection
  of unsupported formats (#94).
- `VALIDATED` — truthful, path-contained deterministic write admission with
  cross-surface parity and zero-side-effect rejection/review (#92).
- `VALIDATED` — reproducible LongMemEval V1 retrieval-only dev-50 adapter and
  historical baseline (#96).
- `VALIDATED` — versioned benchmark ledger, immediate-parent gate, canonical
  comparison, forward environment fingerprint, and conditional CI (#100).
- `IMPLEMENTED` — project-agnostic public surface, README/brand, changelog, and
  PR governance contracts (#62–#66).
- `VALIDATED` — deterministic-core vs optional-LLM responsibility boundary
  accepted in ADR 0001 (#74). Runtime migration remains follow-up work.

## Benchmark capabilities: keep the two baselines separate

| Benchmark | Purpose | Scope | Record | Status |
|---|---|---|---|---|
| deterministic sanity fixture | fast regression alarm for core retrieval | synthetic corpus; Hit@1/3/5, MRR, evidence hit rate | [`benchmarks/sanity`](../benchmarks/sanity/) | `VALIDATED` through #10 |
| LongMemEval V1 dev-50 historical | frozen retrieval-only experiment introduced by #96 | deterministic 50-question subset; not answer quality or full-500 | [baseline record](../benchmarks/results/longmemeval-v1-dev-50/baseline.md) | `VALIDATED` |
| LongMemEval V1 dev-50 forward | candidate-vs-parent merge gate and dependency-drift reference from #100 | same frozen retrieval profile plus environment fingerprint | [forward record](../benchmarks/results/longmemeval-v1-dev-50/forward.md) | `VALIDATED` |
| LongMemEval V1 full-500 | preregistered retrieval/reader/judge execution | all 500 questions | #105 | `BLOCKED` |
| LongMemEval V2 | separate multimodal trajectory-memory protocol | V2 small tier first | #106 | `BLOCKED` |

The sanity fixture and LongMemEval dev-50 are not interchangeable. Dev-50 is a
development retrieval profile, not an official full benchmark or an
answer-quality result.

## Current critical path, M0 through M5

```text
M0  IN_PROGRESS #93 + READY #16 containment
      └─ validated foundations: #68 + #74 + #92 + #94 + #95 + #96 + #100
      ↓
    #67 Quality Gate v2
      ↓
M1  READY #28 rendering ablation
      → #103 frozen-evidence reader
      → #104 calibrated judge
      → #105 V1 full-500
      → #106 V2 (separate protocol)
      ↓
M2  #12 incremental indexing
      → #69 text ingestion
      → #70 structural segmentation
      → #13 corpus doctor
      → #73 revision history
      ↓
M3  #25 graph-expansion card DoR completion
      → #26 relation confidence
      └─ #14 tracker aggregates decisions
      ↓
M4  #73 → #15 temporal model
    #69/#70 → #71 → #32 → #72
    #15 + #16 full + #32/#72 → #27 arbitration
      → #20 sufficiency/abstention
      ↓
M5  #92/#13/#16/#73 → #19 admission
    #20 + merged #74 ADR + #96 → #17 adaptive retrieval
    #19 + #20 + #96 → #21 learning/utility
```

Execution policy:

- #14, #18 and #38 are `TRACKER`s and do not produce direct implementation PRs.
- #28 is newly `READY`; readiness does not authorize execution beyond the
  two-card WIP limit. #25 has a satisfied issue dependency but remains `BLOCKED`
  until its operational Definition of Ready is explicit.
- M0 safety bugs and the #16 containment remain ahead of experimental feature
  work. #74 is completed through accepted ADR 0001; its runtime deviations
  remain follow-up work.
- Policy (#32) precedes resolver (#72); retrieval candidates, sufficiency,
  reader confidence, and final abstention remain separate responsibilities.
- Feature cards depend on the benchmark harness; benchmark reruns are evidence,
  never reverse dependencies.
- See [TEST_CARD_OPERATING_MODEL.md](TEST_CARD_OPERATING_MODEL.md) for the full
  Definition of Ready, stop conditions, and handoff contract.

## Active write-safety evolution

```text
existing deterministic write gate
→ Markdown-only persistence integrity (#94 / PR #101)
→ deterministic-core boundary (#74 / PR #107)
→ truthful detection/transformation/admission plus path containment (#92 / PR #108 / merge `9ab03f7`, VALIDATED)
→ future State Contamination evaluation (#19, still BLOCKED)
```

#92 and #95 now satisfy their required dependency edges for #67; #92 also
satisfies only its own prerequisite for #19. #67 remains `BLOCKED` on #93 and
regression-gate integration; #19 remains blocked on #13, #16 and #73. No
unrelated readiness state changes.

## Productization and integration lane

This lane improves how TESSERA is packaged, discovered and consumed. It runs
alongside the memory-quality roadmap; it does not replace the M0 safety gates or
claim new retrieval intelligence.

```text
#114 auditable templates
  ↓
#95 generic runtime / explicit compatibility (VALIDATED)
  ↓
#115 repository-layout ADR (READY)
  ↓
#116 clean Python distribution (BLOCKED until #115)
  ↓
#117 project/global configuration and tessera init (BLOCKED)
  ├─ #118 clean install + CI onboarding (BLOCKED)
  ├─ #119 CLI experience (BLOCKED)
  └─ #120 MCP robustness (BLOCKED)
       ↓
     #121 official TESSERA Skills (BLOCKED)
```

The repository already declares a Python package. #116 is therefore distribution
hardening, not a claim that no library exists. #115 must classify every candidate
before deletion; names such as `legacy` or `archive` are not sufficient
evidence. #117 treats global state as a registry of named stores, never as silent
cross-project memory merging.

---

# Superseded execution order — historical reference

> The sequence below predates the 2026-08-30 portfolio audit and is retained only to explain earlier roadmap assumptions. Use the authoritative execution portfolio above and the routing block in each open issue.

```text
PUBLIC FOUNDATION / GOVERNANCE
  #62 Project-agnostic public surface
      ↓
  #63 README vNext
  #64 Visual assets
      ↓
  #65 CHANGELOG policy
      ↓
  #66 PR contract v2
      ↓
  #67 CI Quality Gate v2
      ↓
FOUNDATION CONTRACT
  #68 Engine / CLI / MCP contract parity
      ↓
INDEXING / INGESTION
  #12 Incremental & Idempotent Indexing
      ↓
  #69 Text ingestion coverage
      ↓
  #70 Structural segmentation
      ↓
  #13 Metadata Doctor
      ↓
MEASURE EARLY
  #18 LongMemEval baseline / adapter
    └─ #28 Renderer control starts here
      ↓
RELATIONS ABLATIONS
  #14 Typed Relations / controlled expansion
    ├─ #25 Query-aware evidence budget
    └─ #26 Relation confidence / validation
      ↓
TEMPORAL + INSTRUCTIONS
  #15 Temporal Model + State Keys
  #71 Harness Adapter Registry
  #72 Instruction Resolver
  #32 Authority / scope / precedence
  #73 Revision history
      ↓
CONFLICT / TRUST
  #16 Conflict / Supersession
    └─ #27 Evidence Arbitration
      ↓
ADAPTIVE
  #17 Query Compiler / Adaptive Retrieval
  #74 Core vs optional LLM orchestrator
  #19 Memory Admission
      ↓
STATE / ABSTENTION
  #20 State Reconstruction + four-state evidence status
      ↓
LEARNING
  #21 Experience + Utility
```

The ordering is not a claim that every capability will ship. Each feature must earn **KEEP** through its Test Card.

---

# Research-derived experiment map

| Research signal | TESSERA Test Card | Question we measure |
| --- | --- | --- |
| GraphMemix | #25 | Does query-aware/budgeted expansion outperform indiscriminate 1-hop in quality/cost? |
| CaSKG | #26 | Does relation confidence/validation reduce harmful expansion without destroying recall? |
| MemToC | #27 | Does Evidence Arbitration improve source selection and abstention versus a silent winner? |
| MemToC | #20 | Do `sufficient / insufficient / conflicting / ambiguous` improve downstream control flow? |
| MemToC + harness scope | #32/#72 | Do authority + scope + precedence resolve instructions better than newest/relevance wins? |
| RENDER | #28 | Does reader-facing rendering change downstream QA when the evidence set is frozen? |

### Relations: four dimensions that must stay separate

```text
relation_type
→ what the relation means

relation_origin
→ where the relation came from

relation_confidence
→ how strongly we believe the edge is correct

query_relevance
→ whether the edge is useful for this query
```

### Future evidence-status contract

```text
sufficient
→ continue

insufficient
→ search / expand

conflicting
→ inspect provenance / arbitration

ambiguous
→ verify / ask / tool call
```

TESSERA provides infrastructure signals; the consuming agent keeps the final cognitive decision.

---

# Foundation pipeline — what exists today

```text
TEXT FILES
   ↓
① DISCOVER
   ↓
② UNDERSTAND
   ├── document type
   ├── metadata
   ├── scope
   └── semantic drawer
   ↓
③ NORMALIZE
   ├── explicit metadata
   ├── inferred metadata
   └── stable identity
   ↓
④ TRACE
   ├── source
   ├── spans
   ├── hashes
   └── Evidence Ledger
   ↓
⑤ CONNECT
   ├── explicit links
   ├── relations
   └── graph
   ↓
⑥ INDEX
   └── current rebuild/cache behavior
   ↓
⑦ RETRIEVE
   ├── candidates
   ├── explainable ranking
   └── relevant evidence
   ↓
⑧ RETURN
   └── structured evidence + provenance
   ↓
CONSUMING AGENT
```

Incremental/idempotent behavior at step ⑥ is still #12. Plain-text coverage and structural segmentation are still #69/#70. They must not be described as implemented before their Test Cards close.

---

# Target pipeline — only if the Test Cards are KEEP

```text
QUERY
  ↓
Candidate Retrieval
  ↓
Seed Evidence
  ↓
Query-Aware Graph Expansion
  ↓
Relation Type / Origin / Confidence
  ↓
Temporal Validity + State Keys
  ↓
Authority / Scope / Instruction Resolution
  ↓
Conflict Detection
  ↓
Evidence Arbitration
  ↓
Evidence Status
  ├── sufficient
  ├── insufficient
  ├── conflicting
  └── ambiguous
  ↓
Renderer
  ├── RAW
  ├── EVIDENCE
  └── STRUCTURED
  ↓
CONSUMING AGENT
```

This is **target architecture**, not a description of `main` today.

---

# Current retrieval baseline

The deterministic CI sanity suite currently protects:

- Hit@1: **75%**
- Hit@3: **100%**
- Hit@5: **100%**
- MRR: **0.875**
- Evidence hit rate: **100%**

This is a **regression alarm**, not a competitive benchmark. A known paraphrase case can still place the gold memory at #2 rather than #1; that failure remains visible until semantic/adaptive retrieval proves a general improvement through #18/#17 rather than query-specific tuning.

---

# Documentation / research layer

Current-reference docs:

- `docs/OVERVIEW.md` — executive + colloquial + technical overview.
- `docs/FEATURES.md` — implemented capability catalog.
- `docs/CONCEPTS.md` — canonical vocabulary and semantic distinctions.
- `docs/ARCHITECTURE.md` — current architecture and explicit future boundaries.
- `docs/OUTPUT_CONTRACT.md` — structured retrieval semantics.
- `docs/QUERY_EXAMPLES.md` — usage examples and clearly marked future targets.
- `docs/research/REFERENCES.md` — primary research/product sources.
- `docs/research/PAPER_NOTES.md` — source claim → TESSERA learning → Test Card.
- `docs/research/COMPETITIVE_LANDSCAPE.md` — version-aware competitor comparison.
- `docs/research/DECISION_TRACE.md` — source → insight → issue → decision trace.

Program tracker: #38.

---

# GitHub Project fields recommended

The GitHub Projects v2 board should mirror Issues/Test Cards rather than become a second source of truth:

- `Phase`: Foundation / Intelligence / Adaptive / Evaluation / State / Learning
- `Status`: Backlog / Ready / In Progress / Measuring / Decision / Done / Dropped
- `Decision`: Pending / Keep / Iterate / Revert / Drop / Defer
- `Test Card`: Draft / Ready / Updated
- `Impact`: Low / Medium / High / Transformational
- `Evidence`: Missing / Partial / Sufficient
- `Benchmark Gate`: N/A / Pending / Pass / Fail
- `PR`: linked PR

Operational note: Issues + versioned roadmap files remain the source of truth. The board is a visualization of those records.
