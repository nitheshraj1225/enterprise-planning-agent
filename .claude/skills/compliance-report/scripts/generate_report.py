#!/usr/bin/env python3
"""
Compliance report generator.

Reads the append-only audit log (app/audit/audit_log.jsonl) and produces a
summary for a given date range: total actions, a breakdown by actor and by
action type, and a called-out list of human-approved actions.

Must be run from the project root (so the relative audit log path resolves).

Usage:
    python .claude/skills/compliance-report/scripts/generate_report.py \
        --start 2026-08-01 --end 2026-08-31

    (--start and --end are optional; omitting either leaves that side of the
    range open. Dates are ISO format, YYYY-MM-DD.)
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime

AUDIT_LOG_PATH = "app/audit/audit_log.jsonl"


def load_entries():
    if not os.path.exists(AUDIT_LOG_PATH):
        print(f"No audit log found at {AUDIT_LOG_PATH}. Run this from the project root.",
              file=sys.stderr)
        sys.exit(1)
    entries = []
    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def parse_date_bound(value, end_of_day=False):
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


def in_range(entry, start, end):
    ts = datetime.fromisoformat(entry["timestamp"])
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True


def is_human_approved(entry):
    # Convention in this project: actors representing a human-confirmed
    # action are logged as "human:<name>" (see app/audit/logger.py usage).
    return entry.get("actor", "").startswith("human:")


def build_report(entries, start, end):
    filtered = [e for e in entries if in_range(e, start, end)]

    actor_counts = Counter(e["actor"] for e in filtered)
    action_counts = Counter(e["action"] for e in filtered)
    human_approved = [e for e in filtered if is_human_approved(e)]

    lines = []
    lines.append("=" * 60)
    lines.append("COMPLIANCE REPORT")
    lines.append("=" * 60)
    range_desc = f"{start.date() if start else 'earliest'} to {end.date() if end else 'latest'}"
    lines.append(f"Date range: {range_desc}")
    lines.append(f"Total actions logged: {len(filtered)}")
    lines.append("")

    lines.append("-- Breakdown by actor --")
    if actor_counts:
        for actor, count in actor_counts.most_common():
            lines.append(f"  {actor}: {count}")
    else:
        lines.append("  (no entries in range)")
    lines.append("")

    lines.append("-- Breakdown by action type --")
    if action_counts:
        for action, count in action_counts.most_common():
            lines.append(f"  {action}: {count}")
    else:
        lines.append("  (no entries in range)")
    lines.append("")

    lines.append(f"-- Human-approved actions ({len(human_approved)}) --")
    if human_approved:
        for e in human_approved:
            details = json.dumps(e.get("details", {}))
            lines.append(f"  [{e['timestamp']}] {e['actor']} -> {e['action']} {details}")
    else:
        lines.append("  (none in range)")
    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a compliance report from the audit log.")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD), inclusive")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD), inclusive")
    parser.add_argument("--out", default=None, help="Optional path to also write the report to a file")
    args = parser.parse_args()

    start = parse_date_bound(args.start, end_of_day=False)
    end = parse_date_bound(args.end, end_of_day=True)

    entries = load_entries()
    report = build_report(entries, start, end)

    print(report)

    if args.out:
        with open(args.out, "w") as f:
            f.write(report + "\n")
        print(f"\nReport also written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
