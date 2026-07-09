import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tempfile

from inboxpilot import storage
from inboxpilot.pipeline import run_pipeline

SAMPLE_INBOX = Path(__file__).resolve().parent.parent / "sample_data" / "inbox"


def test_pipeline_processes_all_sample_emails():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        results = run_pipeline(SAMPLE_INBOX, db_path)
        assert len(results) == 10

        conn = storage.get_connection(db_path)
        rows = storage.get_all(conn)
        assert len(rows) == 10

        stats = storage.get_stats(conn)
        assert set(stats.keys()) <= {"urgent_support", "sales_lead", "spam", "newsletter", "general"}
        assert sum(stats.values()) == 10


def test_pipeline_is_idempotent_on_rerun():
    """Running the pipeline twice on the same inbox shouldn't duplicate rows
    (upsert on email_id)."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        run_pipeline(SAMPLE_INBOX, db_path)
        run_pipeline(SAMPLE_INBOX, db_path)

        conn = storage.get_connection(db_path)
        rows = storage.get_all(conn)
        assert len(rows) == 10


def test_critical_email_flagged_correctly():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        results = run_pipeline(SAMPLE_INBOX, db_path)
        outage = next(r for r in results if r["id"] == "e001")
        assert outage["category"] == "urgent_support"
        assert outage["priority"] == 5
