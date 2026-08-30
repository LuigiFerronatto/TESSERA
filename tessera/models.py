"""Domain models and custom exceptions for Tessera's atomic memory cards."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


class InvalidFrontmatterError(Exception):
    """Raised when a memory note's YAML frontmatter is malformed or incomplete."""


class WriteGatingViolationError(Exception):
    """Raised when a memory is rejected outright by the write-side security gate."""


@dataclass
class Entity:
    """A named entity mentioned inside a memory note (person, tool, service, ...)."""

    name: str
    description: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"name": self.name, "description": self.description}


# The 3 typed stores ("gavetas") every memory note is filed into. This is a
# deliberate simplification of `node_type` for write-time routing: facts and
# preferences map 1:1, but `procedural_anchor` notes are filed as "insights"
# (transferable learnings from past task execution), matching the mental
# model of "fatos / preferências / insights transferíveis" rather than the
# more implementation-flavored "procedural_anchor" name.
STORE_FACTS = "facts"
STORE_PREFERENCES = "preferences"
STORE_INSIGHTS = "insights"

NODE_TYPE_TO_STORE = {
    "factual": STORE_FACTS,
    "preference": STORE_PREFERENCES,
    "procedural_anchor": STORE_INSIGHTS,
}
STORE_TO_NODE_TYPE = {v: k for k, v in NODE_TYPE_TO_STORE.items()}


@dataclass
class Episode:
    """
    An episodic memory: a task execution broken into beginning / middle / end,
    instead of one undifferentiated block of text. This lets retrieval and
    consolidation distinguish "what was the goal" from "what happened" from
    "what was the outcome/learning" — which is what actually differs between
    a fact, a preference, and a transferable insight.

    - beginning: the goal/context/trigger — why this episode started.
    - middle:    what actually happened — actions taken, decisions made.
    - end:       the outcome — result, resolution, or lesson learned.
    """

    beginning: str
    middle: str
    end: str

    def to_markdown_body(self) -> str:
        """Renders the episode as a structured Markdown body (## sections)."""
        return (
            f"## Início (contexto/gatilho)\n{self.beginning.strip()}\n\n"
            f"## Meio (o que aconteceu)\n{self.middle.strip()}\n\n"
            f"## Fim (resultado/aprendizado)\n{self.end.strip()}\n"
        )

    @staticmethod
    def from_markdown_body(body: str) -> "Episode":
        """
        Best-effort parse of a Markdown body back into begin/middle/end
        sections. Falls back to putting the whole body in `middle` if the
        expected section headers aren't found (e.g. a plain, non-episodic
        note written before this convention existed).
        """
        import re

        sections = {"beginning": "", "middle": "", "end": ""}
        pattern = re.compile(
            r"##\s*(Início|Inicio|Beginning)[^\n]*\n(.*?)"
            r"(?=##\s*(?:Meio|Middle)|##\s*(?:Fim|End)|\Z)"
            r"|##\s*(Meio|Middle)[^\n]*\n(.*?)(?=##\s*(?:Fim|End)|\Z)"
            r"|##\s*(Fim|End)[^\n]*\n(.*)",
            re.IGNORECASE | re.DOTALL,
        )
        found_any = False
        for match in pattern.finditer(body):
            if match.group(1):
                sections["beginning"] = match.group(2).strip()
                found_any = True
            elif match.group(3):
                sections["middle"] = match.group(4).strip()
                found_any = True
            elif match.group(5):
                sections["end"] = match.group(6).strip()
                found_any = True

        if not found_any:
            sections["middle"] = body.strip()

        return Episode(**sections)


@dataclass
class Connection:
    """A directed, typed relationship from one memory note to another node."""

    target_memory_id: str
    relation_type: str
    cosine_similarity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_memory_id": self.target_memory_id,
            "relation_type": self.relation_type,
            "cosine_similarity": self.cosine_similarity,
        }


@dataclass
class MemoryFrontmatter:
    """
    Structured metadata persisted as the YAML frontmatter of every memory
    note (.md file). Mirrors the "atomic card" format used across Tessera.
    """

    memory_id: str
    memory_type: str  # factual | preference | procedural_anchor
    created_at: str
    last_updated_at: str
    episode_id: str
    description: str = ""
    provenance_turns: List[int] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    active_connections: List[Connection] = field(default_factory=list)
    gating_status: str = "passed"
    toxicity_score: float = 0.0
    sanitized: bool = True

    def to_dict(self) -> Dict[str, Any]:
        desc = self.description if self.description else f"{self.memory_type.title()} memory note"
        return {
            "name": self.memory_id.split("/")[-1],
            "description": desc,
            "metadata": {
                "domain": self.memory_id.split("/")[0] if "/" in self.memory_id else "general",
            },
            "id": self.memory_id,
            "node_type": self.memory_type,
            "created_at": self.created_at,
            "last_updated_at": self.last_updated_at,
            "episode_id": self.episode_id,
            "provenance_turns": self.provenance_turns,
            "tags": self.tags,
            "entities": [ent.to_dict() for ent in self.entities],
            "active_connections": [conn.to_dict() for conn in self.active_connections],
            "security": {
                "gating_status": self.gating_status,
                "toxicity_score": self.toxicity_score,
                "sanitized": self.sanitized,
            },
        }
