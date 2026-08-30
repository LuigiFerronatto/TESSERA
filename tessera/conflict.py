"""
Temporal conflict resolver — QUMem / FinPerMA-style alignment.

Resolves chronological contradictions between competing preference/factual
notes about the same subject, keeping only the most recently updated one so
the agent never acts on stale user preferences.
"""

import datetime
from typing import Any, Dict, List, Tuple


class ConflictResolver:
    """
    Resolves chronological contradictions and preference updates.
    Ensures temporal alignment so the agent doesn't rely on obsolete
    preferences once a newer, contradicting note exists.
    """

    @staticmethod
    def resolve_temporal_conflicts(retrieved_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifies conflicting preferences/facts about the same subject and keeps
        only the most recently updated one, building a clean trajectory of state.
        """
        resolved = []
        seen_entities_actions: Dict[str, Tuple[datetime.datetime, Dict[str, Any]]] = {}

        for memory in retrieved_memories:
            mem_type = memory.get("type")
            frontmatter = memory.get("frontmatter", {})

            # Procedural anchors don't suffer temporal obsolescence like preferences do.
            if mem_type == "procedural_anchor":
                resolved.append(memory)
                continue

            updated_at_str = frontmatter.get(
                "last_updated_at", frontmatter.get("created_at", "1970-01-01T00:00:00Z")
            )
            try:
                dt = datetime.datetime.fromisoformat(updated_at_str)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                updated_at = dt
            except Exception:
                updated_at = datetime.datetime.min

            tags = frontmatter.get("tags", [])
            entities = [ent.get("name") for ent in frontmatter.get("entities", [])]

            if not entities:
                resolved.append(memory)
                continue

            # Conflict-subject key: entity name + first thematic tag (e.g. "alex_database").
            conflict_subject = f"{entities[0].lower()}_" + "_".join([t.lower() for t in tags[:1]])

            if conflict_subject in seen_entities_actions:
                prev_time, _prev_mem = seen_entities_actions[conflict_subject]
                if updated_at > prev_time:
                    seen_entities_actions[conflict_subject] = (updated_at, memory)
            else:
                seen_entities_actions[conflict_subject] = (updated_at, memory)

        for _subject, (_dt, mem) in seen_entities_actions.items():
            resolved.append(mem)

        return resolved
