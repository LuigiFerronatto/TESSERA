"""
Episode boundary detection — a lightweight stand-in for QUMem's fine-tuned
turn-by-turn continuity classifier (f_θ).

QUMem's paper trains a small binary classifier that looks at consecutive
user turns and decides "same episode" vs. "new episode starts here",
letting episode boundaries emerge dynamically from a live conversation
instead of being delimited by hand. Tessera previously had NO equivalent at
all — `Episode(beginning, middle, end)` (see `models.py`) was always
populated explicitly by the caller, with zero automatic boundary logic
anywhere in the codebase.

Training/shipping an actual fine-tuned classifier is disproportionate to
Tessera's current scale, so this module implements a **cheap, dependency-free
heuristic** that approximates the same job:

    1. Timeout: if more than `timeout_minutes` elapsed since the last turn,
       the current episode is closed and a new one starts — a long gap
       almost always means the user moved on to something else.
    2. Topical drift: if the new turn's TF-IDF cosine similarity against
       the episode-so-far's accumulated text drops below
       `similarity_threshold`, the topic likely changed — close the
       episode here too.

This is intentionally simple (no fine-tuning, reuses the same TF-IDF
machinery `TesseraEngine` already depends on for retrieval) — see
`Tessera/docs/QUMEM-GAP-ANALYSIS.md` for the full rationale and why a bigger
classifier isn't justified yet.
"""

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Episode

DEFAULT_SIMILARITY_THRESHOLD = 0.03
DEFAULT_TIMEOUT_MINUTES = 30


@dataclass
class _Turn:
    text: str
    timestamp: datetime.datetime


@dataclass
class EpisodeBoundaryTracker:
    """
    Feed it turns one at a time via `add_turn()`. Whenever a boundary is
    detected, the just-closed episode is returned (as an `Episode`, with
    the first turn as `beginning`, the middle turns joined as `middle`, and
    the last turn as `end`) so the caller can immediately persist it (e.g.
    via `TesseraEngine.write_episode` or the new auto-decompose pipeline)
    instead of holding state open indefinitely.

    Usage:
        tracker = EpisodeBoundaryTracker()
        for turn_text in conversation_turns:
            closed = tracker.add_turn(turn_text)
            if closed is not None:
                engine.write_episode(mem_id=..., store=..., episode=closed, ...)
        # Don't forget the tail: whatever's left when the conversation ends.
        tail = tracker.flush()
        if tail is not None:
            engine.write_episode(..., episode=tail, ...)
    """

    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    timeout_minutes: float = DEFAULT_TIMEOUT_MINUTES
    _turns: List[_Turn] = field(default_factory=list)

    def add_turn(self, text: str, timestamp: Optional[datetime.datetime] = None) -> Optional[Episode]:
        """
        Adds a new turn. Returns the just-closed `Episode` if this turn
        triggered a boundary (timeout or topical drift vs. the episode so
        far), in which case `text` becomes the first turn of the NEW
        episode. Returns None if the turn was simply appended to the
        current, still-open episode.
        """
        timestamp = timestamp or datetime.datetime.now().astimezone()
        closed_episode = None

        if self._turns:
            last_turn = self._turns[-1]
            gap_minutes = (timestamp - last_turn.timestamp).total_seconds() / 60.0
            timed_out = gap_minutes > self.timeout_minutes
            drifted = self._has_topical_drift(text)

            if timed_out or drifted:
                closed_episode = self._build_episode()
                self._turns = []

        self._turns.append(_Turn(text=text, timestamp=timestamp))
        return closed_episode

    def flush(self) -> Optional[Episode]:
        """Closes and returns whatever episode is currently open (e.g. at the
        end of a conversation/task), or None if nothing was ever added."""
        if not self._turns:
            return None
        episode = self._build_episode()
        self._turns = []
        return episode

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _has_topical_drift(self, new_text: str) -> bool:
        """True if `new_text` is too dissimilar from the episode accumulated
        so far to still belong to it. A single-turn episode-so-far (or a
        degenerate all-stopword corpus) is never considered drifted — there
        isn't enough signal yet to justify closing so early."""
        accumulated = " ".join(t.text for t in self._turns).strip()
        if not accumulated or not new_text.strip():
            return False
        try:
            vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
            matrix = vectorizer.fit_transform([accumulated, new_text])
            similarity = cosine_similarity(matrix[0], matrix[1])[0][0]
        except ValueError:
            # e.g. empty vocabulary after tokenization (pure punctuation/stopwords)
            return False
        return similarity < self.similarity_threshold

    def _build_episode(self) -> Episode:
        turns = self._turns
        beginning = turns[0].text
        end = turns[-1].text
        middle = "\n".join(t.text for t in turns[1:-1]) if len(turns) > 2 else (
            turns[0].text if len(turns) == 1 else ""
        )
        return Episode(beginning=beginning, middle=middle, end=end)
