# #112 — Make the terminal logo say TESSERA

| Field | Value |
|---|---|
| Issue | [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) |
| Record status | `IN_PROGRESS` |
| Capability type | `runtime branding contract` |
| Pull request | Pending publication from `fix/112-tessera-ascii-banner` |
| Head commit | Updated when the PR is published |
| Merge commit | Not merged |
| Decision | `PENDING` |
| Benchmark applicability | `SMOKE_ONLY` |
| Last audited | 2026-08-31 |

## In one sentence

The command already called itself TESSERA, but its large terminal letters still spelled AMEM.

## What problem existed?

`tessera banner` used a hardcoded six-line block-letter wordmark inherited from the earlier AMem name. The surrounding function, command and tagline said Tessera, so one output presented two product identities at once.

## How did TESSERA behave before?

```text
tessera banner
→ command and tagline: Tessera
→ large ASCII glyphs: AMEM
```

The legacy glyphs originated in the initial direct-main commit `9cc8c38`. PR #2 later changed display and query rendering but retained them. PR #83 made package/MCP runtime identity TESSERA-native without touching `display.py`.

## What changed or is being tested?

The candidate replaces the active glyphs with an inspectable `TESSERA_BANNER_LINES` constant, centralizes the tagline and adds rich/plain output plus active-runtime legacy-name regression tests.

## How does it work now?

**CANDIDATE — NOT YET ON MAIN.**

Rich terminal output renders the six canonical TESSERA rows. Plain output continues to print the product name and tagline. Tests scan active Python runtime files for legacy AMem identity while deliberately preserving A-MEM research citations and archived history.

## Concrete example

```text
before: large letters spell AMEM
after:  large letters spell TESSERA
```

Research documentation still says “A-MEM: Agentic Memory for LLM Agents” when citing that paper.

## How was it validated?

Validation is pending the implementation PR and CI. Required gates are focused banner tests, the full suite, Python 3.9/3.12, CLI smoke, sanity evaluation and benchmark applicability.

## What improved?

Nothing on `main` until merge. The candidate makes active terminal identity internally consistent and testable.

## What remains unimplemented?

This card does not remove other LAO/Blip runtime coupling tracked by #95, redesign SVG assets, rewrite archives or change any retrieval behavior.

## What is unlocked next?

After merge, the exact ASCII regression is closed. #95 remains a broader independent runtime-decoupling card.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) |
| Pull request | Pending |
| Merge commit | Not merged |
| Evidence/Learnings/Decision | Pending |
| Benchmark record | LongMemEval not applicable; smoke/sanity required |
| PR Evolution Audit | Initial `9cc8c38`; PR #2 / merge `5590b1d`; PR #83 / merge `a6dc12c` |

## Evolution

```text
initial AMEM glyphs inside Tessera CLI
→ TESSERA-native package/MCP identity
→ this banner correction
→ broader #95 runtime legacy-coupling audit
```
