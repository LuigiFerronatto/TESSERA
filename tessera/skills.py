"""
Default procedural-anchor skills bundled with Tessera.

Per the operational-failure taxonomy this project targets (category SC2 —
execution/validation-layer failures), an agent's *initial* skill set should
not be encyclopedic/factual knowledge, but compact, reusable procedural
anchors: structured steps, verification plans, and known pitfalls for the
execution environment. The 5 skills bundled here cover the failure classes
skills demonstrably help most with:

    sk_service_lifecycle      — background_service_lifecycle_failure
    sk_docker_environment     — environment_infrastructure_failure
    sk_runtime_verification   — static_verification_without_runtime
    sk_schema_compliance      — output_format_schema_mismatch
    sk_shell_execution        — shell_code_corruption

Each is a fully hand-authored Markdown note (frontmatter + body) shipped as
package data in `tessera/skills_library/*.md`. `install_default_skills(engine)`
copies them as-is into the target storage directory and rebuilds the index —
this preserves the original frontmatter (including descriptive fields like
`domain`, `target_tools`, `success_correlation_rate` that Tessera's indexer
doesn't require but are useful documentation/provenance) rather than
regenerating the notes through `write_memory_note` (which would strip them
and re-timestamp everything).
"""

import importlib.resources
import shutil
from pathlib import Path
from typing import List

from .engine import TesseraEngine

SKILL_IDS: List[str] = [
    "sk_service_lifecycle",
    "sk_docker_environment",
    "sk_runtime_verification",
    "sk_schema_compliance",
    "sk_shell_execution",
]


def _skills_library_dir() -> Path:
    return Path(str(importlib.resources.files("tessera").joinpath("skills_library")))


def list_default_skill_files() -> List[Path]:
    """Returns the paths of all bundled skill Markdown files."""
    library_dir = _skills_library_dir()
    return sorted(library_dir.glob("sk_*.md"))


def install_default_skills(engine: TesseraEngine) -> List[str]:
    """
    Copies all bundled procedural-anchor skills into the engine's storage
    directory, then rebuilds the graph index so they're immediately
    retrievable. Idempotent: re-running overwrites the same files, it does
    not duplicate them. Returns the list of destination file paths.
    """
    storage_dir = Path(engine.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    written_paths = []
    for src_path in list_default_skill_files():
        dest_path = storage_dir / src_path.name
        shutil.copyfile(src_path, dest_path)
        written_paths.append(str(dest_path))

    engine.build_index()
    return written_paths
