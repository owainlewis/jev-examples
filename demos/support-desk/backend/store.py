"""Small SQLite store, including atomic claims for live provider requests."""

import json
import sqlite3
from contextlib import contextmanager
from time import time
from uuid import uuid4

LEASE_SECONDS = 90
PRESETS = [
    {
        "subject": "Charged twice for our subscription",
        "body": "Hi, our subscription payment went through twice this morning. Please refund the duplicate charge. We can still use the product and complete our work normally.",
        "customer": "Amelia Chen",
        "preset": "Refund",
    },
    {
        "subject": "Our whole team is locked out of projects",
        "body": "Every project returns a 500 error for all 18 people on our team. Nobody can finish their work. We have tried another browser and there is no workaround. Please investigate the outage.",
        "customer": "Marcus Reed",
        "preset": "Outage",
    },
    {
        "subject": "Something is wrong with my workspace",
        "body": "Something seems off with my workspace today. Could somebody take a look?",
        "customer": "Sofia Patel",
        "preset": "Ambiguous",
    },
    {
        "subject": "Please update my account email",
        "body": "I need to change the email address on my account. I can still sign in and complete all my work normally. Can you help me update my profile?",
        "customer": "Leo Martin",
        "preset": "Account",
    },
]


class Conflict(Exception):
    pass


class MissingTicket(Exception):
    pass


class Store:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY, subject TEXT NOT NULL, body TEXT NOT NULL,
                    customer TEXT NOT NULL, preset TEXT, created_at REAL NOT NULL,
                    routing TEXT, correction TEXT
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, ticket_id TEXT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
                    mode TEXT NOT NULL, status TEXT NOT NULL, started_at REAL NOT NULL,
                    result TEXT, error TEXT
                );
                CREATE INDEX IF NOT EXISTS runs_ticket ON runs(ticket_id, started_at);
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY);
            """)
            if not db.execute("SELECT 1 FROM meta WHERE key='seeded'").fetchone():
                self._seed(db)
                db.execute("INSERT INTO meta VALUES ('seeded')")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _insert(self, db, data):
        identifier = str(uuid4())
        db.execute(
            "INSERT INTO tickets (id,subject,body,customer,preset,created_at) VALUES (?,?,?,?,?,?)",
            (
                identifier,
                data["subject"],
                data["body"],
                data["customer"],
                data.get("preset"),
                time(),
            ),
        )
        return identifier

    def _seed(self, db):
        for data in reversed(PRESETS):
            self._insert(db, data)

    def _expire(self, db):
        db.execute(
            "UPDATE runs SET status='failed', error='The request expired. Run classification again.' WHERE status='running' AND started_at < ?",
            (time() - LEASE_SECONDS,),
        )

    def _snapshot(self, db, identifier):
        row = db.execute("SELECT * FROM tickets WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise MissingTicket("Ticket not found. Refresh the inbox.")
        ticket = dict(row)
        for key in ("routing", "correction"):
            ticket[key] = json.loads(ticket[key]) if ticket[key] else None
        ticket["runs"] = []
        for row in db.execute(
            "SELECT * FROM runs WHERE ticket_id=? ORDER BY started_at DESC",
            (identifier,),
        ):
            run = dict(row)
            run["result"] = json.loads(run["result"]) if run["result"] else None
            ticket["runs"].append(run)
        return ticket

    def _list(self, db):
        return [
            self._snapshot(db, row["id"])
            for row in db.execute("SELECT id FROM tickets ORDER BY created_at DESC")
        ]

    def list(self):
        with self.connection() as db:
            self._expire(db)
            return self._list(db)

    def get(self, identifier):
        with self.connection() as db:
            self._expire(db)
            return self._snapshot(db, identifier)

    def create(self, data):
        with self.connection() as db:
            identifier = self._insert(db, data)
            return self._snapshot(db, identifier)

    def claim(self, ticket_id, mode):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._expire(db)
            self._snapshot(db, ticket_id)
            if db.execute(
                "SELECT 1 FROM runs WHERE ticket_id=? AND status='running'",
                (ticket_id,),
            ).fetchone():
                raise Conflict(
                    "This ticket is already being classified. Wait for it to finish."
                )
            identifier = str(uuid4())
            db.execute(
                "INSERT INTO runs (id,ticket_id,mode,status,started_at) VALUES (?,?,?,'running',?)",
                (identifier, ticket_id, mode, time()),
            )
            return identifier

    def finish(self, identifier, result=None, error=None):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._expire(db)
            run = db.execute(
                "SELECT * FROM runs WHERE id=? AND status='running'", (identifier,)
            ).fetchone()
            if run is None:
                return False
            db.execute(
                "UPDATE runs SET status=?,result=?,error=? WHERE id=?",
                (
                    "failed" if error else "succeeded",
                    json.dumps(result) if result else None,
                    error,
                    identifier,
                ),
            )
            if result and run["mode"] == "combined":
                db.execute(
                    "UPDATE tickets SET routing=? WHERE id=?",
                    (json.dumps(result["policy"]), run["ticket_id"]),
                )
            return self._snapshot(db, run["ticket_id"])

    def correct(self, identifier, data):
        with self.connection() as db:
            db.execute(
                "UPDATE tickets SET correction=? WHERE id=?",
                (json.dumps(data), identifier),
            )
            return self._snapshot(db, identifier)

    def reset(self):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._expire(db)
            if db.execute("SELECT 1 FROM runs WHERE status='running'").fetchone():
                raise Conflict(
                    "Wait for classification to finish before resetting the demo."
                )
            db.execute("DELETE FROM tickets")
            self._seed(db)
            return self._list(db)
