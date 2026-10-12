"""Synthetic-only tests: no provider, source-history, or real session inputs."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import UUID

import pytest

from tessera.interaction_ledger import (
    CAUSES, DeletePlan, InteractionEvent, InteractionLedger, LedgerError,
    LedgerPolicy, MAX_EVENT_BYTES, fingerprint_query,
)

PROJECT = str(UUID(int=1))
OTHER = str(UUID(int=2))
SESSION = str(UUID(int=3))
RUN = str(UUID(int=4))
NOW = 1700000000000
KEY = b"synthetic-ledger-hmac-key-only!!!x"


def event(number=100, **changes):
    values = dict(event_id=str(UUID(int=number)), project_id=PROJECT,
                  runtime="python", runtime_session_id=SESSION, tessera_run_id=RUN,
                  operation="search", occurred_at_ms=NOW, duration_ms=5,
                  status="success", result_count=1, verdict="found")
    values.update(changes)
    return InteractionEvent(**values)


def ledger(tmp_path, **policy):
    return InteractionLedger(tmp_path / "operational", project_id=PROJECT,
                             policy=LedgerPolicy(enabled=True, **policy))


def files(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def test_disabled_is_no_io_even_when_append_receives_invalid_payload(tmp_path):
    instance = InteractionLedger(tmp_path / "absent", project_id=PROJECT)
    assert instance.append({"raw_query": "FAKE_SECRET_DO_NOT_STORE"}) == "disabled"
    assert instance.events() == []
    assert instance.analytics()["enabled"] is False
    assert instance.plan_delete(action="clear").event_ids == ()
    assert instance.export()["events"] == []
    with pytest.raises(LedgerError, match="ledger_disabled"):
        instance.apply_delete(instance.plan_delete())
    assert not (tmp_path / "absent").exists()


def test_enabled_read_only_views_do_not_create_or_prune(tmp_path):
    instance = ledger(tmp_path, retention_seconds=1)
    assert instance.events(now_ms=NOW) == []
    assert instance.apply_delete(instance.plan_delete(now_ms=NOW)) == 0
    assert not instance.directory.exists()
    instance.append(event(), now_ms=NOW)
    before = files(tmp_path)
    assert instance.events(now_ms=NOW + 1000) == []
    assert instance.plan_delete(now_ms=NOW + 1000).event_ids == (event().event_id,)
    assert files(tmp_path) == before


def test_identity_round_trip_and_run_filter(tmp_path):
    instance = ledger(tmp_path)
    synthetic = event(evidence_ids=("ev_0123456789abcdef",), query_length=27, top_k=5)
    assert instance.append(synthetic, now_ms=NOW) == "recorded"
    result = instance.events(run_id=RUN, now_ms=NOW)[0]
    assert result == json.loads(json.dumps(asdict(synthetic)))
    assert instance.events(run_id=OTHER, now_ms=NOW) == []
    reopened = ledger(tmp_path)
    assert reopened.events(now_ms=NOW) == [result]
    assert instance.export(now_ms=NOW)["events"] == [result]


def test_project_and_policy_mismatch_fail_closed_without_modification(tmp_path):
    instance = ledger(tmp_path)
    instance.append(event(), now_ms=NOW)
    before = files(tmp_path)
    other = InteractionLedger(instance.directory, project_id=OTHER, policy=instance.policy)
    for action in (lambda: other.events(now_ms=NOW), lambda: other.analytics(now_ms=NOW),
                   lambda: other.append(event(project_id=OTHER), now_ms=NOW),
                   lambda: other.plan_delete(now_ms=NOW), lambda: other.export(now_ms=NOW)):
        with pytest.raises(LedgerError, match="project_or_policy_mismatch"):
            action()
    changed_policy = ledger(tmp_path, retention_seconds=99)
    with pytest.raises(LedgerError, match="project_or_policy_mismatch"):
        changed_policy.events(now_ms=NOW)
    with pytest.raises(LedgerError, match="project_mismatch"):
        instance.append(event(project_id=OTHER), now_ms=NOW)
    assert files(tmp_path) == before


def test_hash_is_project_separated_keyed_and_contains_no_query(tmp_path):
    query = "FAKE_API_KEY_TEST_ONLY_sk-012345 /home/fake/private-source.md"
    fingerprint = fingerprint_query(query, project_id=PROJECT, key=KEY)
    assert len(fingerprint) == 64
    assert fingerprint == fingerprint_query(query, project_id=PROJECT, key=KEY)
    assert fingerprint != fingerprint_query(query, project_id=OTHER, key=KEY)
    assert fingerprint != fingerprint_query(query, project_id=PROJECT, key=b"x" * 32)
    assert fingerprint != hashlib.sha256(query.encode()).hexdigest()
    instance = ledger(tmp_path)
    instance.append(event(query_fingerprint=fingerprint, query_length=len(query)), now_ms=NOW)
    material = b"".join(files(tmp_path).values()) + json.dumps(instance.export(now_ms=NOW)).encode()
    for value in (query.encode(), b"FAKE_API_KEY_TEST_ONLY", b"/home/fake", KEY):
        assert value not in material
    for field in ("raw_query", "transcript", "tool_payload", "tool_result", "memory_ids", "raw_content"):
        with pytest.raises(TypeError):
            event(**{field: query})


@pytest.mark.parametrize("field,value", [
    ("event_id", "FAKE_TOKEN"), ("project_id", "/tmp/private"),
    ("runtime_session_id", "person@example.invalid"), ("tessera_run_id", "run-fake"),
    ("operation", "context"), ("runtime", "http"), ("cause", "FAKE_CREDENTIAL"),
    ("status", "custom"), ("duration_ms", float("nan")), ("duration_ms", float("inf")),
    ("duration_ms", True), ("duration_ms", 10**1000), ("duration_ms", -1), ("result_count", -1),
    ("result_count", True), ("occurred_at_ms", "now"), ("top_k", 0),
    ("query_length", 100001), ("query_fingerprint", "raw fake query"),
    ("evidence_ids", ("/tmp/fake-secret.md",)), ("evidence_ids", ["ev_0123456789abcdef"]),
    ("evidence_ids", tuple("ev_%016x" % i for i in range(33))),
    ("write_disposition", "written"), ("schema_version", 2), ("schema_version", True),
])
def test_event_input_rejection_is_bounded_and_never_echoes_data(field, value):
    with pytest.raises(LedgerError) as error:
        event(**{field: value})
    assert str(error.value) == "invalid_" + field
    assert len(str(error.value)) < 60


@pytest.mark.parametrize("policy", [{"enabled": 1}, {"max_events": 0}, {"max_events": 10001},
                                    {"retention_seconds": 0}, {"retention_seconds": 31536001}])
def test_policy_rejects_unbounded_or_ambiguous_options(policy):
    with pytest.raises(LedgerError):
        LedgerPolicy(**policy)


def test_duplicate_event_is_idempotent_conflict_rolls_back(tmp_path):
    instance = ledger(tmp_path)
    item = event(evidence_ids=("ev_0000000000000002", "ev_0000000000000001"))
    assert instance.append(item, now_ms=NOW) == "recorded"
    assert instance.append(replace(item, evidence_ids=tuple(reversed(item.evidence_ids)), duration_ms=5.0), now_ms=NOW) == "duplicate"
    before = files(tmp_path)
    with pytest.raises(LedgerError, match="event_id_conflict"):
        instance.append(replace(item, duration_ms=9), now_ms=NOW)
    assert files(tmp_path) == before
    assert len(instance.events(now_ms=NOW)) == 1


def test_concurrent_initialization_unique_and_duplicate_writes(tmp_path):
    def record(number):
        return ledger(tmp_path).append(event(number=number), now_ms=NOW)
    numbers = list(range(100, 120)) * 3
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(record, numbers))
    assert statuses.count("recorded") == 20
    assert statuses.count("duplicate") == 40
    assert ledger(tmp_path).analytics(now_ms=NOW)["event_count"] == 20
    assert not list((tmp_path / "operational").glob(".ledger-bootstrap-*"))


def test_concurrent_processes_are_serialized(tmp_path):
    instance = ledger(tmp_path)
    instance.append(event(), now_ms=NOW)
    program = '''
import sys
from uuid import UUID
from tessera.interaction_ledger import InteractionLedger, InteractionEvent, LedgerPolicy
ledger = InteractionLedger(sys.argv[1], project_id=sys.argv[2], policy=LedgerPolicy(enabled=True))
for number in range(200, 210):
    event = InteractionEvent(str(UUID(int=number)), sys.argv[2], "python", sys.argv[3], sys.argv[4], "search", 1700000000000, 5, "success")
    ledger.append(event, now_ms=1700000000000)
'''
    processes = [subprocess.Popen([sys.executable, "-c", program, str(instance.directory), PROJECT, SESSION, RUN], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        assert process.returncode == 0, (stdout, stderr)
    assert instance.analytics(now_ms=NOW)["event_count"] == 11


def test_retention_count_is_deterministic_for_out_of_order_events(tmp_path):
    instance = ledger(tmp_path, max_events=3, retention_seconds=2)
    for number in (104, 101, 105, 100, 102, 103):
        instance.append(event(number=number), now_ms=NOW)
    assert [row["event_id"] for row in instance.events(now_ms=NOW)] == [str(UUID(int=n)) for n in (105, 104, 103)]
    assert instance.append(event(number=106, occurred_at_ms=NOW - 2000), now_ms=NOW) == "expired"
    assert instance.append(event(number=102), now_ms=NOW) == "outside_count_window"
    with pytest.raises(LedgerError, match="future_event"):
        instance.append(event(occurred_at_ms=NOW + 1), now_ms=NOW)
    instance.append(event(number=200, occurred_at_ms=NOW + 2000), now_ms=NOW + 2000)
    assert len(instance.events(now_ms=NOW + 2000)) == 1
    with sqlite3.connect(instance.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_delete_plans_stale_forged_cross_project_and_exact_clear(tmp_path):
    instance = ledger(tmp_path)
    source = tmp_path / "source.md"
    source.write_text("Synthetic canonical source", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"evidence": "synthetic"}', encoding="utf-8")
    protected = (source.read_bytes(), evidence.read_bytes())
    instance.append(event(), now_ms=NOW)
    first = instance.plan_delete(action="clear", now_ms=NOW)
    instance.append(event(number=101), now_ms=NOW)
    with pytest.raises(LedgerError, match="stale_delete_plan"):
        instance.apply_delete(first)
    plan = instance.plan_delete(action="clear", now_ms=NOW)
    for forged in (replace(plan, project_id=OTHER), replace(plan, event_ids=first.event_ids), replace(plan, snapshot_digest="x")):
        with pytest.raises(LedgerError):
            instance.apply_delete(forged)
    exported = instance.export(now_ms=NOW)
    assert len(exported["events"]) == 2
    assert instance.apply_delete(plan) == 2
    assert instance.analytics(now_ms=NOW)["event_count"] == 0
    with pytest.raises(LedgerError, match="stale_delete_plan"):
        instance.apply_delete(plan)
    assert (source.read_bytes(), evidence.read_bytes()) == protected


def test_explicit_retention_applies_only_expired_rows(tmp_path):
    instance = ledger(tmp_path, retention_seconds=1)
    instance.append(event(occurred_at_ms=NOW - 900), now_ms=NOW)
    instance.append(event(number=101), now_ms=NOW)
    plan = instance.plan_delete(now_ms=NOW + 100)
    assert plan.action == "retention"
    assert plan.event_ids == (event().event_id,)
    assert instance.apply_delete(plan) == 1
    assert [row["event_id"] for row in instance.events(now_ms=NOW + 100)] == [event(number=101).event_id]


def test_search_denominators_percentiles_and_failure_causes_are_explicit(tmp_path):
    instance = ledger(tmp_path)
    fingerprint = fingerprint_query("synthetic search", project_id=PROJECT, key=KEY)
    for number, result, verdict, duration, status in (
        (100, 2, "found", 1, "success"), (101, 0, "none", 2, "success"),
        (102, 1, "weak", 3, "partial"), (103, 0, "error", 100, "timeout"),
    ):
        instance.append(event(number=number, result_count=result, verdict=verdict,
                              duration_ms=duration, status=status, query_fingerprint=fingerprint), now_ms=NOW)
    for number, cause in enumerate(sorted(CAUSES), 200):
        instance.append(event(number=number, operation="inspect", cause=cause, status="error", verdict="error"), now_ms=NOW)
    for number, disposition in enumerate(("written", "rejected", "no_write"), 300):
        instance.append(event(number=number, operation="remember", write_disposition=disposition), now_ms=NOW)
    result = instance.analytics(now_ms=NOW)
    assert result["search_count"] == 4
    assert result["completed_search_count"] == 3
    assert result["zero_result_rate"] == 1 / 3
    assert result["weak_result_rate"] == 1 / 3
    assert result["repeated_query_rate"] == .75
    assert result["latency_p50_ms"] == 2
    assert result["latency_p95_ms"] == 100
    assert result["cause_counts"] == {cause: 1 for cause in CAUSES}
    assert ledger(tmp_path / "empty").analytics(now_ms=NOW)["zero_result_rate"] is None


def test_arbitrary_files_databases_symlinks_and_locked_store_fail_closed(tmp_path):
    instance = ledger(tmp_path)
    instance.directory.mkdir()
    instance.path.write_text("Synthetic source must not be replaced", encoding="utf-8")
    before = files(tmp_path)
    with pytest.raises(LedgerError):
        instance.append(event(), now_ms=NOW)
    assert files(tmp_path) == before
    other = ledger(tmp_path / "other")
    other.directory.mkdir(parents=True)
    with sqlite3.connect(other.path) as connection:
        connection.execute("CREATE TABLE canonical (body TEXT)")
    before = files(tmp_path)
    with pytest.raises(LedgerError, match="unrecognized_ledger"):
        other.append(event(), now_ms=NOW)
    assert files(tmp_path) == before
    linked = ledger(tmp_path / "linked")
    linked.directory.mkdir(parents=True)
    linked.path.symlink_to(other.path)
    with pytest.raises(LedgerError, match="unsafe_ledger_path"):
        linked.events(now_ms=NOW)
    normal = ledger(tmp_path / "normal")
    normal.append(event(), now_ms=NOW)
    with sqlite3.connect(normal.path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(LedgerError, match="ledger_storage_unavailable"):
            normal.append(event(number=101), now_ms=NOW)
    assert len(normal.events(now_ms=NOW)) == 1


def test_page_bounds_and_event_size(tmp_path):
    instance = ledger(tmp_path)
    for value in (0, 1001, True, "1"):
        with pytest.raises(LedgerError, match="invalid_limit"):
            instance.events(limit=value, now_ms=NOW)
    payload = event(evidence_ids=tuple("ev_%016x" % i for i in range(32)), query_fingerprint="f" * 64, query_length=100000, top_k=1000)
    assert len(json.dumps(asdict(payload)).encode()) <= MAX_EVENT_BYTES


def test_normal_engine_does_not_collect_or_index_ledger(tmp_path):
    from tessera import TesseraEngine
    instance = ledger(tmp_path)
    engine = TesseraEngine(storage_dir=str(tmp_path / "memories"))
    engine.write_memory_note(mem_id="test/synthetic", mem_type="factual", episode_id="fixture", content="Synthetic orchard apples", tags=[], entities=[])
    engine.build_index()
    before = engine.retrieve_context("orchard apples")
    assert not instance.directory.exists()
    instance.append(event(query_fingerprint="e" * 64), now_ms=NOW)
    engine.build_index()
    assert engine.retrieve_context("orchard apples") == before
    assert all("interaction" not in str(value) for value in engine.node_ids)


def test_export_plan_is_read_only_complete_and_honest_about_truncation(tmp_path):
    instance = ledger(tmp_path)
    for number in range(100, 103):
        instance.append(event(number=number), now_ms=NOW)
    before = files(tmp_path)
    exported = instance.export(limit=1, now_ms=NOW)
    assert exported["truncated"] is True
    assert exported["eligible_count"] == 3
    assert len(exported["events"]) == 1
    complete = instance.export(limit=10000, now_ms=NOW)
    plan = instance.plan_export(now_ms=NOW)
    encoded = json.dumps(complete, sort_keys=True, separators=(",", ":")).encode()
    assert plan["event_count"] == 3
    assert plan["export_bytes"] == len(encoded)
    assert plan["export_digest"] == hashlib.sha256(encoded).hexdigest()
    assert plan["includes_raw_content"] is False
    assert files(tmp_path) == before


@pytest.mark.parametrize("change", [
    {"raw_query": "FAKE_SECRET_TEST_ONLY"}, {"project_id": OTHER},
    {"event_id": OTHER}, {"occurred_at_ms": NOW - 1},
])
def test_corrupted_rows_never_expose_raw_data_or_wrong_scope(tmp_path, change):
    instance = ledger(tmp_path)
    instance.append(event(), now_ms=NOW)
    payload = asdict(event())
    payload.update(change)
    with sqlite3.connect(instance.path) as connection:
        connection.execute("UPDATE events SET payload=?", (json.dumps(payload),))
    for read in (lambda: instance.events(now_ms=NOW), lambda: instance.analytics(now_ms=NOW),
                 lambda: instance.plan_delete(now_ms=NOW), lambda: instance.export(now_ms=NOW)):
        with pytest.raises(LedgerError, match="corrupt_ledger"):
            read()


def test_fingerprint_invalid_key_query_and_unicode_fail_closed():
    for query, key in (("x", b"short"), ("x" * 100001, KEY), ("\ud800", KEY)):
        with pytest.raises(LedgerError):
            fingerprint_query(query, project_id=PROJECT, key=key)


@pytest.mark.parametrize("operation", ["search", "evidence", "remember", "inspect", "index", "doctor"])
def test_each_existing_operation_can_emit_without_automatic_capture(tmp_path, operation):
    instance = ledger(tmp_path)
    assert instance.append(event(operation=operation), now_ms=NOW) == "recorded"
    assert instance.events(now_ms=NOW)[0]["operation"] == operation


def test_absent_verdict_is_unknown_rather_than_nonweak(tmp_path):
    instance = ledger(tmp_path)
    instance.append(event(verdict=None), now_ms=NOW)
    summary = instance.analytics(now_ms=NOW)
    assert summary["completed_search_count"] == 1
    assert summary["verdict_search_count"] == 0
    assert summary["weak_result_rate"] is None
    instance.append(event(number=101, verdict="weak"), now_ms=NOW)
    summary = instance.analytics(now_ms=NOW)
    assert summary["verdict_search_count"] == 1
    assert summary["weak_result_rate"] == 1.0


@pytest.mark.parametrize("suffix", ["", "-journal", "-wal", "-shm"])
@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo", "directory"])
def test_sqlite_paths_reject_links_and_nonregular_files_before_open(tmp_path, suffix, kind):
    instance = ledger(tmp_path)
    if suffix:
        instance.append(event(), now_ms=NOW)
    else:
        instance.directory.mkdir()
    victim = tmp_path / "synthetic-victim.txt"
    victim.write_bytes(b"FAKE-SOURCE-DO-NOT-CHANGE")
    target = Path(str(instance.path) + suffix)
    if kind == "symlink":
        target.symlink_to(victim)
    elif kind == "hardlink":
        os.link(victim, target)
    elif kind == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO creation is unavailable on this platform")
        os.mkfifo(target)
    else:
        target.mkdir()
    victim_digest = hashlib.sha256(victim.read_bytes()).hexdigest()
    before = instance.path.read_bytes() if suffix else None
    for action in (lambda: instance.events(now_ms=NOW),
                   lambda: instance.append(event(number=101), now_ms=NOW),
                   lambda: instance.plan_delete(action="clear", now_ms=NOW)):
        with pytest.raises(LedgerError, match="unsafe_ledger_path"):
            action()
    assert hashlib.sha256(victim.read_bytes()).hexdigest() == victim_digest
    if before is not None:
        assert instance.path.read_bytes() == before


@pytest.mark.parametrize("damage", ["oversized_value", "extra_rows"])
def test_ownership_metadata_read_is_bounded_before_rejection(tmp_path, monkeypatch, damage):
    instance = ledger(tmp_path)
    instance.append(event(), now_ms=NOW)
    with sqlite3.connect(instance.path) as connection:
        if damage == "oversized_value":
            connection.execute("UPDATE metadata SET value=?", ("FAKE_METADATA_" * 100000,))
        else:
            connection.executemany("INSERT INTO metadata VALUES (?)", (("extra",) for _ in range(1000)))
    queries = []
    real_connect = sqlite3.connect
    def traced_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        connection.set_trace_callback(queries.append)
        return connection
    monkeypatch.setattr(sqlite3, "connect", traced_connect)
    with pytest.raises(LedgerError, match="project_or_policy_mismatch"):
        instance.events(now_ms=NOW)
    ownership = [query.lower() for query in queries if "from metadata" in query.lower()]
    assert ownership == ["select substr(value, 1, 256) from metadata limit 2"]


def test_unowned_hot_journal_is_not_recovered_before_ownership_check(tmp_path):
    instance = ledger(tmp_path)
    instance.directory.mkdir()
    with sqlite3.connect(instance.path) as connection:
        connection.execute("CREATE TABLE source (body TEXT)")
        connection.executemany("INSERT INTO source VALUES (?)", (("x" * 1000,) for _ in range(100)))
    program = """
