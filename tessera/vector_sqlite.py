"""Opt-in embedded exact-search candidate using only Python's SQLite stdlib.

SQLite owns durability/transactions; bounded fixture search uses the shared
exact scoring kernel. This is not an ANN index or a production-scale winner.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .vector_backend import (
    ExactFlatBackend, SemanticIndexSpec, VectorBackendCapabilities,
    VectorIndexError, VectorIndexIncompatible, VectorIndexStats,
    VectorIndexVerification, VectorRecord, _json, corpus_hash,
    search_snapshot, validate_records,
)


def _no_symlinks(path):
    for item in (path, *path.parents):
        if item.is_symlink():
            raise VectorIndexError("semantic index path must not contain symlinks")


class SQLiteVectorBackend(ExactFlatBackend):
    """Persist only under an explicitly supplied, owned derived index directory.

    Threads share an instance lock. Separate instances/processes use SQLite
    snapshot reads and serialized writers with a bounded five-second timeout.
    The caller owns source serialization: replace_source is last-commit-wins.
    """

    def __init__(self, index_root):
        super().__init__()
        # absolute(), unlike resolve(), does not hide an existing symlink.
        self._root = Path(index_root).absolute()
        self._connection = None
        self.path = None

    def capabilities(self):
        return VectorBackendCapabilities("sqlite-exact", "1", persistence=True)

    def open(self, index_spec):
        if not isinstance(index_spec, SemanticIndexSpec):
            raise VectorIndexError("index_spec must be SemanticIndexSpec")
        with self._lock:
            if self._connection is not None:
                if self._spec != index_spec:
                    raise VectorIndexIncompatible("index spec mismatch; close and rebuild in a fresh namespace")
                return
            path = (self._root / "semantic" / index_spec.embedding_profile_fingerprint[7:] /
                    self.capabilities().backend / "vectors.sqlite3")
            for artifact in (path, Path(str(path) + "-journal"), Path(str(path) + "-wal"), Path(str(path) + "-shm")):
                _no_symlinks(artifact)
            path.parent.mkdir(parents=True, exist_ok=True)
            _no_symlinks(path)
            connection = sqlite3.connect(str(path), timeout=5.0, isolation_level=None,
                                         check_same_thread=False)
            try:
                # DELETE journal + FULL synchronous gives atomic, recoverable commits
                # without a background service. SQLite handles hot-journal recovery.
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                tables = {row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                if not tables:
                    connection.execute("CREATE TABLE vector_manifest (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)")
                    connection.execute("CREATE TABLE vectors (record_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                    manifest = {"spec": asdict(index_spec), "backend": "sqlite-exact",
                                "backend_version": "1", "sqlite_version": sqlite3.sqlite_version,
                                "built_at": datetime.now(timezone.utc).isoformat(),
                                "corpus_manifest_hash": corpus_hash(())}
                    connection.execute("INSERT INTO vector_manifest VALUES (1, ?)", (_json(manifest),))
                elif tables != {"vectors", "vector_manifest"}:
                    raise VectorIndexIncompatible("unrecognized semantic database schema; rebuild in a fresh namespace")
                manifest = self._read_manifest(connection, index_spec)
                records = self._read_records(connection, index_spec)
                if manifest["corpus_manifest_hash"] != corpus_hash(records):
                    raise VectorIndexIncompatible("semantic corpus checksum mismatch; rebuild from canonical inputs")
                connection.commit()
            except BaseException as exc:
                connection.rollback()
                connection.close()
                if isinstance(exc, (sqlite3.DatabaseError, KeyError, TypeError, json.JSONDecodeError)):
                    raise VectorIndexIncompatible("unreadable semantic index; rebuild from canonical inputs") from exc
                raise
            self._connection, self._spec, self.path = connection, index_spec, path

    @staticmethod
    def _read_manifest(connection, spec):
        row = connection.execute("SELECT payload FROM vector_manifest WHERE id=1").fetchone()
        if row is None:
            raise VectorIndexIncompatible("missing semantic manifest; rebuild from canonical inputs")
        manifest = json.loads(row[0])
        if not isinstance(manifest, dict):
            raise VectorIndexIncompatible("invalid semantic manifest; rebuild from canonical inputs")
        if (manifest.get("spec") != json.loads(_json(asdict(spec))) or
                manifest.get("backend") != "sqlite-exact" or manifest.get("backend_version") != "1"):
            raise VectorIndexIncompatible("semantic profile/dimension/backend/configuration mismatch; rebuild or use another namespace")
        return manifest

    @staticmethod
    def _read_records(connection, spec):
        records = []
        for key, payload in connection.execute("SELECT record_id, payload FROM vectors ORDER BY record_id"):
            data = json.loads(payload)
            data["vector"] = tuple(data["vector"])
            data["evidence_ids"] = tuple(data["evidence_ids"])
            record = VectorRecord(**data)
            if record.record_id != key:
                raise VectorIndexIncompatible("semantic vector identity mismatch; rebuild from canonical inputs")
            records.append(record)
        return validate_records(records, spec)

    def _require_connection(self):
        self._require_open()
        if self._connection is None:
            raise VectorIndexError("backend is closed; call open(index_spec)")
        for artifact in (self.path, Path(str(self.path) + "-journal"), Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm")):
            _no_symlinks(artifact)
        return self._connection

    def _snapshot(self):
        connection = self._require_connection()
        manifest = self._read_manifest(connection, self._spec)
        records = self._read_records(connection, self._spec)
        if manifest["corpus_manifest_hash"] != corpus_hash(records):
            raise VectorIndexIncompatible("semantic corpus checksum mismatch; rebuild from canonical inputs")
        return manifest, records

    def _mutate(self, records=(), record_ids=(), source_id=None, rebuild=False):
        # Materialize and validate before obtaining the write lock. A broken
        # encoder/generator therefore cannot leave a half-built source.
        with self._lock:
            batch = validate_records(records, self._require_open())
            ids = tuple(record_ids)
            connection = self._require_connection()
            connection.execute("BEGIN IMMEDIATE")
            try:
                manifest, current = self._snapshot()
                oracle = ExactFlatBackend()
                oracle.open(self._spec)
                oracle.upsert(current)
                result = oracle._mutate(batch, ids, source_id, rebuild)
                old = {r.record_id: r for r in current}
                new = oracle._records
                connection.executemany("DELETE FROM vectors WHERE record_id=?",
                                       ((key,) for key in set(old) - set(new)))
                connection.executemany("INSERT OR REPLACE INTO vectors VALUES (?, ?)",
                                       ((key, _json(asdict(record))) for key, record in new.items()
                                        if old.get(key) != record))
                manifest["corpus_manifest_hash"] = corpus_hash(new.values())
                if result.upserted or result.removed:
                    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
                connection.execute("UPDATE vector_manifest SET payload=? WHERE id=1", (_json(manifest),))
                connection.commit()
                return result
            except BaseException:
                connection.rollback()
                raise

    def search(self, request):
        with self._lock:
            request.validate(self._require_open())
            connection = self._require_connection()
            connection.execute("BEGIN")
            try:
                _, records = self._snapshot()
                spec = self._spec
            finally:
                connection.rollback()
        return search_snapshot(records, request, spec, self.capabilities().backend)

    def stats(self):
        with self._lock:
            connection = self._require_connection()
            connection.execute("BEGIN")
            try:
                manifest, records = self._snapshot()
                size = sum(p.stat().st_size for p in (self.path, Path(str(self.path) + "-journal")) if p.exists())
                return VectorIndexStats(len(records), manifest["corpus_manifest_hash"], size)
            finally:
                connection.rollback()

    def verify(self):
        with self._lock:
            connection = self._require_connection()
            connection.execute("BEGIN")
            try:
                integrity = tuple(row[0] for row in connection.execute("PRAGMA integrity_check"))
                if integrity != ("ok",):
                    return VectorIndexVerification(False, integrity)
                self._snapshot()
                return VectorIndexVerification(True)
            except (ValueError, KeyError, TypeError, sqlite3.DatabaseError) as exc:
                return VectorIndexVerification(False, (f"{type(exc).__name__}: rebuild derived index from canonical inputs",))
            finally:
                connection.rollback()

    def close(self):
        with self._lock:
            if self._connection is not None:
                self._connection.close()
            self._connection, self._spec = None, None
