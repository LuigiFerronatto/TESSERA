# PR Evolution Audit — #87 legal and contribution entrypoints

## Candidate lifecycle

- Issue #87: OPEN / IN_PROGRESS, NOW / Queue 6, selected by the owner's request.
- Starting main: `31df35e2885bcb81efbe3b9f87fdf8b15a858a4b` (#232 merged; #231 closed).
- Branch: `test-card/87-license-contribution`; draft, not merged.
- Classification: repository governance and packaging metadata.
- Benchmark: `NOT_APPLICABLE`; no runtime, retrieval, corpus or benchmark change.
- Owner confirmation: **PENDING**. Proposed MIT notice:
  `Copyright (c) 2026 Luigi Ferronatto`. It is a review proposal, not ownership
  inferred from Git history, package authors, or account identity.
- #134 remains BLOCKED by #87. No legal completion or release authorization is claimed.

## Relevant delivery history

| Delivery | Canonical commit | Capability consumed / gap retained |
|---|---|---|
| #86 / #88 README v3 | `2d7ffc9b09249328ea90bdaf7e48f1b0274566d6` | Developer-facing README; standalone license and contribution guide deferred to #87 |
| #116 / #131 packaging | `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4` | Explicit runtime-only distribution, MIT SPDX expression; owner/legal decision stayed separate |
| #118 / #225 onboarding | `0ee5bbfe3a4b6cd9ecbcbfbcfdbfa65620700c3d` | Clean Python 3.9/3.12 artifact and source-integrity proof |
| #120 / #229 MCP | `b4ead4d7407b8caa2571e1e366616a468f2ef74f` | Installed stdio and runtime ownership contracts |
| #231 / #232 lifecycle | `31df35e2885bcb81efbe3b9f87fdf8b15a858a4b` | Canonical #120 validation; #87 is next owner decision, #134 still blocked |

There is no previous root LICENSE or CONTRIBUTING.md delivery in the audited
history. `authors = [{name = "TESSERA Contributors"}]` and the existing MIT
expression do not establish who owns copyright. Third-party notices in separate
site/vendor content are preserved; no submodule or vendor license is rewritten.

## Scope and implementation

- LICENSE: standard [MIT text](https://opensource.org/license/mit), with the notice
  proposed above for explicit confirmation before merge.
- CONTRIBUTING.md: setup, tests, Issue/Test Card, PR, benchmark, change policy and
  existing lifecycle/review links; no new contributor agreement or duplicated
  architecture contract.
- README: links to both real files; no claim of publication.
- Packaging: keep MIT expression and add standard `project.license-files`, already
  supported by the existing setuptools >=77 baseline. Include the guide in the
  sdist. No dependency, import, CLI, MCP, package name or version change.
- CI: check wheel/sdist metadata and exact license bytes, retain archive ownership
  and installed runtime smoke checks, and verify the installed license outside
  the checkout. The existing Python 3.9/3.12 matrix is unchanged.
- Lifecycle: #87 is IN_PROGRESS / ADMIN / NOW / Queue 6; no executable runtime WIP
  is added. The blocked matrix count drops by one because this owner-requested
  card is now in progress; #134 stays blocked, and #121 stays LATER / Queue 43.

## Technical evidence

[Versioned evidence](evidence/87-license/validation.json) binds the actual built
archives and installed metadata to the license hash. Both builds use
`python -m build`, including an isolated wheel rebuild from the sdist.

| Contract | Baseline | Candidate |
|---|---|---|
| MIT expression | Present | Preserved |
| Wheel License-File and payload | Absent | LICENSE, bytes equal repository |
| Sdist license and guide | Absent | Both included, bytes equal repository |
| Wheel inventory | 34 entries | 35 entries |
| Sdist inventory | 44 entries | 46 entries |
| Runtime/package-data payload | 29 files | All 29 byte-identical |
| Owner confirmation | Missing | Still pending; not inferred from technical success |

The actual CI archive-inspection block passes against the isolated candidate
build. A fresh venv installs the wheel with `--no-deps` for metadata-only
inspection: MIT, License-File and installed license bytes match. This is distinct
from the existing full installed-runtime Python 3.9/3.12 proof in CI.

Local packaging, documentation, governance and routing checks passed: **157 passed,
5 skipped**. Compileall, diff checks and the new relative documentation links also
passed. Technical results and exact-head remote gates are attached to the PR. They do not
constitute legal approval, final KEEP, canonical delivery or #134 readiness.

## Remaining decisions

The owner must confirm the license text and exact copyright holder/year before
merge. If the notice changes, rebuild the artifact proof and rerun exact-head CI
and audit. After approved merge, record the canonical SHA and reconcile #87;
only then reassess #134 under its separate release gates. No publication, legal
ownership determination, CLA/DCO policy or downstream implementation is included.
