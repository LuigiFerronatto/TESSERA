# TESSERA Architecture Decision Records

Architecture Decision Records (ADRs) are binding constraints for TESSERA's
module boundaries and public contracts. An accepted ADR describes the target
architecture; it does not make a proposed runtime capability current.

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-core-vs-optional-llm-boundary.md) | Accepted | Deterministic memory core vs optional LLM and consuming-agent boundary |
| [0002](0002-repository-layout-and-distribution-boundary.md) | Accepted | Preserve the root package, separate distributable runtime from repository tooling, and migrate in owned stages |
| [0003](0003-configuration-and-store-discovery.md) | Accepted candidate | Versioned project config, named global registry, deterministic store selection, and explicit migration |
