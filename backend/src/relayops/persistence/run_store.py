"""Durable investigation admission and fenced ownership; no automatic live replay."""

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from relayops.domain.models import Refused
from relayops.domain.models import digest

SCHEMA_VERSION = 1
COLUMNS = {
    "spec_json": "TEXT",
    "owner": "TEXT",
    "lease_until": "DOUBLE PRECISION",
    "error_kind": "TEXT",
}
SCHEMA = """
CREATE TABLE IF NOT EXISTS relay_schema_migrations (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, case_id TEXT, mode TEXT, status TEXT, review TEXT,
 approval TEXT, created_at TEXT, request_key TEXT UNIQUE, request_hash TEXT,
 execution TEXT, spec_json TEXT, owner TEXT, lease_until DOUBLE PRECISION, error_kind TEXT
);
CREATE INDEX IF NOT EXISTS relay_runs_status_created ON runs(status,created_at,id);
"""


class Row(dict):
    def __getitem__(self, key):
        return (
            tuple(self.values())[key]
            if isinstance(key, int)
            else super().__getitem__(key)
        )


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        value = self.cursor.fetchone()
        return Row(value) if value is not None else None

    def fetchall(self):
        return [Row(value) for value in self.cursor.fetchall()]

    def __iter__(self):
        for value in self.cursor:
            yield Row(value)


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        # Only owned statements reach this boundary; no SQL originates from an LLM.
        if query == "BEGIN IMMEDIATE":
            query = "SELECT pg_advisory_xact_lock(719263104)"
        return Cursor(self.connection.execute(query.replace("?", "%s"), params))


def migrate_postgres(database_url):
    import psycopg

    with psycopg.connect(database_url) as connection:
        connection.execute(SCHEMA)
        connection.execute(
            "INSERT INTO relay_schema_migrations(version) VALUES (%s) ON CONFLICT DO NOTHING",
            (SCHEMA_VERSION,),
        )


