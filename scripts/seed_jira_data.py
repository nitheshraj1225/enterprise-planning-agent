"""
Jira Sample Data Seed Script — one-off setup utility, NOT part of the
production app/ package.

Author: Nithesh Bongoni

Why this exists: jira_velocity_fetch (MCP Advanced, Module 7) needs real
CLOSED sprints with completed story points to compute velocity from — an
empty board returns nothing meaningful. This script creates a few Epics,
a few Stories with story points under each, then creates 3 sprints,
starts each one, marks its stories Done, and closes it — so there's real
historical throughput to pull from later. This is bulk setup data, the
same category as app/data/corpus_generator.py, not a concept to learn
through struggle-first coding — handed over as complete, runnable code.

Run once: python scripts/seed_jira_data.py
"""

import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"].rstrip("/")
JIRA_EMAIL = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
PROJECT_KEY = "EPA"
BOARD_ID = 2

AUTH = (JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def api(method, path, **kwargs):
    """Every Jira call shares base URL, auth, and error handling — callers
    below just pass the path and JSON payload, not repeat this plumbing."""
    url = f"{JIRA_BASE_URL}{path}"
    resp = requests.request(method, url, auth=AUTH, headers=HEADERS, **kwargs)
    resp.raise_for_status()
    return resp.json() if resp.text else {}


def get_issue_type_id(name):
    # Team-managed projects assign their own numeric IDs to issue types —
    # not fixed across sites — so we look them up instead of hardcoding.
    meta = api(
        "GET",
        f"/rest/api/3/issue/createmeta?projectKeys={PROJECT_KEY}&expand=projects.issuetypes",
    )
    for it in meta["projects"][0]["issuetypes"]:
        if it["name"].lower() == name.lower():
            return it["id"]
    raise RuntimeError(f"Issue type '{name}' not found on project {PROJECT_KEY}")


def get_story_points_field_id():
    # The "Story point estimate" custom field also has a per-site ID —
    # discovered by name rather than assumed.
    for f in api("GET", "/rest/api/3/field"):
        if f["name"].lower() in ("story point estimate", "story points"):
            return f["id"]
    raise RuntimeError("Story points field not found on this site")


def create_epic(epic_type_id, summary):
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "issuetype": {"id": epic_type_id},
            "summary": summary,
        }
    }
    result = api("POST", "/rest/api/3/issue", json=payload)
    print(f"Created Epic {result['key']}: {summary}")
    return result["key"]


def create_story(story_type_id, points_field_id, summary, epic_key, points):
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "issuetype": {"id": story_type_id},
            "summary": summary,
            "parent": {"key": epic_key},
            points_field_id: points,
        }
    }
    result = api("POST", "/rest/api/3/issue", json=payload)
    print(f"  Created Story {result['key']} ({points} pts) under {epic_key}")
    return result["key"]


def get_done_transition_id(issue_key):
    # Workflow transition IDs are per-site too — ask the issue itself what
    # transitions are available and find the one named "Done".
    transitions = api("GET", f"/rest/api/3/issue/{issue_key}/transitions")["transitions"]
    for t in transitions:
        if t["name"].lower() == "done":
            return t["id"]
    raise RuntimeError(f"No 'Done' transition found for {issue_key} — check your workflow's status names")


def mark_done(issue_key, transition_id):
    api("POST", f"/rest/api/3/issue/{issue_key}/transitions", json={"transition": {"id": transition_id}})


def create_sprint(name, start_iso, end_iso):
    payload = {
        "name": name,
        "originBoardId": BOARD_ID,
        "startDate": start_iso,
        "endDate": end_iso,
    }
    return api("POST", "/rest/agile/1.0/sprint", json=payload)["id"]


def set_sprint_state(sprint_id, **fields):
    # Partial update — only the fields passed here get changed, everything
    # else on the sprint stays as-is. Used both to start and to close.
    api("POST", f"/rest/agile/1.0/sprint/{sprint_id}", json=fields)


def add_issues_to_sprint(sprint_id, issue_keys):
    api("POST", f"/rest/agile/1.0/sprint/{sprint_id}/issue", json={"issues": issue_keys})


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def main():
    epic_type_id = get_issue_type_id("Epic")
    story_type_id = get_issue_type_id("Story")
    points_field_id = get_story_points_field_id()

    epics = [
        create_epic(epic_type_id, "Migrate notification service for Payments Platform"),
        create_epic(epic_type_id, "Consolidate reporting dashboards for Finance"),
        create_epic(epic_type_id, "Upgrade identity provider integration"),
    ]

    # Three 2-week sprints, sequential, ending today — realistic recent
    # closed-sprint history for velocity to be computed from.
    today = datetime.utcnow()
    sprint_windows = [
        (today - timedelta(days=42), today - timedelta(days=28)),
        (today - timedelta(days=28), today - timedelta(days=14)),
        (today - timedelta(days=14), today),
    ]

    done_transition_id = None
    for i, (start, end) in enumerate(sprint_windows, start=1):
        epic_key = epics[(i - 1) % len(epics)]
        story_keys = [
            create_story(story_type_id, points_field_id, f"Sprint {i} task A", epic_key, 3),
            create_story(story_type_id, points_field_id, f"Sprint {i} task B", epic_key, 5),
            create_story(story_type_id, points_field_id, f"Sprint {i} task C", epic_key, 2),
        ]

        sprint_id = create_sprint(f"Sprint {i}", iso(start), iso(end))
        add_issues_to_sprint(sprint_id, story_keys)
        set_sprint_state(sprint_id, state="active", startDate=iso(start), endDate=iso(end))

        if done_transition_id is None:
            done_transition_id = get_done_transition_id(story_keys[0])
        for key in story_keys:
            mark_done(key, done_transition_id)

        set_sprint_state(sprint_id, state="closed", completeDate=iso(end))
        print(f"Closed Sprint {i} — {sum([3, 5, 2])} points completed\n")

    print("Done. 3 Epics, 9 Stories, 3 closed sprints created.")


if __name__ == "__main__":
    main()