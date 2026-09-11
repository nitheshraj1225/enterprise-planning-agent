---
name: compliance-report
description: Generate a compliance report summarizing audit log activity (total actions, breakdown by actor and action type, human-approved actions) for a given date range. Use when asked for an audit summary, compliance report, or "what happened between X and Y."
---

# Compliance Report

This skill turns the project's append-only audit log (`app/audit/audit_log.jsonl`,
written by `app/audit/logger.py`) into a human-readable compliance summary for
a specified date range.

## When to use this

Use this skill when asked to:
- Produce a compliance or audit report for a date range ("show me what happened in August")
- Summarize agent/human activity for a review or governance check
- List which actions were human-approved before execution

Do not use this for routine, always-on queries about a single Epic or sizing
estimate — this is specifically for retrospective audit summaries.

## How to run it

Run the bundled script from the project root using the Bash tool:

```
python .claude/skills/compliance-report/scripts/generate_report.py --start 2026-08-01 --end 2026-08-31
```

- `--start` and `--end` are optional ISO dates (`YYYY-MM-DD`), inclusive. Omit
  either to leave that side of the range open (e.g. omit `--end` to include
  everything up to the most recent entry).
- Add `--out <path>` to also save the report to a file.

The script must run from the project root so the relative audit log path
(`app/audit/audit_log.jsonl`) resolves correctly.

## What the report contains

- **Total actions logged** in the date range
- **Breakdown by actor** (e.g. `human:nithesh`, `agent:sizing`, etc.), most
  active first
- **Breakdown by action type**, most frequent first
- **Human-approved actions**, called out separately — any entry whose actor
  is logged as `human:<name>`, per this project's audit-logging convention
  (see `app/audit/logger.py`). This is the list a reviewer cares about most:
  it shows exactly which side-effecting actions had explicit human sign-off.

## Output

Plain text, printed to stdout (and optionally written to a file with `--out`).
Present it to the user as-is, or summarize the key numbers in your reply if
the user only wants highlights.
