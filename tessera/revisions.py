"""Opt-in, durable observed source history, independent of disposable indexes.

The archive contains historical source text, not independent live memories or
truth/validity decisions. Only INSERT is supported; retention is an explicit
operator responsibility. SQLite transactions make each snapshot and its
provenance atomic, with FULL synchronous durability and no provider dependency.
"""
from __future__ import annotations

from contextlib import contextmanager
import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterator, List, Optional

from .canonical import CanonicalMetadata, compute_sha256
from .evidence import _evidence_fingerprint, evidence_from_canonical
from .source_formats import split_source

HISTORY_DIRECTORY = ".tessera_history"
HISTORY_SCHEMA_VERSION = 1


class RevisionHistoryError(RuntimeError):
    """History could not be preserved or verified; never silently fall back.

    ``source_committed`` distinguishes failure before replacement from failure
    archiving the new version after a successful source replacement.
    """

    def __init__(self, message: str, *, source_committed: bool = False):
        super().__init__(message)
        self.source_committed = source_committed


class RevisionHistory:
    """Append-only full-text revisions and issued evidence; lazy disk creation."""

    def __init__(self, storage_dir: str, index_dir: str):
        self.root = Path(storage_dir).expanduser().absolute() / HISTORY_DIRECTORY
        self.path = self.root / "revisions.sqlite3"
        index = Path(index_dir).resolve()
        root = self.root.resolve()
        if index == root or index in root.parents or root in index.parents:
            raise ValueError("durable revision history and disposable index must not overlap")

    def _check_paths(self) -> None:
        if self.root.is_symlink() or self.path.is_symlink():
            raise RevisionHistoryError("revision history must not be a symlink")
        # SQLite journal files are created alongside the database.
        for suffix in ("-journal", "-wal", "-shm"):
            if Path(str(self.path) + suffix).is_symlink():
                raise RevisionHistoryError("revision history journal must not be a symlink")

    @contextmanager
    def _connect(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        self._check_paths()
        connection = None
        try:
            if write:
                self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
                connection = sqlite3.connect(str(self.path), timeout=30)
                connection.execute("PRAGMA synchronous = FULL")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in (0, HISTORY_SCHEMA_VERSION):
                    raise RevisionHistoryError(f"unsupported revision history schema: {version}")
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS revisions (
                        document_id TEXT NOT NULL, document_hash TEXT NOT NULL,
                        raw_text TEXT NOT NULL, content_hash TEXT NOT NULL,
                        source_format TEXT NOT NULL,
                        PRIMARY KEY (document_id, document_hash));
                    CREATE TABLE IF NOT EXISTS observations (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id TEXT NOT NULL, document_hash TEXT NOT NULL,
                        memory_id TEXT NOT NULL, source_path TEXT NOT NULL,
                        observed_at TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS evidence (
                        evidence_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                        document_id TEXT NOT NULL, document_hash TEXT NOT NULL);
                    CREATE INDEX IF NOT EXISTS observations_path ON observations(source_path, sequence);
                """)
                for table in ("revisions", "observations", "evidence"):
                    for action in ("UPDATE", "DELETE"):
                        connection.execute(
                            f"CREATE TRIGGER IF NOT EXISTS prevent_{table}_{action.lower()} "
                            f"BEFORE {action} ON {table} BEGIN "
                            "SELECT RAISE(ABORT, 'revision history is append-only'); END"
                        )
                connection.execute(f"PRAGMA user_version = {HISTORY_SCHEMA_VERSION}")
            else:
                connection = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
                if connection.execute("PRAGMA user_version").fetchone()[0] != HISTORY_SCHEMA_VERSION:
                    raise RevisionHistoryError("unsupported revision history schema")
            with connection:
                yield connection
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            raise RevisionHistoryError(f"revision history unavailable or invalid: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()

    def check_available(self) -> None:
        """Preflight existing archive before a potentially destructive source write."""
        self._check_paths()
        if self.path.exists():
            with self._connect() as connection:
                connection.execute("SELECT COUNT(*) FROM revisions").fetchone()

    def capture(self, metadata: CanonicalMetadata, raw_text: str) -> None:
        """Preserve one observed exact text version and its canonical evidence."""
        source = metadata.source
        _frontmatter, body = split_source(raw_text, source_format=source.format)
        if (compute_sha256(raw_text), compute_sha256(body)) != (
            source.document_hash, source.content_hash
        ):
            raise RevisionHistoryError("source changed between canonical parsing and archival")
        record = evidence_from_canonical(metadata).to_dict()
        with self._connect(write=True) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO revisions VALUES (?, ?, ?, ?, ?)",
                (source.document_id, source.document_hash, raw_text, source.content_hash, source.format),
            )
            saved = connection.execute(
                "SELECT raw_text, content_hash, source_format FROM revisions "
                "WHERE document_id = ? AND document_hash = ?",
                (source.document_id, source.document_hash),
            ).fetchone()
            if saved != (raw_text, source.content_hash, source.format):
                raise RevisionHistoryError("revision content collision or archive corruption")
            latest = connection.execute(
                "SELECT document_id, document_hash, memory_id FROM observations "
                "WHERE source_path = ? ORDER BY sequence DESC LIMIT 1", (source.path,),
            ).fetchone()
            identity = (source.document_id, source.document_hash, metadata.identity.id)
            if latest != identity:
                connection.execute(
                    "INSERT INTO observations(document_id, document_hash, memory_id, source_path, observed_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (*identity, source.path, datetime.datetime.now(datetime.timezone.utc).isoformat()),
                )
            self._insert_evidence(connection, record)

    @staticmethod
    def _insert_evidence(connection: sqlite3.Connection, record: Dict[str, Any]) -> None:
        source = record["source"]
        expected = _evidence_fingerprint(
            record["memory_id"], source["document_id"], source["document_hash"], source["content_hash"],
            record["span"]["start_line"], record["span"]["end_line"],
        )
        if record["fingerprint"] != expected or record["evidence_id"] != f"ev_{expected[:16]}":
            raise RevisionHistoryError("invalid evidence fingerprint")
        existing = connection.execute(
            "SELECT record_json FROM evidence WHERE evidence_id = ?", (record["evidence_id"],),
        ).fetchone()
        if existing:
            previous = json.loads(existing[0])
            # Location/extraction method aren't identity: a move or another
            # extraction can issue the same source-version/span evidence ID.
            if previous["fingerprint"] != record["fingerprint"]:
                raise RevisionHistoryError("evidence ID collision")
            return
        connection.execute(
            "INSERT INTO evidence VALUES (?, ?, ?, ?)",
            (record["evidence_id"], json.dumps(record, sort_keys=True, ensure_ascii=False),
             source["document_id"], source["document_hash"]),
        )

    def record_evidence(self, record: Dict[str, Any]) -> None:
        """Persist an issued query-specific evidence ID only for an archived body."""
        source = record["source"]
        revision = self.get_revision(source["document_id"], source["document_hash"])
        if revision is None or revision["content_hash"] != source["content_hash"]:
            raise RevisionHistoryError("cannot issue durable evidence without its exact source revision")
        with self._connect(write=True) as connection:
            self._insert_evidence(connection, record)

    def get_revision(self, document_id: str, document_hash: str) -> Optional[Dict[str, Any]]:
        self._check_paths()
        if not self.path.exists():
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT raw_text, content_hash, source_format FROM revisions "
                "WHERE document_id = ? AND document_hash = ?", (document_id, document_hash),
            ).fetchone()
        if row is None:
            return None
        raw_text, content_hash, source_format = row
        _frontmatter, body = split_source(raw_text, source_format=source_format)
        if compute_sha256(raw_text) != document_hash or compute_sha256(body) != content_hash:
            raise RevisionHistoryError("archived source failed integrity verification")
        return {"document_id": document_id, "document_hash": document_hash,
                "content_hash": content_hash, "format": source_format, "raw_text": raw_text}

    def identity_entries(self) -> Dict[str, Dict[str, str]]:
        """Last observed identities, used only when the disposable manifest lacks them."""
        self._check_paths()
        if not self.path.exists():
            return {}
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT o.source_path, o.memory_id, o.document_id, r.content_hash "
                "FROM observations o JOIN revisions r USING(document_id, document_hash) "
                "WHERE o.sequence = (SELECT MAX(sequence) FROM observations WHERE source_path=o.source_path)"
            ).fetchall()
        return {path: {"id": memory_id, "document_id": document_id, "content_hash": content_hash}
                for path, memory_id, document_id, content_hash in rows}

    def list_revisions(self, document_id: str) -> List[Dict[str, Any]]:
        """Return observed transitions, including moves and A -> B -> A reverts."""
        self._check_paths()
        if not self.path.exists():
            return []
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT sequence, document_id, document_hash, memory_id, source_path, observed_at "
                "FROM observations WHERE document_id = ? ORDER BY sequence", (document_id,),
            )
            keys = [entry[0] for entry in cursor.description]
            return [dict(zip(keys, row)) for row in cursor.fetchall()]

    def resolve_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Resolve an issued ID from durable history, even without any live source/index."""
        self._check_paths()
        if not self.path.exists():
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_json FROM evidence WHERE evidence_id = ?", (evidence_id,),
            ).fetchone()
        if row is None:
            return None
        record = json.loads(row[0])
        source = record["source"]
        revision = self.get_revision(source["document_id"], source["document_hash"])
        if revision is None or revision["content_hash"] != source["content_hash"]:
            raise RevisionHistoryError("evidence references a missing or inconsistent revision")
        start, end = record["span"]["start_line"], record["span"]["end_line"]
        expected = _evidence_fingerprint(
            record["memory_id"], source["document_id"], source["document_hash"], source["content_hash"], start, end
        )
        if record["fingerprint"] != expected or evidence_id != f"ev_{expected[:16]}":
            raise RevisionHistoryError("archived evidence failed fingerprint verification")
        lines = revision["raw_text"].splitlines(keepends=True)
        if start is not None and end is not None and not (1 <= start <= end <= len(lines)):
            raise RevisionHistoryError("archived evidence span is outside its source")
        return {"status": "archived", "evidence": record, "revision": revision,
                "evidence_text": "".join(lines[start - 1:end]) if start and end else None}
