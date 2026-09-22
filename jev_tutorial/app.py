"""Local support desk: save first, classify second, preserve human corrections."""

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from time import time

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from .classifier import ROOT, TEAM_CRITERIA, classify_ticket

ATTEMPT_LEASE_SECONDS = 120  # Longer than the 30-second API timeout.


def create_app(database=None, classifier=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        MAX_CONTENT_LENGTH=64 * 1024,
        TRUSTED_HOSTS=["localhost", "127.0.0.1"],
        SESSION_COOKIE_SAMESITE="Lax",
    )
    database = Path(database or os.environ.get("JEV_TICKET_DB", ROOT / "instance/tickets.sqlite3"))
    database.parent.mkdir(parents=True, exist_ok=True)
    classify = classifier or classify_ticket

    @contextmanager
    def connect():
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    with connect() as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            error TEXT,
            human_team TEXT,
            human_priority TEXT,
            reviewed_at TEXT,
            attempt_id TEXT,
            attempt_started REAL
        )""")
        # Keep tickets made by an earlier version of this local demo.
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(tickets)")}
        for name, kind in (("attempt_id", "TEXT"), ("attempt_started", "REAL")):
            if name not in columns:
                connection.execute(f"ALTER TABLE tickets ADD COLUMN {name} {kind}")

    def get_ticket(ticket_id):
        with connect() as connection:
            row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            abort(404)
        return unpack(row)

    def unpack(row):
        ticket = dict(row)
        ticket["result"] = json.loads(ticket["result"]) if ticket["result"] else None
        result = ticket["result"]
        ticket["team"] = ticket["human_team"] or (result["policy"]["suggested_team"] if result else None)
        ticket["in_progress"] = (ticket["status"] == "pending" and ticket["attempt_id"] is not None
                                 and ticket["attempt_started"] > time() - ATTEMPT_LEASE_SECONDS)
        return ticket

    def evaluate(ticket_id):
        ticket = get_ticket(ticket_id)
        attempt_id = secrets.token_hex(16)
        now = time()
        with connect() as connection:
            claimed = connection.execute(
                "UPDATE tickets SET status = 'pending', attempt_id = ?, attempt_started = ? "
                "WHERE id = ? AND status IN ('pending', 'failed') "
                "AND (attempt_id IS NULL OR attempt_started <= ?)",
                (attempt_id, now, ticket_id, now - ATTEMPT_LEASE_SECONDS),
            ).rowcount
        if not claimed:
            return False
        try:
            result = classify({"subject": ticket["subject"], "body": ticket["body"]})
            status = "needs_review" if result["policy"]["review_required"] else "classified"
            with connect() as connection:
                connection.execute(
                    "UPDATE tickets SET status = CASE WHEN reviewed_at IS NOT NULL THEN 'reviewed' "
                    "ELSE ? END, result = ?, error = NULL, attempt_id = NULL, attempt_started = NULL "
                    "WHERE id = ? AND attempt_id = ?",
                    (status, json.dumps(result), ticket_id, attempt_id),
                )
        except Exception as error:
            # Store the failure type only. Provider errors can contain request data.
            with connect() as connection:
                connection.execute(
                    "UPDATE tickets SET status = CASE WHEN reviewed_at IS NOT NULL THEN 'reviewed' "
                    "ELSE 'failed' END, error = ?, attempt_id = NULL, attempt_started = NULL "
                    "WHERE id = ? AND attempt_id = ?",
                    (type(error).__name__, ticket_id, attempt_id),
                )
        return True

    @app.before_request
    def protect_forms():
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        if request.method == "POST":
            supplied = request.form.get("csrf_token", "")
            if not secrets.compare_digest(supplied, session["csrf_token"]):
                abort(400, "The form expired. Reload the page and try again.")

    @app.context_processor
    def template_values():
        return {"teams": TEAM_CRITERIA, "csrf_token": session["csrf_token"]}

    @app.get("/")
    def inbox():
        team = request.args.get("team", "")
        review_only = request.args.get("review") == "1"
        with connect() as connection:
            all_tickets = [unpack(row) for row in connection.execute(
                "SELECT * FROM tickets ORDER BY id DESC"
            )]
        tickets = [t for t in all_tickets
                   if (not team or t["team"] == team)
                   and (not review_only or t["status"] in ("needs_review", "failed", "pending"))]
        return render_template("inbox.html", tickets=tickets, total=len(all_tickets),
                               active_team=team, review_only=review_only)

    @app.get("/tickets/new")
    def new_ticket():
        return render_template("new.html", subject="", body="")

    @app.post("/tickets")
    def submit_ticket():
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()
        if not subject or not body or len(subject) > 160 or len(body) > 10000:
            return render_template("new.html", subject=subject, body=body,
                                   error="Add a title (up to 160 characters) and a description (up to 10,000)."), 400
        with connect() as connection:
            ticket_id = connection.execute(
                "INSERT INTO tickets (subject, body) VALUES (?, ?)", (subject, body)
            ).lastrowid
        evaluate(ticket_id)
        return redirect(url_for("ticket_detail", ticket_id=ticket_id), code=303)

    @app.get("/tickets/<int:ticket_id>")
    def ticket_detail(ticket_id):
        return render_template("ticket.html", ticket=get_ticket(ticket_id))

    @app.post("/tickets/<int:ticket_id>/retry")
    def retry_ticket(ticket_id):
        if not evaluate(ticket_id):
            abort(409, "This ticket is already classified, reviewed, or being classified. Refresh its page.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id), code=303)

    @app.post("/tickets/<int:ticket_id>/review")
    def review_ticket(ticket_id):
        get_ticket(ticket_id)
        team = request.form.get("team")
        priority = request.form.get("priority")
        if team not in TEAM_CRITERIA or priority not in ("standard", "blocked"):
            abort(400, "Choose a team and priority.")
        with connect() as connection:
            connection.execute(
                "UPDATE tickets SET human_team = ?, human_priority = ?, status = 'reviewed', "
                "reviewed_at = CURRENT_TIMESTAMP WHERE id = ?", (team, priority, ticket_id)
            )
        flash("Review saved. The original model answer is kept below.")
        return redirect(url_for("ticket_detail", ticket_id=ticket_id), code=303)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5050, debug=False)
