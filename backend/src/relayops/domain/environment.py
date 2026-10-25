"""Original sandbox business world; fixtures do not connect to real vendors."""

import json
import sqlite3
from pathlib import Path

from relayops.domain.models import Refused
from relayops.domain.models import digest

SYSTEMS = ("procurement", "warehouse", "billing", "case_management")


def fixture(
    name="short-shipment",
    *,
    ordered=100,
    received=80,
    unit_cents=2500,
    stock=50,
    delivery_known=True,
    billed=None,
    tenant="northstar",
):
    billed = ordered if billed is None else billed
    return {
        "tenant": tenant,
        "case_id": name,
        "procurement": {
            "order_id": "PO-2041",
            "ordered_units": ordered,
            "unit_cents": unit_cents,
        },
        "warehouse": {
            "received_units": received,
            "delivery_known": delivery_known,
            "available_units": stock,
        },
        "billing": {"invoiced_units": billed, "held_cents": 0},
        "case_management": {"status": "open", "claim_units": 0, "reserved_units": 0},
        "documents": {
            "invoice": {
                "title": "Supplier invoice INV-2041",
                "order_id": "PO-2041",
                "units": billed,
                "unit_cents": unit_cents,
                "note": "Invoice quantity must be reconciled with confirmed delivery.",
            },
            "delivery_note": {
                "title": "Delivery note DN-2041",
                "order_id": "PO-2041",
                "units": received,
                "confirmed": delivery_known,
                "note": "Inspect delivery confirmation before acting.",
            },
        },
    }


class World:
    """SQLite is only this local fixture/receipt backend, not a distributed queue."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, tenant TEXT NOT NULL, version TEXT NOT NULL, system TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, digest TEXT NOT NULL, tenant TEXT NOT NULL, status TEXT NOT NULL, operator TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, plan_digest TEXT NOT NULL, action_index INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT);
                CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def initialize(self, source):
        with self.connect() as db:
            db.execute("INSERT INTO state VALUES (1,?)", (json.dumps(source),))

    def state(self, db=None):
        if db is not None:
            return json.loads(
                db.execute("SELECT payload FROM state WHERE id=1").fetchone()[0]
            )
        with self.connect() as connection:
            return self.state(connection)

    def source(self, db=None):
        state = self.state(db)
        return {
            "tenant": state["tenant"],
            "case_id": state["case_id"],
            "procurement": state["procurement"],
            "warehouse": {
                k: state["warehouse"][k]
                for k in ("received_units", "delivery_known", "available_units")
            },
            "billing": {"invoiced_units": state["billing"]["invoiced_units"]},
            "documents": state.get("documents", {}),
        }

    def version(self, db=None):
        return digest(self.source(db))

    def observe(self, tenant, system):
        if system not in SYSTEMS:
            raise Refused("Unknown observation system")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self.state(db)
            if state["tenant"] != tenant:
                raise Refused("Tenant scope mismatch")
            version = self.version(db)
            record = {
                "tenant": tenant,
                "case_id": state["case_id"],
                "source_version": version,
                "system": system,
                "data": state[system],
            }
            identity = digest(record)
            db.execute(
                "INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?)",
                (identity, tenant, version, system, json.dumps(record)),
            )
            return {"evidence_id": identity, **record}

    def public_observations(self):
        return [self.observe(self.state()["tenant"], system) for system in SYSTEMS]

    def observe_document(self, tenant, document):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self.state(db)
            if tenant != state["tenant"] or document not in state.get("documents", {}):
                raise Refused("Document outside the authorized case")
            version = self.version(db)
            record = {
                "tenant": tenant,
                "case_id": state["case_id"],
                "source_version": version,
                "system": "document:" + document,
                "data": state["documents"][document],
            }
            identity = digest(record)
            db.execute(
                "INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?)",
                (identity, tenant, version, record["system"], json.dumps(record)),
            )
            return {"evidence_id": identity, **record}

    def events(self):
        with self.connect() as db:
            return [
                {"kind": row["kind"], "payload": json.loads(row["payload"])}
                for row in db.execute("SELECT * FROM events ORDER BY id")
            ]

    def change_source(self, **values):
        """Evaluator fixture operation: simulate new delivery information."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self.state(db)
            state["warehouse"].update(values)
            db.execute("UPDATE state SET payload=? WHERE id=1", (json.dumps(state),))

    def reset_effects(self):
        """Not exposed as an agent tool; evaluation uses fresh worlds instead."""
        raise Refused("Sandbox effects cannot be silently reset")
