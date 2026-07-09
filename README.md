# ◈ InboxPilot — AI Email Triage & Auto-Response Agent

InboxPilot reads incoming emails, classifies them (urgent support, sales lead, spam, newsletter, general), scores priority, and drafts a suggested reply — all visible on a live console dashboard.

It runs in two tiers, and **works out of the box with zero setup**:

1. **Rule engine** (default) — keyword/pattern heuristics with negation handling (e.g. correctly ignores "not urgent"). No API key, no network call, no cost.
2. **LLM engine** (optional) — set `ANTHROPIC_API_KEY` and InboxPilot automatically upgrades to Claude-powered classification and reply drafting, with automatic fallback to the rule engine if the call fails.

## Why this exists

Support inboxes mix true emergencies with sales pitches, spam, and newsletters — and triaging them by hand doesn't scale. InboxPilot automates the first pass: sort by real priority, flag what needs a human now, and draft a starting-point reply so nothing sits untouched.

## Features

- Hybrid classification engine (rules + optional LLM), same output shape either way
- Priority scoring (1–5) with a control-room style dashboard, sorted by urgency
- Auto-drafted replies per category
- SQLite persistence with idempotent re-runs (no duplicate rows)
- CLI for scripted/batch use
- FastAPI web dashboard with live stats and a "Run Triage" / "Clear Queue" workflow
- 13 automated tests, including a mocked LLM path and a regression test for a real bug (false-positive urgency on negated phrases like "not urgent")
- GitHub Actions CI running the full suite on every push

## Quick start

```bash
git clone https://github.com/ebinraj2007-cmd/inboxpilot.git
cd inboxpilot
pip install -r requirements.txt

# CLI — process the sample inbox
python -m inboxpilot.cli run

# Web dashboard
uvicorn webapp.main:app --reload
# then open http://127.0.0.1:8000
```

Click **Run Triage** on the dashboard to process the sample inbox and watch the queue populate, sorted by priority.

## Enabling the LLM engine (optional)

```bash
export ANTHROPIC_API_KEY=your-key-here
python -m inboxpilot.cli run
```

No key set → automatically uses the rule engine. No code changes needed either way.

## Architecture

```
sample_data/inbox/*.json   →  ingest.py   →  classifier.py   →  storage.py (SQLite)
                                                   │                    │
                                          rules or Claude API      triage_log table
                                                                        │
                                                              CLI  ←────┼────→  FastAPI dashboard
```

- `inboxpilot/classifier.py` — the hybrid engine (rules + optional LLM)
- `inboxpilot/ingest.py` — loads emails from local JSON (also includes a documented IMAP hook for real inboxes)
- `inboxpilot/pipeline.py` — orchestrates ingest → classify → store
- `inboxpilot/storage.py` — SQLite persistence
- `inboxpilot/cli.py` — command-line interface
- `webapp/` — FastAPI backend + vanilla JS/CSS dashboard

## Using your own inbox

Drop JSON files shaped like this into any folder:

```json
{ "id": "e001", "sender": "someone@example.com", "subject": "...", "body": "..." }
```

```bash
python -m inboxpilot.cli run --inbox path/to/your/folder
```

For a real mailbox, `inboxpilot/ingest.py` includes a working `fetch_from_imap()` function — plug in your IMAP credentials and it slots into the same pipeline.

## Running tests

```bash
pytest tests/ -v
```

## Tech stack

Python · FastAPI · SQLite · Anthropic Claude API (optional) · vanilla JS/CSS · pytest · GitHub Actions

## License

MIT
