"""Queue ownership, API restart and fresh-process execution contracts."""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import httpx

from relayops.domain.models import Refused
from relayops.persistence.run_store import RunStore
from relayops.persistence.run_store import migrate_postgres
from relayops.api.web import create_app
from relayops.workers.worker import run_one

SPEC = {"case_id": "short-shipment", "mode": "scripted", "browser": False}
TEST_DATABASE_URL = os.getenv("RELAY_TEST_DATABASE_URL")


class QueueContract:
    database_url = ""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        if self.database_url:
            migrate_postgres(self.database_url)
        self.store = RunStore(self.root, self.database_url)
        self.addCleanup(self.store.close)
        if self.database_url:
            with self.store.connection() as connection:
                connection.execute("DELETE FROM runs")

    def test_concurrent_stores_have_one_admission_and_one_owner_per_job(self):
        stores = [RunStore(self.root, self.database_url) for _ in range(4)]
        for store in stores:
            self.addCleanup(store.close)
        with ThreadPoolExecutor(max_workers=4) as pool:
            admitted = list(pool.map(lambda store: store.enqueue(SPEC, "same-request"), stores))
        self.assertEqual(len({value[0] for value in admitted}), 1)
        self.assertEqual(sum(value[2] for value in admitted), 1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            claimed = list(pool.map(lambda store: store.claim(), stores))
        self.assertEqual(sum(value is not None for value in claimed), 1)
        with self.assertRaises(Refused):
            self.store.enqueue({**SPEC, "browser": True}, "same-request")

    def test_expiry_blocks_heartbeat_and_publication_without_requeue(self):
        identity, _, _ = self.store.enqueue(SPEC, "expired-request")
        job = self.store.claim(lease_seconds=-1)
        published = []
        with self.assertRaises(Refused):
            self.store.finish(job, "completed", publish=lambda: published.append(True))
        with self.assertRaises(Refused):
            self.store.heartbeat(job)
        self.assertIsNone(self.store.claim())
        self.assertEqual(published, [])
        with self.store.connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (identity,)).fetchone()
        self.assertEqual(row["status"], "interrupted")
        self.assertEqual(row["error_kind"], "LeaseExpired")

    def test_queued_payload_survives_reopening_and_worker_completes_verified_report(self):
        identity, _, _ = self.store.enqueue(SPEC, "durable-request")
        reopened = RunStore(self.root, self.database_url)
        self.addCleanup(reopened.close)
        self.assertTrue(asyncio.run(run_one(reopened)))
        with self.store.connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (identity,)).fetchone()
        self.assertEqual(row["status"], "completed")
        self.assertIsNone(row["owner"])
        report = json.loads((self.root / "runs" / identity / "assessment.json").read_text())
        self.assertTrue(report["simulation"]["passed"])
        self.assertEqual(report["tool_calls"], 6)
        self.assertIsNone(self.store.claim())


class SQLiteQueueTests(QueueContract, unittest.TestCase):
    def test_legacy_migration_preserves_completed_history_and_blocks_ambiguous_replay(self):
        import sqlite3
        legacy = self.root / "legacy"
        legacy.mkdir()
        with sqlite3.connect(legacy / "runs.sqlite") as connection:
            connection.execute("CREATE TABLE runs (id TEXT PRIMARY KEY, case_id TEXT, mode TEXT, status TEXT, review TEXT, approval TEXT, created_at TEXT, request_key TEXT UNIQUE, request_hash TEXT, execution TEXT)")
            for identity, status in (("completed-old", "completed"), ("queued-old", "queued")):
                connection.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)", (identity, "short-shipment", "scripted", status, "approved" if status=="completed" else None, None, "2026-10-12", identity, "old-hash", None))
        migrated = RunStore(legacy, "")
        self.addCleanup(migrated.close)
        with migrated.connection() as connection:
            old = connection.execute("SELECT * FROM runs WHERE id='completed-old'").fetchone()
            ambiguous = connection.execute("SELECT * FROM runs WHERE id='queued-old'").fetchone()
        self.assertEqual((old["status"], old["review"], old["request_hash"]), ("completed", "approved", "old-hash"))
        self.assertEqual(ambiguous["status"], "interrupted")
        self.assertIsNone(migrated.claim())

    def test_separate_python_worker_executes_persisted_request(self):
        identity, _, _ = self.store.enqueue(SPEC, "process-request")
        environment = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[3] / "backend" / "src"),
                           RELAY_DATABASE_URL="", RELAY_ALLOW_LIVE="0")
        environment.pop("ANTHROPIC_API_KEY", None)
        completed = subprocess.run([sys.executable, "-m", "relayops.workers.worker", "--once", "--state-dir", str(self.root)],
                                   env=environment, capture_output=True, text=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        with self.store.connection() as connection:
            self.assertEqual(connection.execute("SELECT status FROM runs WHERE id=?", (identity,)).fetchone()[0], "completed")


@unittest.skipUnless(TEST_DATABASE_URL, "Set RELAY_TEST_DATABASE_URL for real PostgreSQL integration")
class PostgresQueueTests(QueueContract, unittest.TestCase):
    database_url = TEST_DATABASE_URL


class RestartAndAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_restart_preserves_queue_and_owned_worker(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"RELAY_EMBEDDED_WORKER": "0", "RELAY_DATABASE_URL": ""}):
            root = Path(directory)
            app = create_app(root)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)), base_url="http://localhost") as client:
                    response = await client.post("/api/runs", json=SPEC, headers={"Idempotency-Key": "restart-request"})
                    identity = response.json()["id"]
            worker = RunStore(root, "")
            self.addCleanup(worker.close)
            job = worker.claim()
            restarted = create_app(root)
            async with restarted.router.lifespan_context(restarted):
                with worker.connection() as connection:
                    self.assertEqual(connection.execute("SELECT status FROM runs WHERE id=?", (identity,)).fetchone()[0], "running")
                worker.heartbeat(job)
            # Explicit worker interruption retains terminal state; API shutdown did not change ownership.
            worker.finish(job, "interrupted", error_kind="WorkerShutdown")

    async def test_hosted_operator_gate_accepts_bearer_and_browser_basic_auth(self):
        import base64
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"RELAY_ACCESS_TOKEN": "a" * 32, "RELAY_PUBLIC_ORIGIN": "https://relay.example", "RELAY_DATABASE_URL": ""}):
            app = create_app(directory)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("203.0.113.10", 1)), base_url="https://relay.example") as client:
                    self.assertEqual((await client.get("/healthz")).status_code, 200)
                    self.assertEqual((await client.get("/readyz")).json(), {"status": "ready"})
                    denied = await client.get("/")
                    self.assertEqual(denied.status_code, 401)
                    self.assertIn("Basic", denied.headers["WWW-Authenticate"])
                    self.assertEqual((await client.get("/", headers={"Authorization": "Bearer " + "a" * 32})).status_code, 200)
                    basic = base64.b64encode(("operator:" + "a" * 32).encode()).decode()
                    self.assertEqual((await client.get("/", headers={"Authorization": "Basic " + basic})).status_code, 200)
                    self.assertEqual((await client.get("/", headers={"Authorization": "Basic invalid!"})).status_code, 401)
