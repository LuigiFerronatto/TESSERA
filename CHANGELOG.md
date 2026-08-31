# Changelog

All notable TESSERA product changes are recorded here.

This is a **curated product history**, not an automatically generated commit log. Pull requests should update `Unreleased` when they change product behavior, public contracts, configuration, supported inputs or user-visible capabilities. Documentation-only changes may mark changelog impact as N/A when they do not alter the product contract.

See [`docs/CHANGE_POLICY.md`](docs/CHANGE_POLICY.md) for the update rules.

## Unreleased

### Added
- A versioned LongMemEval V1 dev-50 benchmark ledger with immediate-parent regression gating, a separate historical #96 comparison, validated Test Card attribution, pinned forward-environment fingerprints, and checksum-pinned conditional benchmark CI. ([#100](https://github.com/LuigiFerronatto/TESSERA/issues/100))
- Versioned TESSERA brand assets and a canonical 1280×640 repository/social card. ([#81](https://github.com/LuigiFerronatto/TESSERA/pull/81))

### Changed
- The experimental roadmap now derives status from GitHub state, merged
  implementation/evidence, declared dependencies, and benchmark records. It
  records completed #68/#94/#96/#100 work, accepted ADR #74 in progress, the
  #103–#106 evaluation chain, and the current M0–M5 critical path without stale
  emoji markers. ([#74](https://github.com/LuigiFerronatto/TESSERA/issues/74))
- Root README is now the progressive product entrypoint: executive first, plain-language explanation next, technical details and experimental roadmap deeper down. ([#82](https://github.com/LuigiFerronatto/TESSERA/pull/82))
- Package metadata and MCP runtime configuration are TESSERA-native and standalone. The canonical MCP storage variable is now `TESSERA_STORAGE_DIR`. ([#83](https://github.com/LuigiFerronatto/TESSERA/pull/83))
- Pull requests now use PR Contract v2 with explicit change classification, contract-surface impact, Evaluation Card, changelog decision, public-surface invariants and known-regression disclosure. ([#66](https://github.com/LuigiFerronatto/TESSERA/issues/66))

### Fixed
- Memory writes now accept only canonical Markdown persistence and reject unsupported formats before mutation, preventing acknowledged-but-unindexable JSON files. ([#94](https://github.com/LuigiFerronatto/TESSERA/issues/94))
- Public package metadata no longer points to an external development repository or publishes an external project identity as the package author. ([#83](https://github.com/LuigiFerronatto/TESSERA/pull/83))

### Experimental
- No new experimental capability has been promoted in this documentation/governance round. Existing graph, temporal, arbitration, abstention and adaptive-retrieval work remains governed by its Test Cards.

### Deprecated
- Legacy project-specific MCP storage configuration is deprecated by removal; migrate to `TESSERA_STORAGE_DIR`.

### Removed
- Legacy external-project identity from package metadata and MCP-facing examples/configuration. ([#83](https://github.com/LuigiFerronatto/TESSERA/pull/83))

### Architecture Decisions
- Accepted ADR 0001: deterministic TESSERA memory infrastructure ends at
  structured evidence with provenance; optional planner/reader adapters consume
  that contract, consuming agents own final cognition, and LLM judges remain
  benchmark-only infrastructure. This records current legacy deviations without
  changing runtime behavior. ([#74](https://github.com/LuigiFerronatto/TESSERA/issues/74))
- TESSERA's public product boundary is project-agnostic: public docs, examples, fixtures, benchmarks and runtime-facing configuration must describe TESSERA itself rather than a development environment. ([#62](https://github.com/LuigiFerronatto/TESSERA/issues/62))
- Brand assets are repository-owned and current-vs-target architecture must remain visually distinguishable. ([#64](https://github.com/LuigiFerronatto/TESSERA/issues/64))
- The root README describes **implemented capabilities separately from hypotheses/Test Cards**. ([#63](https://github.com/LuigiFerronatto/TESSERA/issues/63))
- Product-history updates are curated manually; CI may enforce explicit changelog consideration but must not synthesize entries from commits. ([#65](https://github.com/LuigiFerronatto/TESSERA/issues/65))

---

## Foundation history — pre-changelog backfill

This section summarizes the major Foundation milestones that existed before the changelog policy. It does not attempt to recreate every commit.

### Added
- Output/agent-consumption contract and core product invariants. ([#1](https://github.com/LuigiFerronatto/TESSERA/pull/1))
- Explainable multi-signal ranking and query-aware relevant evidence. ([#2](https://github.com/LuigiFerronatto/TESSERA/pull/2))
- Canonical Metadata, document classification, stable memory identity, stable source-document identity and explicit relation parsing. ([#3](https://github.com/LuigiFerronatto/TESSERA/pull/3))
- Permanent TESSERA CI with Python 3.9/3.12 tests, CLI smoke and deterministic sanity retrieval evaluation. ([#4](https://github.com/LuigiFerronatto/TESSERA/pull/4))
- Evidence Ledger and source-version-aware provenance integrated into retrieval. ([#6](https://github.com/LuigiFerronatto/TESSERA/pull/6))
- Documentation map, architecture/reference docs, research references and competitive landscape.

### Architecture Decisions
- Source text remains authoritative; index/cache/ledger state is derived and rebuildable.
- TESSERA returns structured evidence rather than replacing the consuming agent's final cognition.
- Exactly three semantic drawers remain: `facts`, `preferences`, `insights`.
- Retrieval relevance, confidence, authority, temporal validity, relation confidence and utility are separate dimensions.
- New research ideas enter through Test Cards and ablations rather than being promoted directly into the architecture.
