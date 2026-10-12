# #71 — Isolate instruction formats behind a deterministic registry

| Field | Value |
|---|---|
| Issue | [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) |
| Record status | `IMPLEMENTED` |
| Capability type | `runtime` |
| Pull request | [#289](https://github.com/LuigiFerronatto/TESSERA/pull/289) |
| Merge commit | `f149ff292238e2a6f5cdd95894e9c11c365457f2` |
| Decision | `PENDING` lifecycle decision; no final-head formal review recorded |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-12 |

## In one sentence
Recognize textual instruction conventions in one small registry while preserving source metadata and retrieval behavior.

## What problem existed?
Canonical parsing carried separate filename conditionals for document type and
harness. Adding a convention risked spreading format knowledge across ingestion.

## How did TESSERA behave before?
AGENTS/CLAUDE/GEMINI/Copilot/SKILL names selected instruction metadata directly
inside canonical.py; unknown formats followed its generic classification.

## What changed or is being tested?
Immutable adapter declarations and a deterministic registry own those defaults.
Duplicate names and ambiguous matches fail explicitly; generic fallback survives.

## How does it work now?
Canonical main: Engine normalization uses the built-ins. Explicit
consumer registries can be passed to parse_and_normalize without mutating global
state. Source frontmatter, hashes, spans and classification provenance retain
their existing ownership. See [contract](../../reference/harness-adapters.md).

## Concrete example
AGENTS.md selects the agent-agnostic adapter and stays drawerless. An unrelated
AGENTS.md.txt takes the generic path. Registering two matching instruction
adapters raises ambiguity rather than choosing an authority winner.

## How was it validated?
`tests/test_harness_adapters.py` covers ten frozen full canonical snapshots,
selection, source metadata, registration and ambiguity. Existing canonical suites
also pass. A five-query corpus has identical baseline/candidate results except
runtime indexed_at and unchanged source bytes. Historical local full-suite counts remain in the PR and are not attributed to
the final candidate. Exact-head and canonical CI evidence is recorded below.

## What improved?
Filename format knowledge lives in one inspectable module; extensions do not
need retrieval changes. Local median selection cost:2.93 microseconds over five
10,000-call repeats with five built-ins; no broad performance claim.

## What remains unimplemented?
Authority, precedence, external import loading and semantic instruction intent
remain #32/#72. No runtime plugin discovery or custom Engine cache schema was
added. No instruction is promoted into a semantic memory by its filename.

## What is unlocked next?
The runtime adapter prerequisite is canonically delivered. #32 remains blocked
only on completing this lifecycle reconciliation and recording its decision; its
authoritative routing does not depend on #15/#20/#27. #72 remains blocked on #32.
Dependency readiness does not itself select or deliver the authority policy.

## Technical provenance
- Baseline:`20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Fixtures:`tests/fixtures/harness_adapters/canonical_baseline.json`
- Implementation:`tessera/harness_adapters.py`, `tessera/canonical.py`
- Prior ingestion/segmentation:[#69](69-text-ingestion.md),[#70](70-structural-segmentation.md)
- Benchmark rationale: exact default canonical and retrieval equivalence; no ranking or corpus changes

### Verified merge and CI evidence

- Final candidate: `973a1e75ae1c024edcdd9acef54d840227bc801b`.
- Merged on 2026-10-12 at 03:52:27 UTC as `f149ff292238e2a6f5cdd95894e9c11c365457f2`.
- [Candidate CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38191615200): all six required Python 3.9/3.12 test/distribution, smoke and sanity jobs succeeded.
- [Candidate Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38191615264): offline reporting and benchmark-contract passed; dev-50 skipped under declared `SMOKE_ONLY`.
- [Canonical CI](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38201483965) and [canonical Benchmark Ledger](https://github.com/LuigiFerronatto/TESSERA/actions/runs/38201483988) succeeded on the merge commit, including canonical dev-50.
- [Candidate Governor](https://github.com/LuigiFerronatto/TESSERA/runs/114655657122) concluded failure at 03:52:33 UTC, six seconds after merge, solely because `mergeable_state` could not be determined. It is not evidence of a pre-merge failure or a successful governor authorization.
- [Historical BLOCK](https://github.com/LuigiFerronatto/TESSERA/pull/289#issuecomment-5946275186) audited old head `3139af3c68751e3dfd2e1ebd68164d7f11c32b5d`; no final-head formal review or KEEP is claimed. Current deterministic governance no longer requires an AI KEEP.
- This reconciliation is a `DOCUMENTATION_CORRECTION`, not a second runtime delivery. Native branch protection migration is separate; this record neither changes nor bypasses settings.

### Current proposed acceptance decision

Proposed `KEEP` for the registry boundary, pending canonical adoption of this
lifecycle correction. This is a new evidence-based proposal, not a historical
Maintainer Audit or an approval attributed to the repository owner. Current
governance permits deterministic acceptance without an AI KEEP; no new formal
review requirement is introduced here. The seven #71 criteria map to frozen
metadata agreement; inspectable deterministic selection; generic/ambiguous-name
fixtures; independent immutable registration without retrieval changes; drawerless
instructions; explicit/default provenance; and the stdlib-only adapter module.
The local canonical/adapter tests and exact-head/canonical CI support those
bounded criteria. The claimed retrieval-equivalence measurement remains the
implementation PR's historical evidence, not a new performance/quality finding.
Once this correction is canonically adopted with successful candidate checks,
record that adoption in #71 and reassess #32 as READY. #72 still requires #32.

## Evolution
Filename conditionals → explicit immutable registry → independent review and
canonical merge with green deterministic validation → lifecycle decision pending
→ separately evaluated authority and instruction resolution.
