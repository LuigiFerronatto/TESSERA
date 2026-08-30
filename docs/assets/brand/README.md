# TESSERA visual identity

## Executive takeaway

This folder contains the canonical repository-owned visual assets for TESSERA. The visual system is intentionally minimal, high-profile and technical: dark neutral surfaces, a violet/blue spectral accent and a single star-like mark.

The logo is a brand mark, not an architecture diagram. Product diagrams must remain visually consistent with it without changing its shape to represent implementation details.

## Canonical assets

- `tessera-logo-light.svg` — standalone logo on white.
- `tessera-lockup-light.svg` — logo + title + expanded name on white.
- `tessera-repo-card.svg` — 1280×640 repository/social card, dark background.

## Name

**TESSERA**

Expanded name:

> **Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories**

## Palette

| Role | Color | Hex |
| --- | --- | --- |
| Light background | White | `#FFFFFF` |
| Dark background | Near black | `#030307` |
| Dark secondary | Ink violet | `#0A0918` |
| Soft violet | Soft lilac | `#C8B6FF` |
| Spectral violet | Violet | `#9B7CFF` |
| Cool spectral accent | Periwinkle | `#7F93FF` |
| Deep accent | Electric violet | `#6D4DFF` |
| Light body text | Mist | `#D8D4E5` |
| Dark body text | Graphite violet | `#4F4B60` |

The logo/title gradient may interpolate through the violet/periwinkle values. Do not introduce unrelated accent colors into primary TESSERA brand surfaces.

## Typography

The generated visual identity uses a custom geometric/futurist treatment rather than a guaranteed single commercial typeface. For reproducible repository assets, use this stack:

### Title / display

`Michroma` as the preferred open display reference, with `Eurostile`/system geometric fallbacks.

Characteristics:
- extended geometric proportions;
- generous tracking;
- thin-to-medium weight;
- no decorative sci-fi UI framing.

### Subtitle / body

`Inter` or `Manrope`, with standard sans-serif fallbacks.

Characteristics:
- neutral;
- readable at small sizes;
- modest tracking for the expanded TESSERA name.

## Visual rules

1. Keep the logo shape stable; do not replace it with a cube/tesseract illustration.
2. Prefer substantial negative space over decorative interface chrome.
3. Use glow sparingly; the logo may emit a soft spectral halo, but text should remain crisp.
4. Current architecture and target architecture must be labeled distinctly in diagrams.
5. Public visuals must be project-agnostic and must not depend on a private agent/project narrative.
6. Avoid marketing claims that are not backed by benchmarks or Test Cards.

## Repository social card

The canonical social card is exactly `1280×640` in SVG viewBox/declared dimensions and contains only:

- the approved star mark;
- `TESSERA`;
- `Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories`.

No feature list, benchmark claim or external project name should be added to the social card.
