# #112 — Make the terminal logo say TESSERA

| Field | Value |
|---|---|
| Issue | [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) |
| Record status | `VALIDATED` |
| Capability type | `runtime branding contract` |
| Pull request | [PR #113](https://github.com/LuigiFerronatto/TESSERA/pull/113) |
| Candidate head | `817ec65e6e792cfaf84f27f6bd0359f874384d23` |
| Merge commit | [`a80a5f1`](https://github.com/LuigiFerronatto/TESSERA/commit/a80a5f19671a002e6ec2ed1846d041afb090b7a2) |
| Decision | `KEEP` |
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

**VALIDATED ON `main`.**

Rich terminal output renders the six canonical TESSERA rows. Plain output continues to print the product name and tagline. Tests scan active Python runtime files for legacy AMem identity while deliberately preserving A-MEM research citations and archived history.

## Concrete example

```text
before: large letters spell AMEM
after:  large letters spell TESSERA
```

Research documentation still says “A-MEM: Agentic Memory for LLM Agents” when citing that paper.

## How was it validated?

PR #113 passed Python 3.9, Python 3.12, CLI smoke, deterministic sanity evaluation and offline benchmark reporting/applicability. LongMemEval dev-50 was correctly skipped because retrieval semantics did not change.

## What improved?

The active terminal identity is now internally consistent and guarded by exact rich/plain regression tests.

## What remains unimplemented?

This card does not remove other LAO/Blip runtime coupling tracked by #95, redesign SVG assets, rewrite archives or change any retrieval behavior.

## What is unlocked next?

After merge, the exact ASCII regression is closed. #95 remains a broader independent runtime-decoupling card.

## Technical provenance

| Artifact | Link or identifier |
|---|---|
| Issue/Test Card | [#112](https://github.com/LuigiFerronatto/TESSERA/issues/112) |
| Pull request | [PR #113](https://github.com/LuigiFerronatto/TESSERA/pull/113) |
| Merge commit | [`a80a5f1`](https://github.com/LuigiFerronatto/TESSERA/commit/a80a5f19671a002e6ec2ed1846d041afb090b7a2) |
| Evidence/Learnings/Decision | [Issue comment](https://github.com/LuigiFerronatto/TESSERA/issues/112#issuecomment-5473210880) |
| Benchmark record | LongMemEval not applicable; smoke/sanity required |
| PR Evolution Audit | Initial `9cc8c38`; PR #2 / merge `5590b1d`; PR #83 / merge `a6dc12c` |

## Evolution

```text
initial AMEM glyphs inside Tessera CLI
→ TESSERA-native package/MCP identity
→ this banner correction
→ broader #95 runtime legacy-coupling audit
```
