# #80 — Versioned current and experimental architecture diagrams

| Field | Value |
|---|---|
| Issue | [#80](https://github.com/LuigiFerronatto/TESSERA/issues/80) |
| Record status | `IN_PROGRESS` |
| Capability type | `documentation` |
| Pull request | Candidate branch `docs/78-80-project-neutral-visuals` |
| Merge commit | Not merged |
| Decision | `PENDING` review |
| Benchmark applicability | `NOT_APPLICABLE` |
| Last audited | 2026-10-02 |

## In one sentence
Add six editable SVG diagrams and a deterministic generator, with explicit current/experimental text and source mappings.

## What problem existed?
Readers lacked a compact visual map separating current Foundation contracts from conditional target experiments.

## How did TESSERA behave before?
Runtime was already project-agnostic, but historical material could imply private
project ownership or show research ideas as current capabilities.

## What changed or is being tested?
Add six editable SVG diagrams and a deterministic generator, with explicit current/experimental text and source mappings. The companion documentation card covers the related cleanup/visual lane.

## How does it work now?
TARGET — NOT YET ON MAIN: the [diagram guide](../ARCHITECTURE_DIAGRAMS.md)
records six asset/source mappings and current-versus-target status. Historical
prose points to current contracts and exact prior identifiers stay in linked Git
history. Production runtime semantics remain unchanged.

## Concrete example
Solid blue Foundation boxes contrast with dashed orange experimental boxes; issue owners remain visible and no target capability is promoted.

## How was it validated?
`tests/test_project_neutral_visual_docs.py` checks exact SVG regeneration, current
and experimental labels, removed private names/assets, 22 retained HTML sections,
valid local image references and a single README architecture image. All SVGs
were rendered and visually inspected. The HTML deck was print-rendered to 22 pages
and compared with the original. The cloud browser denied localhost preview, so
interactive navigation parity is not claimed. Full-suite counts are in the PR.

## What improved?
Public examples no longer imply a private-project dependency. Visual references
make source ownership and conditional target status explicit without adding a
wall of images to the README.

## What remains unimplemented?
No target runtime capability, new brand design or browser integration is
implemented. Interactive HTML preview remains unverified in this environment.
QUMem correction is reused from PR #284 and not counted as another runtime delivery.

## What is unlocked next?
Documentation review, not promotion of downstream runtime experiments.

## Technical provenance
- Baseline:`20814a47ec0f72d7bea0639e0b057df1ecf5cded`
- Guide:[ARCHITECTURE_DIAGRAMS](../ARCHITECTURE_DIAGRAMS.md)
- Assets:`docs/assets/architecture/*.svg`
- Generator:`scripts/render_architecture_diagrams.py`
- Tests:`tests/test_project_neutral_visual_docs.py`
- Related issue:[#78](https://github.com/LuigiFerronatto/TESSERA/issues/78)

## Evolution
Legacy private narrative and sparse visual guidance → neutral public examples
and source-mapped current/target diagrams → review/canonical documentation merge.