class RunStore:
    def __init__(self, root, database_url=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database_url = (
            database_url
            if database_url is not None
            else os.getenv("RELAY_DATABASE_URL")
        )
        self.pool = None
        if self.database_url:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            self.pool = ConnectionPool(
                self.database_url,
                min_size=1,
                max_size=5,
                open=True,
                kwargs={"row_factory": dict_row},
            )
            try:
                self.pool.wait(timeout=10)
                with self.connection() as connection:
                    row = connection.execute(
                        "SELECT MAX(version) FROM relay_schema_migrations"
                    ).fetchone()
                    if row[0] != SCHEMA_VERSION:
                        raise Refused(
                            "Run the RelayOps database migration before startup"
                        )
            except BaseException:
                self.pool.close()
                raise
        else:
            with sqlite3.connect(self.root / "runs.sqlite") as connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, case_id TEXT, mode TEXT, status TEXT, review TEXT, approval TEXT, created_at TEXT, request_key TEXT UNIQUE, request_hash TEXT, execution TEXT)"
                )
                existing = {
                    row[1] for row in connection.execute("PRAGMA table_info(runs)")
                }
                for name, kind in COLUMNS.items():
                    if name not in existing:
                        connection.execute(
                            "ALTER TABLE runs ADD COLUMN " + name + " " + kind
                        )
                connection.executescript(SCHEMA)
                connection.execute(
                    "INSERT OR IGNORE INTO relay_schema_migrations VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                # The old schema did not retain browser configuration or ownership.
                # Preserve completed records; never replay ambiguous legacy active work.
                for identity, case_id, mode in connection.execute(
                    "SELECT id,case_id,mode FROM runs WHERE spec_json IS NULL"
                ).fetchall():
                    connection.execute(
                        "UPDATE runs SET spec_json=? WHERE id=?",
                        (
                            json.dumps(
                                {"case_id": case_id, "mode": mode, "browser": True}
                            ),
                            identity,
                        ),
                    )
                    connection.execute(
                        "UPDATE runs SET status='interrupted',error_kind='LegacyOwnershipUnknown' "
                        "WHERE id=? AND status IN ('queued','running')",
                        (identity,),
                    )

    @contextmanager
    def connection(self):
        if self.pool:
            with self.pool.connection() as connection:
                with connection.transaction():
                    yield PostgresConnection(connection)
        else:
            connection = sqlite3.connect(self.root / "runs.sqlite", timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            try:
                with connection:
                    yield connection
            finally:
                connection.close()

    def close(self):
        if self.pool:
            self.pool.close()

    def enqueue(self, spec, key):
        from datetime import datetime
        from datetime import timezone

        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            old = connection.execute(
                "SELECT * FROM runs WHERE request_key=?", (key,)
            ).fetchone()
            if old:
                if old["request_hash"] != digest(spec):
                    raise Refused("Idempotency key was used for another request")
                return old["id"], old["status"], False
            count = connection.execute(
                "SELECT COUNT(*) FROM runs WHERE status IN ('queued','running')"
            ).fetchone()[0]
            if count >= 16:
                raise Refused("Investigation queue capacity reached")
            identity = uuid.uuid4().hex
            connection.execute(
                "INSERT INTO runs(id,case_id,mode,status,created_at,request_key,request_hash,spec_json) VALUES (?,?,?,?,?,?,?,?)",
                (
                    identity,
                    spec["case_id"],
                    spec["mode"],
                    "queued",
                    datetime.now(timezone.utc).isoformat(),
                    key,
                    digest(spec),
                    json.dumps(spec),
                ),
            )
        return identity, "queued", True

    def claim(self, identity=None, lease_seconds=60):
        with self.connection() as connection:
            if not self.pool:
                connection.execute("BEGIN IMMEDIATE")
            now = time.time()
            connection.execute(
                "UPDATE runs SET status='interrupted',owner=NULL,lease_until=NULL,error_kind='LeaseExpired' "
                "WHERE status='running' AND lease_until<?",
                (now,),
            )
            clause, params = (" AND id=?", (identity,)) if identity else ("", ())
            lock = " FOR UPDATE SKIP LOCKED" if self.pool else ""
            row = connection.execute(
                "SELECT * FROM runs WHERE status='queued'"
                + clause
                + " ORDER BY created_at,id LIMIT 1"
                + lock,
                params,
            ).fetchone()
            if not row:
                return None
            owner = uuid.uuid4().hex
            connection.execute(
                "UPDATE runs SET status='running',owner=?,lease_until=? WHERE id=?",
                (owner, now + lease_seconds, row["id"]),
            )
            return {
                "id": row["id"],
                "owner": owner,
                "spec": json.loads(row["spec_json"]),
            }

    def heartbeat(self, job, lease_seconds=60):
        with self.connection() as connection:
            now = time.time()
            updated = connection.execute(
                "UPDATE runs SET lease_until=? WHERE id=? AND status='running' AND owner=? AND lease_until>=?",
                (now + lease_seconds, job["id"], job["owner"], now),
            )
            if updated.rowcount != 1:
                raise Refused("Worker ownership expired; publication is blocked")

    def finish(self, job, status, publish=None, error_kind=None):
        if status not in ("completed", "failed", "interrupted"):
            raise ValueError("Invalid terminal state")
        with self.connection() as connection:
            if not self.pool:
                connection.execute("BEGIN IMMEDIATE")
            lock = " FOR UPDATE" if self.pool else ""
            row = connection.execute(
                "SELECT * FROM runs WHERE id=?" + lock, (job["id"],)
            ).fetchone()
            if (
                not row
                or row["status"] != "running"
                or row["owner"] != job["owner"]
                or row["lease_until"] < time.time()
            ):
                raise Refused("Worker ownership expired; publication is blocked")
            if publish:
                publish()
            connection.execute(
                "UPDATE runs SET status=?,owner=NULL,lease_until=NULL,error_kind=? WHERE id=?",
                (status, error_kind, job["id"]),
            )
