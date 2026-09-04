"""
Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories
=================================

Long-term memory engine for autonomous agents. Memories are stored as human-readable Markdown
files with YAML frontmatter and indexed in-memory as a heterogeneous
knowledge graph, retrieved via a Dynamic Weighted PageRank (DW-PR)
subgraph search.

Quick usage:

    from tessera import TesseraEngine, Entity, Connection

    engine = TesseraEngine(storage_dir="./memories")
    engine.write_memory_note(
        mem_id="mem_pref_001",
        mem_type="preference",
        episode_id="ep_001",
        content="Alex prefers reports generated strictly in PDF format.",
        tags=["reports", "pdf"],
        entities=[Entity("Alex", "Primary operator.")],
    )
    engine.build_index()
    results = engine.retrieve_context("How does Alex want reports delivered?")

See docs/ARCHITECTURE.md for the full design rationale.
"""

from .models import (
    Entity,
    Connection,
    Episode,
    MemoryFrontmatter,
    InvalidFrontmatterError,
    WriteGatingViolationError,
    STORE_FACTS,
    STORE_PREFERENCES,
    STORE_INSIGHTS,
)
from .security import (
    WriteAdmission,
    WriteGateDecision,
    WriteGatingEngine,
    WriteResult,
    content_sha256,
)
from .conflict import ConflictResolver
from .engine import TesseraEngine
from .orchestrator import TesseraOrchestrator, OrchestratorResult
from .hooks import TesseraTaskHook, TaskInterceptionResult
from .skills import SKILL_IDS, install_default_skills, list_default_skill_files
from .init_flow import (
    InitRequest,
    InitializationPlan,
    InitializationResult,
    apply_initialization_plan,
    build_initialization_plan,
)
from .evidence import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceExtraction,
    EvidenceFreshness,
    EvidenceLedger,
    EvidenceRecord,
    EvidenceSource,
    EvidenceSpan,
    enrich_retrieval_results,
    evidence_for_text,
    evidence_from_canonical,
    ledger_from_graph,
    locate_evidence_span,
    verify_evidence_freshness,
)

__version__ = "3.4.0"

__all__ = [
    "TesseraEngine",
    "TesseraOrchestrator",
    "OrchestratorResult",
    "TesseraTaskHook",
    "TaskInterceptionResult",
    "Entity",
    "Connection",
    "Episode",
    "MemoryFrontmatter",
    "WriteGatingEngine",
    "WriteAdmission",
    "WriteGateDecision",
    "WriteResult",
    "content_sha256",
    "ConflictResolver",
    "InvalidFrontmatterError",
    "WriteGatingViolationError",
    "STORE_FACTS",
    "STORE_PREFERENCES",
    "STORE_INSIGHTS",
    "SKILL_IDS",
    "install_default_skills",
    "list_default_skill_files",
    "InitRequest",
    "InitializationPlan",
    "InitializationResult",
    "build_initialization_plan",
    "apply_initialization_plan",
    "EVIDENCE_SCHEMA_VERSION",
    "EvidenceExtraction",
    "EvidenceFreshness",
    "EvidenceLedger",
    "EvidenceRecord",
    "EvidenceSource",
    "EvidenceSpan",
    "enrich_retrieval_results",
    "evidence_for_text",
    "evidence_from_canonical",
    "ledger_from_graph",
    "locate_evidence_span",
    "verify_evidence_freshness",
    "__version__",
]
