"""Frozen E1/E3 experiment contracts, intentionally outside the runtime package.

Membership is decided before any optional TESSERA B/M/E rendering. Records here
are harness inputs, not a competing durable EpisodeTurn model (see README).
"""

from dataclasses import dataclass
from datetime import datetime
import math
import re
from typing import List, Optional, Sequence, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROLES = frozenset({"user", "assistant", "tool", "system"})
ACKNOWLEDGEMENTS = frozenset({"sim", "ok", "okay", "faz isso", "yes", "do it", "continue"})
TOPIC_SWITCH = re.compile(
    r"^(?:new topic|change (?:the )?topic|switch(?:ing)? topics|"
    r"mudando de assunto|mudar de assunto|outro assunto)(?:\b|:)", re.IGNORECASE
)


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("timestamp must be ISO-8601 source text or null")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamp must have an explicit timezone")
    return parsed


@dataclass(frozen=True)
class ExperimentTurn:
    """An explicit source projection local to this benchmark, with no persistence."""

    turn_id: str
    position: int
    role: str
    content: str
    session_id: str
    task_id: str
    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        for name in ("turn_id", "session_id", "task_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be nonempty source text")
        if type(self.position) is not int or self.position < 1:
            raise ValueError("position must be a positive integer")
        if self.role not in ROLES:
            raise ValueError("role must explicitly be user, assistant, tool or system")
        if not isinstance(self.content, str):
            raise ValueError("content must be source text")
        parse_timestamp(self.timestamp)


def validate_turns(turns: Sequence[ExperimentTurn]) -> None:
    """Reject mixed sessions/tasks, duplicate IDs and reordered source records."""
    positions = [turn.position for turn in turns]
    if positions != sorted(set(positions)):
        raise ValueError("positions must be unique and increasing")
    if len({turn.turn_id for turn in turns}) != len(turns):
        raise ValueError("turn IDs must be unique")
    if len({(turn.session_id, turn.task_id) for turn in turns}) > 1:
        raise ValueError("segment each session/task separately")
    known_times = [parse_timestamp(t.timestamp) for t in turns if t.timestamp is not None]
    if known_times != sorted(known_times):
        raise ValueError("known source timestamps must be nondecreasing")


@dataclass(frozen=True)
class Decision:
    turn_id: str
    previous_user_id: Optional[str]
    semantic_boundary: Optional[bool]
    semantic_reason: str
    similarity: Optional[float]
    timed_out: Optional[bool]
    gap_minutes: Optional[float]
    boundary: bool


@dataclass(frozen=True)
class Segmentation:
    episodes: Tuple[Tuple[ExperimentTurn, ...], ...]
    decisions: Tuple[Decision, ...]

    @property
    def boundary_ids(self) -> Tuple[str, ...]:
        return tuple(episode[0].turn_id for episode in self.episodes[1:])


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"(?u)\b\w+\b", text.casefold()))


def adjacent_signal(previous: ExperimentTurn, current: ExperimentTurn,
                    threshold: float) -> Tuple[Optional[bool], str, Optional[float]]:
    """Only adjacent user texts enter this signal; timestamps and other roles do not."""
    if previous.role != "user" or current.role != "user":
        raise ValueError("continuity inputs must both have explicit user roles")
    if TOPIC_SWITCH.match(current.content.strip()):
        return True, "explicit_topic_switch", None
    # Frozen, narrow acknowledgements; arbitrary short requests are NOT all acks.
    # Abstain on either adjacent side; do not silently compare an older user turn.
    pair = [_normalize(previous.content), _normalize(current.content)]
    if not all(pair):
        return None, "insufficient_lexical_signal", None
    if any(text in ACKNOWLEDGEMENTS for text in pair):
        return None, "adjacent_acknowledgement", None
    matrix = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b").fit_transform(
        [previous.content, current.content]
    )
    similarity = float(cosine_similarity(matrix[0], matrix[1])[0][0])
    return similarity < threshold, "adjacent_user_tfidf", similarity


def segment(turns: Sequence[ExperimentTurn], *, variant: str,
            similarity_threshold: float = 0.03, timeout_minutes: float = 30) -> Segmentation:
    """E1 ignores timeout for membership; E3 ORs it as a separate user-gap signal.

    Non-user turns never start semantic episodes and are retained byte-for-byte.
    Leading non-user context stays with the first user. Missing time means unknown,
    not zero and not wall-clock now. Equality to the timeout does not split.
    """
    if variant not in {"E1", "E3"}:
        raise ValueError("variant must explicitly be E1 or E3")
    if not math.isfinite(similarity_threshold) or not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity threshold must be finite and in [0, 1]")
    if not math.isfinite(timeout_minutes) or timeout_minutes < 0:
        raise ValueError("timeout minutes must be finite and nonnegative")
    validate_turns(turns)
    episodes: List[Tuple[ExperimentTurn, ...]] = []
    current_episode: List[ExperimentTurn] = []
    decisions: List[Decision] = []
    previous_user: Optional[ExperimentTurn] = None
    for turn in turns:
        semantic, reason, similarity = None, "non_user_context", None
        gap, timed_out = None, None
        previous_id = previous_user.turn_id if previous_user is not None else None
        if turn.role == "user":
            reason = "first_user"
            if previous_user is not None:
                semantic, reason, similarity = adjacent_signal(previous_user, turn, similarity_threshold)
                before, after = parse_timestamp(previous_user.timestamp), parse_timestamp(turn.timestamp)
                if before is not None and after is not None:
                    gap = (after - before).total_seconds() / 60
                    timed_out = gap > timeout_minutes
            previous_user = turn
        boundary = semantic is True or (variant == "E3" and timed_out is True)
        if boundary and current_episode:
            episodes.append(tuple(current_episode))
            current_episode = []
        current_episode.append(turn)
        decisions.append(Decision(turn.turn_id, previous_id, semantic, reason, similarity,
                                  timed_out, gap, boundary))
    if current_episode:
        episodes.append(tuple(current_episode))
    return Segmentation(tuple(episodes), tuple(decisions))
