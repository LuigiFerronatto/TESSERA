"""Domain models and custom exceptions for Tessera's atomic memory cards."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class InvalidFrontmatterError(Exception):
    """Raised when a memory note's YAML frontmatter is malformed or incomplete."""


class WriteGatingViolationError(Exception):
    """Raised by the compatibility write API when admission is reject/review."""

    def __init__(self, result: Any):
        self.result = result
        decision = result.decision
        super().__init__(
            f"Write not persisted: admission={decision.admission.value}; "
            f"reasons={','.join(decision.reasons)}"
        )


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


@dataclass(frozen=True)
class EpisodeTurn:
    """An actual source interaction; position is a positive, episode-local order key.

    Positions may be sparse and must be supplied by the source producer. Role
    and timestamp are source metadata, not inferred from the turn's text.
    """

    position: int
    role: str
    content: str
    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 1:
            raise ValueError("turn position must be a positive integer")
        if not isinstance(self.role, str) or not self.role.strip():
            raise ValueError("turn role must be a nonempty source role")
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("turn content must be nonempty text")
        if self.timestamp is not None and not isinstance(self.timestamp, str):
            raise ValueError("turn timestamp must be source text or None")


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
    turns: Tuple[EpisodeTurn, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) for value in (self.beginning, self.middle, self.end)):
            raise ValueError("episode sections must be text")
        self.turns = tuple(self.turns)
        if not all(isinstance(turn, EpisodeTurn) for turn in self.turns):
            raise ValueError("episode turns must be EpisodeTurn records")
        positions = [turn.position for turn in self.turns]
        if positions != sorted(set(positions)):
            raise ValueError("episode turns must have unique, increasing positions")

    @classmethod
    def from_turns(cls, turns: List[EpisodeTurn]) -> "Episode":
        """Keep actual turns without fabricating summaries or losing source roles."""
        return cls("", "", "", tuple(turns))

    def to_markdown_body(self) -> str:
        """Renders the episode as a structured Markdown body (## sections)."""
        rendered = (
            f"## Início (contexto/gatilho)\n{self.beginning.strip()}\n\n"
            f"## Meio (o que aconteceu)\n{self.middle.strip()}\n\n"
            f"## Fim (resultado/aprendizado)\n{self.end.strip()}\n"
        )
        for turn in self.turns:
            rendered += f"\n## Turn {turn.position} ({turn.role})\n{turn.content}\n"
        return rendered

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
    sanitized: bool = False
    threat_detected: bool = False
    content_changed: bool = False
    admission: str = "accept"
    reasons: List[str] = field(default_factory=list)
    original_hash: str = ""
    persisted_hash: str = ""
    temporal_position: Optional[int] = None
    episode_source: Optional[Dict[str, Any]] = None
    source_evidence: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        desc = self.description if self.description else f"{self.memory_type.title()} memory note"
        payload = {
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
                "threat_detected": self.threat_detected,
                "content_changed": self.content_changed,
                "admission": self.admission,
                "reasons": self.reasons,
                "original_hash": self.original_hash,
                "persisted_hash": self.persisted_hash,
            },
        }
        if self.episode_source is not None:
            payload["temporal_position"] = self.temporal_position
            payload["episode_source"] = self.episode_source
            payload["source_evidence"] = self.source_evidence
        return payload