import os, sqlite3, sys
connection = sqlite3.connect(sys.argv[1])
connection.execute("PRAGMA cache_size=1")
connection.execute("BEGIN IMMEDIATE")
connection.execute("UPDATE source SET body=REPLACE(body, 'x', 'y')")
os._exit(0)
"""
    subprocess.run([sys.executable, "-c", program, str(instance.path)], check=True, timeout=10)
    assert Path(str(instance.path) + "-journal").exists()
    before = files(tmp_path)
    with pytest.raises(LedgerError):
        instance.append(event(), now_ms=NOW)
    assert files(tmp_path) == before


@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.parametrize("sidecars", [False, True])
def test_wal_mode_is_refused_before_any_sqlite_connection(tmp_path, monkeypatch, owned, sidecars):
    instance = ledger(tmp_path)
    if owned:
        instance.append(event(), now_ms=NOW)
    else:
        instance.directory.mkdir()
    connection = sqlite3.connect(instance.path)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.execute("CREATE TABLE synthetic_wal (value TEXT)")
        connection.execute("INSERT INTO synthetic_wal VALUES ('synthetic only')")
        connection.commit()
        if not sidecars:
            connection.close()
            assert not Path(str(instance.path) + "-wal").exists()
        else:
            assert Path(str(instance.path) + "-shm").exists()
        before = files(tmp_path)
        def forbidden_connect(*args, **kwargs):
            raise AssertionError("Unsupported WAL state reached SQLite")
        monkeypatch.setattr(sqlite3, "connect", forbidden_connect)
        for action in (lambda: instance.events(now_ms=NOW),
                       lambda: instance.append(event(number=101), now_ms=NOW),
                       lambda: instance.plan_delete(action="clear", now_ms=NOW)):
            with pytest.raises(LedgerError):
                action()
        assert files(tmp_path) == before
    finally:
        connection.close()
