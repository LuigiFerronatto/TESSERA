#!/usr/bin/env python3
"""Synthetic ledger mechanics/overhead smoke; emits JSON and uses temp files only."""
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import sqlite3
import statistics
import tempfile
import time
from uuid import UUID

from tessera.interaction_ledger import (
    InteractionEvent, InteractionLedger, LedgerPolicy, fingerprint_query,
)


def distribution(values):
    ordered = sorted(values)
    return {"p50_ms": statistics.median(values),
            "p95_ms": ordered[math.ceil(len(ordered) * .95) - 1],
            "max_ms": max(values)}


def main():
    now = 1700000000000
    project = str(UUID(int=1))
    query = "FAKE_SECRET_SYNTHETIC_smoke-only /fake/private-path"
    fingerprint = fingerprint_query(query, project_id=project, key=b"synthetic-key-for-smoke-only!!!!!x")
    events = [InteractionEvent(str(UUID(int=100 + number)), project, "python",
                               str(UUID(int=2)), str(UUID(int=3)), "search", now,
                               number % 100, "success", number % 3,
                               query_fingerprint=fingerprint) for number in range(1000)]
    with tempfile.TemporaryDirectory(prefix="tessera-ledger-smoke-") as root:
        path = Path(root)
        disabled = InteractionLedger(path / "disabled", project_id=project)
        disabled_times = []
        for event in events:
            start = time.perf_counter()
            assert disabled.append(event, now_ms=now) == "disabled"
            disabled_times.append((time.perf_counter() - start) * 1000)
        assert not disabled.directory.exists()
        enabled = InteractionLedger(path / "enabled", project_id=project,
                                    policy=LedgerPolicy(enabled=True, max_events=250))
        enabled_times = []
        at_capacity_bytes = None
        for number, event in enumerate(events):
            start = time.perf_counter()
            assert enabled.append(event, now_ms=now) == "recorded"
            enabled_times.append((time.perf_counter() - start) * 1000)
            if number == 249:
                at_capacity_bytes = enabled.path.stat().st_size
        assert enabled.append(events[-1], now_ms=now) == "duplicate"
        start = time.perf_counter()
        stats = enabled.analytics(now_ms=now)
        analytics_ms = (time.perf_counter() - start) * 1000
        assert stats["event_count"] == 250
        assert stats["search_count"] == 250
        data = enabled.export(limit=10000, now_ms=now)
        assert data["truncated"] is False
        assert len({event["event_id"] for event in data["events"]}) == 250
        raw = enabled.path.read_bytes()
        assert query.encode() not in raw and b"FAKE_SECRET" not in raw
        retained_bytes = enabled.path.stat().st_size
        clear = enabled.plan_delete(action="clear", now_ms=now)
        assert enabled.apply_delete(clear) == 250
        assert enabled.analytics(now_ms=now)["event_count"] == 0
        print(json.dumps({
            "applicability": "SMOKE_ONLY", "input": "synthetic temporary store",
            "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
            "events_submitted": len(events), "count_limit": 250,
            "retained_unique_events": stats["event_count"], "expected_pruned_events": 750,
            "unexpected_loss": 0, "duplicate_rows": 0, "fake_secret_leaks": 0,
            "event_json_bytes": len(json.dumps(asdict(events[0])).encode()),
            "database_bytes_at_250_appends": at_capacity_bytes,
            "database_bytes_at_1000_appends": retained_bytes,
            "disabled_append": distribution(disabled_times),
            "enabled_append_including_first_initialization": distribution(enabled_times),
            "analytics_250_events_ms": analytics_ms,
            "explicit_clear_removed": 250,
            "limits": "Local wall-clock sample, no production/session integration or latency gate. Logical deletion is not secure erasure."
        }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
