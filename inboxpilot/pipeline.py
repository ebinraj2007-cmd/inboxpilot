"""pipeline.py — Orchestrates ingest -> classify -> store."""

from __future__ import annotations

from pathlib import Path

from . import ingest, storage
from .classifier import classify_email


def run_pipeline(inbox_folder: str | Path, db_path: Path | None = None) -> list[dict]:
    emails = ingest.load_from_json_folder(inbox_folder)
    conn = storage.get_connection(db_path)

    results = []
    for email in emails:
        result = classify_email(email.subject, email.body, email.sender)
        storage.save_result(conn, email.id, email.sender, email.subject, email.body, result)
        results.append({
            "id": email.id,
            "sender": email.sender,
            "subject": email.subject,
            **result.to_dict(),
        })

    conn.close()
    return results
