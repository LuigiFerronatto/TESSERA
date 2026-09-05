"""Non-destructive containment for possible memory conflicts.

TESSERA does not yet have the validated state keys, validity semantics, or
supersession rules needed to decide that one memory invalidates another. The
compatibility resolver therefore preserves every retrieved candidate. Full
temporal conflict resolution remains a separate experiment under Issue #16.
"""

from typing import Any, Dict, List


class ConflictResolver:
    """Preserve possible-conflict evidence until deterministic rules exist."""

    @staticmethod
    def resolve_temporal_conflicts(retrieved_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return all candidates in their existing order without mutation.

        The former compatibility heuristic grouped factual/preference notes by
        their first entity and first tag, then retained only the newest note in
        each group. That key was neither a canonical state identity nor proof
        of supersession, so it could silently erase valid history. Until the
        temporal/state work defines auditable deterministic rules, a possible
        conflict is contained by preserving the evidence for downstream use.

        A shallow list copy preserves the established list return type while
        retaining the original candidate objects, IDs, provenance, scores, and
        ranking order. This method performs no persistence or network work.
        """
        return list(retrieved_memories)
