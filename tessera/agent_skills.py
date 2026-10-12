"""Read-only, packaged agent instructions over existing TESSERA public APIs.

These resources are not semantic-memory procedural anchors. Loading them never
installs a runtime integration, writes a store, or executes their example commands.
"""
import importlib.resources
from typing import Tuple

AGENT_SKILL_BUNDLE_VERSION = "1"
AGENT_SKILL_NAMES = (
    "tessera-benchmark", "tessera-doctor", "tessera-init", "tessera-query", "tessera-write",
)


def list_agent_skill_names() -> Tuple[str, ...]:
    """Return the immutable identifiers of the bundled agent instructions."""
    return AGENT_SKILL_NAMES


def read_agent_skill(name: str) -> str:
    """Read one known SKILL.md without installing it or touching user sources."""
    if not isinstance(name, str) or name not in AGENT_SKILL_NAMES:
        raise ValueError("Unknown TESSERA agent skill")
    return importlib.resources.files("tessera").joinpath(
        "agent_skills", name, "SKILL.md"
    ).read_text(encoding="utf-8")
