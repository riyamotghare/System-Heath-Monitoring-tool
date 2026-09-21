"""database.py - SQLite storage for support tickets.

Every query uses ? placeholders (parameterized queries) so user input is
always treated as data, never as SQL code. This prevents SQL injection.
"""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

# Stored next to this file so the path is the same however the app is launched.
DB_PATH = Path(__file__).resolve().parent / "tickets.db"

CATEGORIES = ["Hardware", "Software", "Network", "Account/Access", "Performance", "Other"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["Open", "In Progress", "Resolved"]


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the tickets table if it does not exist yet."""
    with closing(get_connection()) as conn:
        with conn:  # commits on success, rolls back on error
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    description TEXT,
                    troubleshooting TEXT,
                    status TEXT NOT NULL DEFAULT 'Open',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )


def _now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def create_ticket(title, category, priority, description, troubleshooting):
    """Insert a new ticket and return its id. Raises ValueError on bad input."""
    title = (title or "").strip()
    if not title:
        raise ValueError("Title is required.")
    if category not in CATEGORIES:
        raise ValueError("Invalid category.")
    if priority not in PRIORITIES:
        raise ValueError("Invalid priority.")

    now = _now()
    with closing(get_connection()) as conn:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO tickets
                    (title, category, priority, description, troubleshooting,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'Open', ?, ?)
                """,
                (title, category, priority, (description or "").strip(),
                 (troubleshooting or "").strip(), now, now),
            )
            return cursor.lastrowid


def get_tickets(status=None):
    """Return tickets as a Pandas DataFrame, newest first. Optional status filter."""
    query = "SELECT * FROM tickets"
    params = ()
    if status and status != "All":
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY id DESC"
    with closing(get_connection()) as conn:
        return pd.read_sql_query(query, conn, params=params)


def update_ticket_status(ticket_id, new_status):
    """Change a ticket's status. Returns True if a row was updated."""
    if new_status not in STATUSES:
        raise ValueError("Invalid status.")
    with closing(get_connection()) as conn:
        with conn:
            cursor = conn.execute(
                "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, _now(), int(ticket_id)),
            )
            return cursor.rowcount > 0
