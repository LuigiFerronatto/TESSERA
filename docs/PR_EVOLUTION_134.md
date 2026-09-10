# PR Evolution Audit — #134 PyPI release (R0/R1)

## Canonical lifecycle

- Issue: #134; reopened by the maintainer after merge; status `IN_PROGRESS`;
  decision pending (`KEEP` inherited for the merged R0/R1 scope only).
- Branch: `test-card/134-pypi-release`.
- Final candidate: `2472f47d52d63afc9a7aa8135bb0b889cfc47198`.
- Canonical squash merge: `bcc371045c226dde13138eadd451c4e14de5b33e`,
  merged by the maintainer on 2026-09-10 via [PR #237](https://github.com/LuigiFerronatto/TESSERA/pull/237).
- Candidate and canonical merge deliver the same tree: one runtime/tooling
  delivery. Benchmark applicability: `SMOKE_ONLY` (release packaging and
  external-install workflow; no retrieval/ranking code touched).

## Scope of this delivery

This PR implements only Release phases **R0 (metadata freeze)** and
**R1 (release workflow authoring)** from #134's Definition of Done:

- froze the public PyPI distribution name `tessera-agent-memory`;
- froze the first public version line `0.0.1`;
- added `.github/workflows/release.yml` (tag-triggered build job with no
  `id-token: write`, plus a separate `publish` job scoped to
  `id-token: write` and gated by the protected `pypi` GitHub Environment,
  using `pypa/gh-action-pypi-publish` Trusted Publishing);
- updated `tessera-ci.yml`, `scripts/clean_room/check_installed.py`,
  `tests/test_packaging_contract.py` and added
  `tests/test_release_workflow.py` to assert the new name/version/workflow
  contract;
- updated `README.md`, `docs/MCP_RUNTIME.md`,
  `docs/COMO-FUNCIONA-E-PROXIMOS-PASSOS.md` and
  `docs/test-cards/87-license-contribution.md` install references;
- added the required `CHANGELOG.md` `Unreleased` entry for the distribution
  name/version decision.

`import tessera` and the `tessera` CLI/entry points are unchanged.

## What remains outstanding (why #134 stays open / `IN_PROGRESS`)

Per #134's own Definition of Done, this PR does **not** perform:

- R2 — TestPyPI publication and clean remote-install proof;
- R3 — production PyPI gate (explicit maintainer approval);
- R4 — production PyPI publication;
- R5 — post-publication real-world clean-install smoke.

No PyPI upload or credential access occurred during this PR's review. The
maintainer reopened #134 immediately after merging #237, explicitly noting
that TestPyPI validation, production publication and post-publication smoke
remain outstanding.

## Evidence

- Focused packaging, release-security, governance and documentation checks:
  79 passed, 5 skipped (declared in the PR body).
- Independent audits on earlier heads: ITERATE (missing CHANGELOG entry,
  `de930702...`), BLOCK (CI incomplete/draft, `2f6820cb...`, `2472f47d...`).
  The CHANGELOG gap was resolved before merge.
- PyPI name availability (`tessera-agent-memory`) was rechecked live as
  HTTP 404 immediately before this PR; this is an availability observation,
  not a reservation, and must be rechecked again before any upload.

## Findings and classification

| Finding | Classification | Resolution |
|---|---|---|
| First candidate head lacked a `CHANGELOG.md Unreleased` entry for a user-visible install/version change | `IN_SCOPE_FIX` | Added the required entry before merge |
| PR merged while release publication (R2–R5) is still outstanding | `EXPECTED` | Maintainer reopened #134 rather than closing it, to keep the release gate open until publication evidence exists |

## Decision

**IMPLEMENTED (R0/R1 only) — not `VALIDATED`**: the frozen name/version and
protected release workflow are canonically merged on `main` and covered by
CI, but #134 cannot be marked `VALIDATED` or closed until TestPyPI proof,
production publication and post-publication smoke exist. This lifecycle
correction does not perform any of the outstanding release phases.

## Scope and downstream routing

No downstream issue's blocker changes as a result of this merge: #134 was
already the terminal node of the FASE 2 / "first public release" dependency
chain, and its own remaining gates (TestPyPI, production publish, smoke) are
unaffected by any other issue. No implementation, publication, tag, or
release execution is authorized by this lifecycle PR.
