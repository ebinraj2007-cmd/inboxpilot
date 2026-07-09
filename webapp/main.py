"""webapp/main.py — FastAPI dashboard for InboxPilot.

Run with:  uvicorn webapp.main:app --reload --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from inboxpilot import storage
from inboxpilot.pipeline import run_pipeline

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
SAMPLE_INBOX = ROOT_DIR / "sample_data" / "inbox"
INDEX_HTML = (BASE_DIR / "templates" / "index.html").read_text()

app = FastAPI(title="InboxPilot", description="AI Email Triage & Auto-Response Agent")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return INDEX_HTML


@app.get("/api/emails")
def api_emails():
    conn = storage.get_connection()
    rows = storage.get_all(conn)
    conn.close()
    return JSONResponse([dict(row) for row in rows])


@app.get("/api/stats")
def api_stats():
    conn = storage.get_connection()
    stats = storage.get_stats(conn)
    total = sum(stats.values())
    conn.close()
    return JSONResponse({"total": total, "by_category": stats})


@app.post("/api/process")
def api_process():
    results = run_pipeline(SAMPLE_INBOX)
    return JSONResponse({"processed": len(results)})


@app.post("/api/clear")
def api_clear():
    conn = storage.get_connection()
    storage.clear_all(conn)
    conn.close()
    return JSONResponse({"cleared": True})
