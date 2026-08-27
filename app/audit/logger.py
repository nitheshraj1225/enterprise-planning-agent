import json
import os
from datetime import datetime

AUDIT_LOG_PATH = "app/audit/audit_log.jsonl"


def log_event(actor: str, action: str, details: dict = None) -> dict:
    """
    Append one audit entry to the JSONL file.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),  # e.g. "2026-08-27T14:32:01"
        "actor": actor,
        "action": action,
        "details": details or {},  # avoid storing None; store an empty dict instead
    }

    # "a" = append mode. If the file doesn't exist yet, Python creates it.
    # If it exists, this adds to the end without touching existing lines —
    # that's the whole mechanism behind "append-only."
    with open(AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")  # one JSON object, then a newline

    return entry


def get_audit_log(limit: int = None) -> list:
    """
    Read back audit entries from the JSONL file, oldest first.
    """
    # First run: no file exists yet, so there's nothing to read.
    if not os.path.exists(AUDIT_LOG_PATH):
        return []

    entries = []
    with open(AUDIT_LOG_PATH, "r") as f:
        for line in f:  # JSONL = one JSON object per line
            line = line.strip()
            if line:  # skip any blank lines
                entries.append(json.loads(line))

    if limit is not None:
        entries = entries[-limit:]  # last `limit` entries = the most recent ones

    return entries


if __name__ == "__main__":
    log_event("human:nithesh", "test_entry", {"note": "first audit log test"})
    print(get_audit_log())