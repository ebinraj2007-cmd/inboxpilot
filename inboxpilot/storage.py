"""storage.py — SQLite persistence for processed emails."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "inboxpilot.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS triage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT UNIQUE,
    sender TEXT,
    subject TEXT,
    body TEXT,
    category TEXT,
    priority INTEGER,
    confidence REAL,
    reasoning TEXT,
    suggested_reply TEXT,
    engine TEXT,
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def save_result(conn: sqlite3.Connection, email_id: str, sender: str, subject: str,
                 body: str, result) -> None:
    conn.execute(
        """INSERT INTO triage_log
           (email_id, sender, subject, body, category, priority, confidence,
            reasoning, suggested_reply, engine)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(email_id) DO UPDATE SET
             category=excluded.category, priority=excluded.priority,
             confidence=excluded.confidence, reasoning=excluded.reasoning,
             suggested_reply=excluded.suggested_reply, engine=excluded.engine,
             processed_at=CURRENT_TIMESTAMP
        """,
        (email_id, sender, subject, body, result.category, result.priority,
         result.confidence, result.reasoning, result.suggested_reply, result.engine),
    )
    conn.commit()


def get_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM triage_log ORDER BY priority DESC, processed_at DESC"
    ).fetchall()


def get_stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT category, COUNT(*) as n FROM triage_log GROUP BY category"
    ).fetchall()
    return {row["category"]: row["n"] for row in rows}


def clear_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM triage_log")
    conn.commit()
