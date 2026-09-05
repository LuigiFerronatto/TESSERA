"""P0 regression coverage for non-destructive conflict containment (#16)."""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, Dict, List, Optional

from tessera import Entity, TesseraEngine
from tessera.conflict import ConflictResolver


def _candidate(
    memory_id: str,
    content: str,
    updated_at: str,
    *,
    memory_type: str = "preference",
    entity: str = "User",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    drawer = "facts" if memory_type == "factual" else "preferences"
    return {
        "id": memory_id,
        "type": memory_type,
        "body": content,
        "score": 1.0,
        "frontmatter": {
            "drawer": drawer,
            "last_updated_at": updated_at,
            "tags": list(tags or ["reports"]),
            "entities": [{"name": entity}],
            "source_document_id": f"doc-{memory_id}",
            "source_version": f"sha256:{memory_id}",
            "source_spans": [{"start_line": 1, "end_line": 1}],
            "relations": [{"type": "derived_from", "target": f"episode-{memory_id}"}],
        },
    }


def _ids(memories: List[Dict[str, Any]]) -> List[str]:
    return [memory["id"] for memory in memories]


def test_three_chronological_preferences_all_survive() -> None:
    memories = [
        _candidate("P1", "Prefer concise reports.", "2026-01-01T00:00:00Z"),
        _candidate("P2", "Prefer more detail than before.", "2026-02-01T00:00:00Z"),
        _candidate(
            "P3",
            "Prefer highly detailed reports for quarterly reviews.",
            "2026-03-01T00:00:00Z",
        ),
    ]

    assert _ids(ConflictResolver.resolve_temporal_conflicts(memories)) == ["P1", "P2", "P3"]


def test_context_specific_preference_does_not_delete_broad_preference() -> None:
    memories = [
        _candidate("P1", "Prefer concise reports.", "2026-01-01T00:00:00Z"),
        _candidate(
            "P2",
            "For board presentations, prefer detailed reports.",
            "2026-02-01T00:00:00Z",
        ),
    ]

    assert _ids(ConflictResolver.resolve_temporal_conflicts(memories)) == ["P1", "P2"]


def test_unresolved_contradiction_preserves_both_candidates() -> None:
    memories = [
        _candidate("P1", "User prefers concise reports.", "2026-01-01T00:00:00Z"),
        _candidate("P2", "User prefers detailed reports.", "2026-02-01T00:00:00Z"),
    ]

    assert _ids(ConflictResolver.resolve_temporal_conflicts(memories)) == ["P1", "P2"]


def test_false_coarse_key_collision_preserves_unrelated_candidates() -> None:
    memories = [
        _candidate("C1", "Prefer concise reports.", "2026-01-01T00:00:00Z"),
        _candidate("C2", "Prefer reports delivered by email.", "2026-02-01T00:00:00Z"),
    ]

    assert _ids(ConflictResolver.resolve_temporal_conflicts(memories)) == ["C1", "C2"]


def test_old_but_valid_fact_survives_newer_unrelated_observation() -> None:
    memories = [
        _candidate(
            "F1",
            "The quarterly review happens in April.",
            "2025-01-01T00:00:00Z",
            memory_type="factual",
        ),
        _candidate(
            "F2",
            "The quarterly review uses a slide deck.",
            "2026-01-01T00:00:00Z",
            memory_type="factual",
        ),
    ]

    assert _ids(ConflictResolver.resolve_temporal_conflicts(memories)) == ["F1", "F2"]


def test_metadata_order_cannot_trigger_destructive_loss() -> None:
    memories = [
        _candidate("P1", "Prefer concise reports.", "2026-01-01T00:00:00Z", tags=["reports", "style"]),
        _candidate("P2", "Prefer detailed board reports.", "2026-02-01T00:00:00Z", tags=["style", "reports"]),
    ]

    assert _ids(ConflictResolver.resolve_temporal_conflicts(memories)) == ["P1", "P2"]


def test_candidate_identity_order_and_provenance_are_unchanged() -> None:
    memories = [
        _candidate("P1", "Prefer concise reports.", "2026-01-01T00:00:00Z"),
        _candidate("P2", "Prefer detailed reports.", "2026-02-01T00:00:00Z"),
    ]
    provenance_before = [memory["frontmatter"].copy() for memory in memories]

    resolved = ConflictResolver.resolve_temporal_conflicts(memories)

    assert resolved == memories
    assert resolved is not memories
    assert all(after is before for after, before in zip(resolved, memories))
    assert [memory["frontmatter"] for memory in resolved] == provenance_before


def test_retrieval_does_not_rewrite_source_files(tmp_path: Path) -> None:
    engine = TesseraEngine(storage_dir=str(tmp_path))
    for memory_id, content in (
        ("preferences/p1", "Prefer concise reports."),
        ("preferences/p2", "Prefer detailed reports."),
    ):
        engine.write_preference(
            mem_id=memory_id,
            episode_id="episode/reports",
            content=content,
            tags=["reports"],
            entities=[Entity("User", "Report preference owner.")],
        )
    engine.build_index(use_cache=False)
    source_files = sorted(tmp_path.glob("preferences/*.md"))
    before = {path: path.read_bytes() for path in source_files}

    engine.retrieve_context("reports", top_n=10, resolve_conflicts=True)

    assert {path: path.read_bytes() for path in source_files} == before


def test_normal_retrieval_preserves_ranking_and_only_stops_filtering(tmp_path: Path) -> None:
    engine = TesseraEngine(storage_dir=str(tmp_path))
    for memory_id, content in (
        ("preferences/p1", "Prefer concise quarterly reports."),
        ("preferences/p2", "Prefer detailed quarterly reports for the board."),
        ("preferences/p3", "Prefer quarterly reports delivered as slides."),
    ):
        engine.write_preference(
            mem_id=memory_id,
            episode_id="episode/reports",
            content=content,
            tags=["reports"],
            entities=[Entity("User", "Report preference owner.")],
        )
    engine.build_index(use_cache=False)

    unresolved = engine.retrieve_context("quarterly reports", top_n=10, resolve_conflicts=False)
    contained = engine.retrieve_context("quarterly reports", top_n=10, resolve_conflicts=True)

    assert _ids(contained) == _ids(unresolved)
    assert [memory["score"] for memory in contained] == [memory["score"] for memory in unresolved]


def test_engine_default_preserves_preference_trajectory(tmp_path: Path) -> None:
    engine = TesseraEngine(storage_dir=str(tmp_path))
    for index, content in enumerate(
        (
            "Prefer concise quarterly reports.",
            "Prefer more detail than before in quarterly reports.",
            "Prefer highly detailed quarterly reports for board reviews.",
        ),
        start=1,
    ):
        engine.write_preference(
            mem_id=f"preferences/p{index}",
            episode_id="episode/reports",
            content=content,
            tags=["reports"],
            entities=[Entity("User", "Report preference owner.")],
        )
    engine.build_index(use_cache=False)

    assert set(_ids(engine.retrieve_context("quarterly reports", top_n=10))) == {
        "preferences/p1",
        "preferences/p2",
        "preferences/p3",
    }


def test_resolver_does_not_duplicate_candidates() -> None:
    memories = [
        _candidate("P1", "Prefer concise reports.", "2026-01-01T00:00:00Z"),
        _candidate("P2", "Prefer detailed reports.", "2026-02-01T00:00:00Z"),
    ]

    resolved = ConflictResolver.resolve_temporal_conflicts(memories)

    assert len(resolved) == len(memories)
    assert len({id(memory) for memory in resolved}) == len(memories)


def test_resolver_requires_no_provider_or_network(monkeypatch) -> None:
    def fail_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("network access is not allowed")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    memories = [_candidate("P1", "Prefer concise reports.", "2026-01-01T00:00:00Z")]

    assert ConflictResolver.resolve_temporal_conflicts(memories) == memories
