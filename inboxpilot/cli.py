"""cli.py — Command-line interface.

Usage:
    python -m inboxpilot.cli run
    python -m inboxpilot.cli run --inbox path/to/emails --db path/to.db
    python -m inboxpilot.cli stats
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import storage
from .pipeline import run_pipeline

PRIORITY_LABEL = {5: "CRITICAL", 4: "HIGH", 3: "MEDIUM", 2: "LOW", 1: "MINIMAL"}


def cmd_run(args):
    results = run_pipeline(args.inbox, Path(args.db) if args.db else None)
    print(f"\nProcessed {len(results)} email(s):\n")
    for r in sorted(results, key=lambda x: -x["priority"]):
        label = PRIORITY_LABEL.get(r["priority"], r["priority"])
        print(f"[{label:>8}] {r['category']:<15} conf={r['confidence']:.2f}  "
              f"({r['engine']})  \"{r['subject']}\"  <{r['sender']}>")
        print(f"           → {r['reasoning']}")
    print()


def cmd_stats(args):
    conn = storage.get_connection(Path(args.db) if args.db else None)
    stats = storage.get_stats(conn)
    total = sum(stats.values())
    print(f"\nTotal processed: {total}")
    for category, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {category:<15} {count}")
    print()


def main():
    parser = argparse.ArgumentParser(prog="inboxpilot", description="AI email triage agent")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Process emails from an inbox folder")
    p_run.add_argument("--inbox", default="sample_data/inbox", help="Folder of JSON email files")
    p_run.add_argument("--db", default=None, help="Path to SQLite db (optional)")
    p_run.set_defaults(func=cmd_run)

    p_stats = sub.add_parser("stats", help="Show triage stats from the database")
    p_stats.add_argument("--db", default=None, help="Path to SQLite db (optional)")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
