"""ingest.py — Loads emails to be triaged.

Default source: local JSON files in sample_data/inbox/ (or any folder you point at),
so the whole pipeline runs with zero external accounts or credentials.

For real-world use, wire up `fetch_from_imap()` with your mail provider's IMAP
credentials (see README) — the rest of the pipeline doesn't need to change.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str


def load_from_json_folder(folder: str | Path) -> list[Email]:
    folder = Path(folder)
    emails = []
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text())
        emails.append(Email(
            id=data.get("id", path.stem),
            sender=data["sender"],
            subject=data["subject"],
            body=data["body"],
        ))
    return emails


def fetch_from_imap(host: str, username: str, password: str, folder: str = "INBOX",
                     limit: int = 20) -> list[Email]:
    """Real-world IMAP ingestion (optional). Requires network access to your mail
    server, which is not available in this sandboxed demo — included so the project
    is production-ready, not just a local toy.
    """
    import imaplib
    import email as email_lib
    from email.header import decode_header

    emails: list[Email] = []
    conn = imaplib.IMAP4_SSL(host)
    conn.login(username, password)
    conn.select(folder)

    status, data = conn.search(None, "UNSEEN")
    ids = data[0].split()[-limit:]

    for eid in ids:
        status, msg_data = conn.fetch(eid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)

        subject, encoding = decode_header(msg.get("Subject", ""))[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8", errors="ignore")

        sender = msg.get("From", "")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        emails.append(Email(id=eid.decode(), sender=sender, subject=subject, body=body))

    conn.logout()
    return emails
