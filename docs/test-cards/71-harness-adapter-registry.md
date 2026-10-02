# #71 — Isolate instruction formats behind a deterministic registry

| Field | Value |
|---|---|
| Issue | [#71](https://github.com/LuigiFerronatto/TESSERA/issues/71) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime` |
| Pull request | Candidate branch `feat/71-harness-adapter-registry` |
| Merge commit | Not merged |
| Decision | `PENDING` independent review |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-10-02 |

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
TARGET — NOT YET ON MAIN: Engine normalization uses the built-ins. Explicit
consumer registries can be passed to parse_and_normalize without mutating global
state. Source frontmatter, hashes, spans and classification provenance retain
their existing ownership. See [contract](../HARNESS_ADAPTERS.md).

## Concrete example
AGENTS.md selects the agent-agnostic adapter and stays drawerless. An unrelated
AGENTS.md.txt takes the generic path. Registering two matching instruction
adapters raises ambiguity rather than choosing an authority winner.

## How was it validated?
`tests/test_harness_adapters.py` covers ten frozen full canonical snapshots,
selection, source metadata, registration and ambiguity. Existing canonical suites
also pass. A five-query corpus has identical baseline/candidate results except
runtime indexed_at and unchanged source bytes. Final full-suite and exact-head
CI counts are recorded in the PR.

## What improved?
Filename format knowledge lives in one inspectable module; extensions do not
need retrieval changes. Local median selection cost:2.93 microseconds over five
10,000-call repeats with five built-ins; no broad performance claim.

## What remains unimplemented?
Authority, precedence, external import loading and semantic instruction intent
remain #32/#72. No runtime plugin discovery or custom Engine cache schema was
added. No instruction is promoted into a semantic memory by its filename.

## What is unlocked next?
After canonical review/merge/lifecycle, #32's adapter prerequisite can be
reassessed. #72 still depends on #32 as well. No dependency is promoted now.

## Technical provenance
- Baseline:`20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Fixtures:`tests/fixtures/harness_adapters/canonical_baseline.json`
- Implementation:`tessera/harness_adapters.py`, `tessera/canonical.py`
- Prior ingestion/segmentation:[#69](69-text-ingestion.md),[#70](70-structural-segmentation.md)
- Benchmark rationale: exact default canonical and retrieval equivalence; no ranking or corpus changes

## Evolution
Filename conditionals → explicit immutable registry → independent review and
canonical merge → separately evaluated authority and instruction resolution.
