"""Experimental opt-in operational events, independent of semantic memory.

No Engine, CLI or MCP hooks are installed by this module. Identities and
outcomes must be supplied by a trusted caller; this is not an access-control
service or a session lifecycle implementation. See docs/INTERACTION_LEDGER.md.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import time
from typing import Optional, Tuple
from uuid import UUID

SCHEMA_VERSION = 1
MAX_EVENT_BYTES = 4096
MAX_EVENTS = 10000
MAX_PAGE_SIZE = 1000
APPLICATION_ID = 0x544C4731
RUNTIMES = frozenset({"python", "cli", "mcp"})
OPERATIONS = frozenset({"search", "evidence", "remember", "inspect", "index", "doctor"})
STATUSES = frozenset({"success", "partial", "timeout", "cancelled", "error"})
CAUSES = frozenset({"empty_corpus", "scope_denied", "index_missing", "index_stale",
                   "unmatched", "provider_unavailable", "capability_unavailable",
                   "timeout", "cancelled", "configuration_mismatch", "transport_failure",
                   "server_failure", "malformed_request", "write_rejected", "unknown"})


class LedgerError(ValueError):
    """A bounded diagnostic code; never includes caller content or local paths."""


def _integer(value, name, minimum=0, maximum=2**53 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise LedgerError("invalid_" + name)


def _uuid(value, name):
    try:
        valid = type(value) is str and len(value) == 36 and str(UUID(value)) == value
    except (ValueError, AttributeError):
        valid = False
    if not valid:
        raise LedgerError("invalid_" + name)


def _choice(value, choices, name):
    if type(value) is not str or value not in choices:
        raise LedgerError("invalid_" + name)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint_query(query: str, *, project_id: str, key: bytes) -> str:
    """Compute a project-separated HMAC; never store the query or caller's key.

    Keys must be application-owned random bytes, not a provider credential.
    Fingerprints remain pseudonymous information, not anonymized content.
    """
    _uuid(project_id, "project_id")
    if type(key) is not bytes or not 32 <= len(key) <= 128:
        raise LedgerError("invalid_fingerprint_key")
    if type(query) is not str or len(query) > 100000:
        raise LedgerError("invalid_query")
    try:
        encoded = query.encode("utf-8")
    except UnicodeError:
        raise LedgerError("invalid_query") from None
    return hmac.new(key, b"tessera-ledger-v1\0" + project_id.encode("ascii") +
                    b"\0" + encoded, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class LedgerPolicy:
    enabled: bool = False
    max_events: int = 1000
    retention_seconds: int = 7 * 86400

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise LedgerError("invalid_enabled")
        _integer(self.max_events, "max_events", 1, MAX_EVENTS)
        _integer(self.retention_seconds, "retention_seconds", 1, 365 * 86400)


@dataclass(frozen=True)
class InteractionEvent:
    event_id: str
    project_id: str
    runtime: str
    runtime_session_id: str
    tessera_run_id: str
    operation: str
    occurred_at_ms: int
    duration_ms: float
    status: str
    result_count: int = 0
    verdict: Optional[str] = None
    cause: Optional[str] = None
    query_fingerprint: Optional[str] = None
    query_length: Optional[int] = None
    top_k: Optional[int] = None
    evidence_ids: Tuple[str, ...] = ()
    write_disposition: Optional[str] = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        for name in ("event_id", "project_id", "runtime_session_id", "tessera_run_id"):
            _uuid(getattr(self, name), name)
        _integer(self.schema_version, "schema_version", 1, 1)
        _choice(self.runtime, RUNTIMES, "runtime")
        _choice(self.operation, OPERATIONS, "operation")
        _choice(self.status, STATUSES, "status")
        _integer(self.occurred_at_ms, "occurred_at_ms")
        if type(self.duration_ms) not in (int, float) or not 0 <= self.duration_ms <= 86400000 or not math.isfinite(self.duration_ms):
            raise LedgerError("invalid_duration_ms")
        object.__setattr__(self, "duration_ms", float(self.duration_ms))
        _integer(self.result_count, "result_count", 0, 1000000)
        if self.verdict is not None:
            _choice(self.verdict, {"found", "weak", "none", "error"}, "verdict")
        if self.cause is not None:
            _choice(self.cause, CAUSES, "cause")
        if self.query_fingerprint is not None and (type(self.query_fingerprint) is not str or not re.fullmatch(r"[0-9a-f]{64}", self.query_fingerprint)):
            raise LedgerError("invalid_query_fingerprint")
        for name, minimum, maximum in (("query_length", 0, 100000), ("top_k", 1, 1000)):
            if getattr(self, name) is not None:
                _integer(getattr(self, name), name, minimum, maximum)
        if type(self.evidence_ids) is not tuple or len(self.evidence_ids) > 32:
            raise LedgerError("invalid_evidence_ids")
        if any(type(value) is not str or not re.fullmatch(r"ev_[0-9a-f]{16}", value) for value in self.evidence_ids):
            raise LedgerError("invalid_evidence_ids")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(self.evidence_ids))))
        if self.write_disposition is not None:
            _choice(self.write_disposition, {"written", "rejected", "no_write"}, "write_disposition")
            if self.operation != "remember":
                raise LedgerError("invalid_write_disposition")
        if len(_json(asdict(self)).encode("utf-8")) > MAX_EVENT_BYTES:
            raise LedgerError("event_too_large")


@dataclass(frozen=True)
class DeletePlan:
    project_id: str
    action: str
    as_of_ms: int
    snapshot_digest: str
    event_ids: Tuple[str, ...]


class InteractionLedger:
    """One project per database; disabled by default and no ambient discovery.

    Reads/plans never create storage or prune rows. Enabled appends atomically
    prune age/count overflow. Deduplication lasts only while an event is retained.
    SQLite serializes writers with a 250 ms busy timeout; errors are explicit.
    """

    def __init__(self, directory, *, project_id: str, policy=LedgerPolicy()):
        _uuid(project_id, "project_id")
        if type(policy) is not LedgerPolicy:
            raise LedgerError("invalid_policy")
        self.directory = Path(directory).absolute()
        self.path = self.directory / "interactions-v1.sqlite3"
        self.project_id = project_id
        self.policy = policy

    def _metadata(self):
        return _json({"schema_version": SCHEMA_VERSION, "project_id": self.project_id,
                      "max_events": self.policy.max_events,
                      "retention_seconds": self.policy.retention_seconds})

    def _check_path(self):
        # Preflight against accidental/malicious links in cooperative local
        # operation. This does not defeat a filesystem owner racing path swaps.
        for path in (self.directory, *self.directory.parents):
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(info.st_mode):
                raise LedgerError("unsafe_ledger_path")
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            try:
                info = path.lstat()
                if info.st_nlink > 1 and stat.S_ISREG(info.st_mode):
                    # Atomic bootstrap publication briefly has two links until
                    # its temporary name is removed. Recheck without opening it;
                    # persistent hard links still fail closed.
                    time.sleep(0.001)
                    info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise LedgerError("unsafe_ledger_path")
            if suffix in {"-wal", "-shm"}:
                raise LedgerError("unsupported_ledger_journal_mode")

    def _check_header(self):
        # A read-only SQLite connection can still update WAL shared memory.
        # Inspect only the fixed header, without SQLite, before ownership probes.
        with self.path.open("rb") as stream:
            header = stream.read(100)
        if (len(header) != 100 or header[:16] != b"SQLite format 3\0"
                or int.from_bytes(header[68:72], "big") != APPLICATION_ID):
            raise LedgerError("unrecognized_ledger")
        if header[18:20] != b"\x01\x01":
            raise LedgerError("unsupported_ledger_journal_mode")

    def _initialize(self):
        self._check_path()
        if self.path.exists():
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        # Build a complete database before atomically publishing it. Concurrent
        # initializers must never inspect a half-initialized database or overwrite
        # an existing source file/database. SQLite's own lock handles later writes.
        fd, name = tempfile.mkstemp(prefix=".ledger-bootstrap-", dir=self.directory)
        os.close(fd)
        try:
            connection = sqlite3.connect(name)
            try:
                connection.executescript(f"""
                    PRAGMA application_id={APPLICATION_ID};
                    CREATE TABLE metadata (value TEXT NOT NULL);
                    CREATE TABLE events (
                        event_id TEXT PRIMARY KEY, occurred_at_ms INTEGER NOT NULL,
                        payload TEXT NOT NULL CHECK(length(payload) <= {MAX_EVENT_BYTES}));
                    CREATE INDEX chronology ON events (occurred_at_ms, event_id);
                """)
                connection.execute("INSERT INTO metadata VALUES (?)", (self._metadata(),))
                connection.commit()
            finally:
                connection.close()
            try:
                os.link(name, self.path)
            except FileExistsError:
                pass
        finally:
            os.unlink(name)

    @contextmanager
    def _connection(self, *, write=False):
        connection = None
        try:
            self._check_path()
            if write:
                self._initialize()
                self._check_path()
            elif not self.path.exists():
                yield None
                return
            self._check_header()
            # Even a SELECT on an rw connection may recover a hot journal.
            # Probe ownership read-only first, so an unidentified/project-mismatched
            # database cannot be mutated merely by opening it for validation.
            connection = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True, timeout=0.25)
            if connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
                raise LedgerError("unrecognized_ledger")
            rows = connection.execute("SELECT substr(value, 1, 256) FROM metadata LIMIT 2").fetchall()
            if rows != [(self._metadata(),)]:
                raise LedgerError("project_or_policy_mismatch")
            if write:
                connection.close()
                connection = None
                self._check_path()
                connection = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=0.25)
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            if write:
                connection.commit()
        except (OSError, sqlite3.Error):
            raise LedgerError("ledger_storage_unavailable") from None
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _now(now_ms):
        result = int(time.time() * 1000) if now_ms is None else now_ms
        _integer(result, "now_ms")
        return result

    def _cutoff(self, now_ms):
        return now_ms - self.policy.retention_seconds * 1000

    def append(self, event: InteractionEvent, *, now_ms=None) -> str:
        if not self.policy.enabled:
            return "disabled"
        if type(event) is not InteractionEvent:
            raise LedgerError("invalid_event")
        # Revalidate even a dataclass modified by low-level caller code.
        event = InteractionEvent(**asdict(event))
        if event.project_id != self.project_id:
            raise LedgerError("project_mismatch")
        now = self._now(now_ms)
        if event.occurred_at_ms > now:
            raise LedgerError("future_event")
        if event.occurred_at_ms <= self._cutoff(now):
            return "expired"
        payload = _json(asdict(event))
        with self._connection(write=True) as connection:
            existing = connection.execute("SELECT payload FROM events WHERE event_id=?", (event.event_id,)).fetchone()
            if existing and existing[0] != payload:
                raise LedgerError("event_id_conflict")
            connection.execute("INSERT OR IGNORE INTO events VALUES (?, ?, ?)", (event.event_id, event.occurred_at_ms, payload))
            connection.execute("DELETE FROM events WHERE occurred_at_ms <= ?", (self._cutoff(now),))
            connection.execute("""DELETE FROM events WHERE event_id IN (
                SELECT event_id FROM events ORDER BY occurred_at_ms DESC, event_id DESC
                LIMIT -1 OFFSET ?)""", (self.policy.max_events,))
            retained = connection.execute("SELECT 1 FROM events WHERE event_id=?", (event.event_id,)).fetchone()
        return "duplicate" if existing else ("recorded" if retained else "outside_count_window")

    def events(self, *, limit=100, run_id=None, now_ms=None):
        """Return newest retained events, ordered deterministically by time then ID."""
        _integer(limit, "limit", 1, MAX_PAGE_SIZE)
        if run_id is not None:
            _uuid(run_id, "run_id")
        return self._events(now_ms=now_ms, run_id=run_id)[:limit]

    def _events(self, *, now_ms=None, run_id=None):
        if not self.policy.enabled:
            return []
        now = self._now(now_ms)
        with self._connection() as connection:
            if connection is None:
                return []
            rows = self._snapshot(connection)
        events = [json.loads(row[2]) for row in rows if self._cutoff(now) < row[1] <= now]
        return [event for event in events if run_id is None or event["tessera_run_id"] == run_id]

    def analytics(self, *, now_ms=None):
        events = self._events(now_ms=now_ms)
        searches = [event for event in events if event["operation"] == "search"]
        completed = [event for event in searches if event["status"] in {"success", "partial"}]
        assessed = [event for event in completed if event["verdict"] in {"found", "weak", "none"}]
        fingerprints = [event["query_fingerprint"] for event in searches if event["query_fingerprint"] is not None]
        latencies = sorted(event["duration_ms"] for event in searches)
        def ratio(count, total):
            return count / total if total else None
        return {
            "schema_version": SCHEMA_VERSION, "enabled": self.policy.enabled,
            "event_count": len(events), "search_count": len(searches),
            "completed_search_count": len(completed),
            "zero_result_rate": ratio(sum(event["result_count"] == 0 for event in completed), len(completed)),
            "verdict_search_count": len(assessed),
            "weak_result_rate": ratio(sum(event["verdict"] == "weak" for event in assessed), len(assessed)),
            "fingerprinted_search_count": len(fingerprints),
            "repeated_query_rate": ratio(len(fingerprints) - len(set(fingerprints)), len(fingerprints)),
            "latency_p50_ms": latencies[math.ceil(len(latencies) * .50) - 1] if latencies else None,
            "latency_p95_ms": latencies[math.ceil(len(latencies) * .95) - 1] if latencies else None,
            "status_counts": dict(sorted(Counter(event["status"] for event in events).items())),
            "cause_counts": dict(sorted(Counter(event["cause"] for event in events if event["cause"]).items())),
            "operation_counts": dict(sorted(Counter(event["operation"] for event in events).items())),
            "runtime_counts": dict(sorted(Counter(event["runtime"] for event in events).items())),
        }

    def export(self, *, limit=100, now_ms=None):
        """Return bounded minimized data to the caller; never write/upload a file."""
        _integer(limit, "limit", 1, MAX_EVENTS)
        events = self._events(now_ms=now_ms)
        return {"schema_version": SCHEMA_VERSION, "project_id": self.project_id,
                "eligible_count": len(events), "truncated": len(events) > limit,
                "events": events[:limit]}

    def plan_export(self, *, now_ms=None):
        """Describe a full bounded export without writing a destination file."""
        data = self.export(limit=MAX_EVENTS, now_ms=now_ms)
        encoded = _json(data).encode("utf-8")
        return {"project_id": self.project_id, "event_count": data["eligible_count"],
                "export_bytes": len(encoded),
                "export_digest": hashlib.sha256(encoded).hexdigest(),
                "includes_raw_content": False}

    def _snapshot(self, connection):
        if connection is None:
            return []
        # Bound reads too, including when a damaged or externally edited file is
        # supplied. Validate persisted content before returning it to a caller.
        rows = connection.execute("""SELECT event_id, occurred_at_ms,
            substr(payload, 1, ?) FROM events
            ORDER BY occurred_at_ms DESC, event_id DESC LIMIT ?""",
            (MAX_EVENT_BYTES + 1, self.policy.max_events + 1)).fetchall()
        if len(rows) > self.policy.max_events:
            raise LedgerError("ledger_limit_exceeded")
        try:
            for event_id, occurred, payload in rows:
                if len(payload.encode("utf-8")) > MAX_EVENT_BYTES:
                    raise LedgerError("corrupt_ledger")
                decoded = json.loads(payload)
                if type(decoded.get("evidence_ids")) is not list:
                    raise LedgerError("corrupt_ledger")
                decoded["evidence_ids"] = tuple(decoded["evidence_ids"])
                event = InteractionEvent(**decoded)
                if (event.project_id != self.project_id or event.event_id != event_id
                        or event.occurred_at_ms != occurred or _json(asdict(event)) != payload):
                    raise LedgerError("corrupt_ledger")
        except (TypeError, ValueError, AttributeError):
            raise LedgerError("corrupt_ledger") from None
        return rows

    def _plan(self, rows, action, now):
        _choice(action, {"clear", "retention"}, "action")
        digest = hashlib.sha256(_json(rows).encode("utf-8")).hexdigest()
        targets = tuple(row[0] for offset, row in enumerate(rows) if action == "clear" or row[1] <= self._cutoff(now) or offset >= self.policy.max_events)
        return DeletePlan(self.project_id, action, now, digest, targets)

    def plan_delete(self, *, action="retention", now_ms=None):
        """Plan deletion of ledger rows only; expired rows remain on disk until pruning."""
        now = self._now(now_ms)
        if not self.policy.enabled:
            return self._plan([], action, now)
        with self._connection() as connection:
            return self._plan(self._snapshot(connection), action, now)

    def apply_delete(self, plan: DeletePlan) -> int:
        """Explicitly apply an exact snapshot plan; stale or altered plans fail closed.

        This is logical SQLite row deletion, not secure erasure of free pages,
        filesystem snapshots or backups. Sources and evidence are never opened.
        """
        if not self.policy.enabled:
            raise LedgerError("ledger_disabled")
        if type(plan) is not DeletePlan or plan.project_id != self.project_id:
            raise LedgerError("invalid_delete_plan")
        self._now(plan.as_of_ms)
        # A missing ledger cannot be created just to apply an empty plan.
        with self._connection() as connection:
            if connection is None:
                if plan != self._plan([], plan.action, plan.as_of_ms):
                    raise LedgerError("stale_delete_plan")
                return 0
        with self._connection(write=True) as connection:
            if plan != self._plan(self._snapshot(connection), plan.action, plan.as_of_ms):
                raise LedgerError("stale_delete_plan")
            connection.executemany("DELETE FROM events WHERE event_id=?", ((event_id,) for event_id in plan.event_ids))
        return len(plan.event_ids)
