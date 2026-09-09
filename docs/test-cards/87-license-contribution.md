# #87 — License and contribution entrypoints

| Field | Value |
|---|---|
| Issue | [#87](https://github.com/LuigiFerronatto/TESSERA/issues/87) |
| Record status | `VALIDATED` |
| Capability type | Repository governance / packaging metadata |
| Pull request | [#233](https://github.com/LuigiFerronatto/TESSERA/pull/233), merged 2026-09-09 |
| Final candidate | `c27ede1b6552e9a2b3a0f51a41185c558186e895` |
| Merge commit | `d473f230b914908fcaad3a46291b5046bde6b918` |
| Decision | `KEEP`; owner confirmation, exact-head audit and canonical CI/Benchmark passed |
| Benchmark applicability | `NOT_APPLICABLE`; runtime and retrieval unchanged |
| Last audited | 2026-09-09; canonical main `d473f230b914908fcaad3a46291b5046bde6b918` |

## In one sentence

A contributor can find the project's license and contribution workflow, and an
installed distribution carries the same license text as the repository.

## What problem existed?

The package declared MIT without a standalone LICENSE file. The README said a
contribution guide would come later. Built wheel/sdist metadata named MIT but
contained no License-File entry or license text.

## How did TESSERA behave before?

Runtime, packaging boundaries and the installed onboarding/MCP contracts were
already validated. Neither package authors nor the repository account established
copyright ownership. #134 remained blocked on the owner's #87 decision.

## What changed or is being tested?

The candidate adds the standard MIT text, a concise CONTRIBUTING.md, README links,
an explicit `project.license-files = ["LICENSE"]` declaration and distribution
checks for byte-identical license payloads and metadata. The sdist includes the
contribution guide; the wheel contains the runtime plus its license metadata.

The owner confirmed the presented MIT proposal and notice
**Copyright (c) 2026 Luigi Ferronatto** on 2026-09-09 with “Confirmo a adocao!”.
The [recorded decision](https://github.com/LuigiFerronatto/TESSERA/issues/87#issuecomment-5607594368)
satisfies #87's explicit owner prerequisite. The license bytes are unchanged;
this records the owner's decision, not an independent ownership determination.

## How does it work now?

Setuptools includes LICENSE in the sdist and in the wheel's
`.dist-info/licenses/` directory, and declares MIT / License-File in both
metadata files. CI checks the actual archives on Python 3.9/3.12 and then reads
the installed license outside the checkout. Existing runtime smoke checks remain.

## Concrete example

After installing the built wheel, `importlib.metadata.distribution("tessera")`
exposes `License-Expression: MIT`, `License-File: LICENSE` and the same text through
`read_text("licenses/LICENSE")`. A README reader follows CONTRIBUTING.md to the
existing Test Card, PR, benchmark and change-policy contracts.

## How was it validated?

Isolated baseline and candidate builds each rebuild the wheel from the sdist.
The baseline has 34 wheel / 44 sdist entries and no license payload; the candidate
has 35 / 46 entries. All 29 runtime/package-data files are byte-identical.
The actual CI archive-inspection block passes locally, as does license metadata
inspection in a fresh wheel-only environment outside the checkout. Full runtime
installation and protocol proof remain existing CI gates.

See [versioned evidence](../evidence/87-license/validation.json) and
[evolution audit](../PR_EVOLUTION_87.md). Technical checks do not confirm ownership.

## What improved?

The license accompanies distributed copies, and contributor instructions point
to existing repository contracts instead of duplicating them.

## What remains unimplemented?

The canonical merge and lifecycle validation are complete. There is no PyPI
publication, release workflow,
package rename, version bump, CLA/DCO introduction, runtime change or automatic
selection of #121. Existing third-party notices remain with their files.

## What is unlocked next?

#134 is now the next release gate. Release engineering and publication follow
#134's own gates; no publication is authorized by this card.

## Technical provenance

| Item | Evidence |
|---|---|
| Discovered gap | #86 README v3 / PR #88 |
| Packaging baseline | #116 / PR #131, `0dd6e5c8c3e720cc39b1e666abed98a9fa3357e4` |
| Canonical starting point | #232, `31df35e2885bcb81efbe3b9f87fdf8b15a858a4b` |
| MIT text | [Open Source Initiative](https://opensource.org/license/mit) |
| License-file metadata | [PyPA specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/) |

## Evolution

```text
MIT metadata, missing repository/distribution license and contribution guide
-> #87 owner-confirmed proposal, IN_PROGRESS / NOW / Queue 6
-> exact-head review -> canonical merge `d473f230...` -> VALIDATED / KEEP
-> #134 release gate becomes eligible for its own validation
```
