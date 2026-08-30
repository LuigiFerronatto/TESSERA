"""
Tessera — Temporal Evolving State Synthesis with Explicit Relations and Atomic Memories
=================================

Long-term memory engine for autonomous agents (built for LAO — Lab
Autonomous Officer). Memories are stored as human-readable Markdown
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
from .security import WriteGatingEngine
from .conflict import ConflictResolver
from .engine import TesseraEngine
from .orchestrator import TesseraOrchestrator, OrchestratorResult
from .hooks import TesseraTaskHook, TaskInterceptionResult
from .skills import SKILL_IDS, install_default_skills, list_default_skill_files
from .evidence import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceExtraction,
    EvidenceFreshness,
    EvidenceLedger,
    EvidenceRecord,
    EvidenceSource,
    EvidenceSpan,
    evidence_from_canonical,
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
    "ConflictResolver",
    "InvalidFrontmatterError",
    "WriteGatingViolationError",
    "STORE_FACTS",
    "STORE_PREFERENCES",
    "STORE_INSIGHTS",
    "SKILL_IDS",
    "install_default_skills",
    "list_default_skill_files",
    "EVIDENCE_SCHEMA_VERSION",
    "EvidenceExtraction",
    "EvidenceFreshness",
    "EvidenceLedger",
    "EvidenceRecord",
    "EvidenceSource",
    "EvidenceSpan",
    "evidence_from_canonical",
    "verify_evidence_freshness",
    "__version__",
]
