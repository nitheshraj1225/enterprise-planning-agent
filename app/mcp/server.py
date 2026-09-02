"""
MCP Server for the Enterprise Planning Intelligence Agent.

This exposes tools, a resource, and a prompt over the Model Context
Protocol (MCP) using local stdio transport. Any MCP-compatible client
(Claude Desktop, Claude Code, the MCP Inspector, or a custom script)
can discover and call these without needing project-specific
tool-calling code like Module 4's hand-rolled tool_choice loop.

erp_record_fetch, finance_policy_retrieve, check_recent_updates, and
create_action_request stay MOCKED — they return realistic, hardcoded
structured data. jira_epic_lookup and jira_velocity_fetch are REAL —
they call Jira Cloud's REST/Agile APIs directly, using the same
email/API-token auth pattern already used in scripts/seed_jira_data.py.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))  # so "app.audit..." resolves when run directly
import json
import requests
from dotenv import load_dotenv

load_dotenv()

FIBONACCI_SCALE = (1, 2, 3, 5, 8, 13, 21)
from app.audit.logger import get_audit_log
from mcp.server.fastmcp import FastMCP

# FastMCP is the high-level MCP server class. Passing a name here is
# just an identifier the server reports to clients (shown in the
# Inspector UI, for example) — it's not used for routing.
mcp = FastMCP("enterprise-planning-agent")

# --- Real Jira integration (MCP Advanced) -----------------------------
# Same email/token auth pattern already used in scripts/seed_jira_data.py.
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JIRA_AUTH = (JIRA_EMAIL, JIRA_API_TOKEN)
JIRA_HEADERS = {"Accept": "application/json"}


# ---------------------------------------------------------------------
# Tool 1: erp_record_fetch
# ---------------------------------------------------------------------
@mcp.tool()
def erp_record_fetch(record_id: str) -> dict:
    """
    Fetch a single ERP (Enterprise Resource Planning) record by ID.

    Args:
        record_id: The unique identifier of the ERP record to fetch,
            e.g. "ERP-4821".

    Returns:
        A dict with the record's status, owner, and last-updated date.
    """
    # MOCK: hardcoded response standing in for a real ERP system call.
    return {
        "record_id": record_id,
        "status": "Active",
        "owner": "Finance Ops Team",
        "last_updated": "2026-08-20",
        "source": "mock_erp",
    }


# ---------------------------------------------------------------------
# Tool 2: finance_policy_retrieve
# ---------------------------------------------------------------------
@mcp.tool()
def finance_policy_retrieve(policy_topic: str) -> dict:
    """
    Retrieve a finance policy summary for a given topic.

    Args:
        policy_topic: The finance policy area to look up, e.g.
            "capital expenditure approval" or "travel reimbursement".

    Returns:
        A dict with the policy's title, summary text, and effective date.
    """
    # MOCK: in a real build this might hit an internal knowledge base
    # or even reuse our own retrieve() from app/rag/retriever.py.
    return {
        "policy_topic": policy_topic,
        "title": f"Policy: {policy_topic.title()}",
        "summary": (
            f"Standard organizational policy governing {policy_topic}. "
            "Requires manager approval above $10,000 threshold."
        ),
        "effective_date": "2026-01-01",
        "source": "mock_finance_policy",
    }


# ---------------------------------------------------------------------
# Tool 3: check_recent_updates
# ---------------------------------------------------------------------
@mcp.tool()
def check_recent_updates(entity_id: str, days: int = 7) -> dict:
    """
    Check whether an entity (epic, record, etc.) has had recent updates.

    Args:
        entity_id: The ID of the entity to check, e.g. "PROJ-123".
        days: How many days back to look for updates. Defaults to 7.

    Returns:
        A dict with a boolean flag and a list of recent change summaries.
    """
    # MOCK: hardcoded to always report one recent change.
    return {
        "entity_id": entity_id,
        "days_checked": days,
        "has_recent_updates": True,
        "changes": [
            {"date": "2026-08-24", "change": "Status moved to In Progress"},
        ],
        "source": "mock_updates",
    }


# ---------------------------------------------------------------------
# Tool 4: create_action_request
# ---------------------------------------------------------------------
@mcp.tool()
def create_action_request(description: str, priority: str = "medium") -> dict:
    """
    Create an action request (e.g. a follow-up task or approval request).

    Args:
        description: What the action request is for.
        priority: One of "low", "medium", "high". Defaults to "medium".

    Returns:
        A dict confirming the request was created, with a mock request ID.
    """
    # MOCK: in a real build this would POST to a ticketing/workflow system.
    return {
        "request_id": "AR-00042",
        "description": description,
        "priority": priority,
        "status": "created",
        "source": "mock_action_request",
    }


# ---------------------------------------------------------------------
# Tool 5: jira_epic_lookup (REAL — MCP Advanced Topics)
# ---------------------------------------------------------------------
def _extract_description_text(description_adf):
    # Jira stores rich-text fields (like description) as ADF — a nested
    # JSON document format, not plain text. This walks it and joins the
    # plain text runs together, so callers get a normal string back.
    if not description_adf:
        return ""
    parts = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                parts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)

    walk(description_adf)
    return " ".join(parts)


@mcp.tool()
def jira_epic_lookup(epic_key: str) -> dict:
    """
    Fetch a real Epic's details from Jira Cloud.

    Args:
        epic_key: The Epic's Jira key, e.g. "EPA-6".

    Returns:
        A dict with the Epic's title, status, and description — same
        structured-dict shape as erp_record_fetch, backed by a live
        Jira API call instead of mock data.
    """
    resp = requests.get(f"{JIRA_BASE_URL}/rest/api/3/issue/{epic_key}", auth=JIRA_AUTH, headers=JIRA_HEADERS)
    if resp.status_code == 404:
        return {"error": f"Epic {epic_key} not found", "epic_key": epic_key}
    resp.raise_for_status()
    fields = resp.json()["fields"]
    return {
        "epic_key": epic_key,
        "title": fields["summary"],
        "status": fields["status"]["name"],
        "description": _extract_description_text(fields.get("description")),
        "source": "real_jira",
    }


# ---------------------------------------------------------------------
# Tool 6: jira_velocity_fetch (REAL — MCP Advanced Topics)
# ---------------------------------------------------------------------
def _get_story_points_field_id():
    # Per-site custom field ID, same lookup as the seed script — not
    # hardcoded, since it can differ across Jira sites.
    resp = requests.get(f"{JIRA_BASE_URL}/rest/api/3/field", auth=JIRA_AUTH, headers=JIRA_HEADERS)
    resp.raise_for_status()
    for f in resp.json():
        if f["name"].lower() in ("story point estimate", "story points"):
            return f["id"]
    return None


@mcp.tool()
def jira_velocity_fetch(board_id: int, num_sprints: int = 3) -> dict:
    """
    Compute a team's real historical velocity from the last N CLOSED
    sprints on a board — completed story points per sprint. This is the
    grounding evidence an Epic-sizing estimate needs: how much has this
    team actually delivered, not a guess.

    Args:
        board_id: The Jira Software board ID, e.g. 2.
        num_sprints: How many of the most recent closed sprints to
            analyze. Defaults to 3.

    Returns:
        A dict with per-sprint completed points and the average velocity.
    """
    points_field = _get_story_points_field_id()

    sprints_resp = requests.get(
        f"{JIRA_BASE_URL}/rest/agile/1.0/board/{board_id}/sprint?state=closed",
        auth=JIRA_AUTH, headers=JIRA_HEADERS,
    )
    sprints_resp.raise_for_status()
    closed_sprints = sprints_resp.json()["values"][-num_sprints:]

    sprint_results = []
    for sprint in closed_sprints:
        # NOTE: the classic GET /rest/api/3/search endpoint was retired
        # by Atlassian (410 Gone) — replaced by POST /rest/api/3/search/jql,
        # which takes fields as a list and a JSON body instead of query params.
        jql = f"sprint = {sprint['id']} AND statusCategory = Done"
        search_resp = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql",
            auth=JIRA_AUTH, headers={**JIRA_HEADERS, "Content-Type": "application/json"},
            json={"jql": jql, "fields": [points_field]},
        )
        search_resp.raise_for_status()
        issues = search_resp.json()["issues"]
        completed_points = sum(i["fields"].get(points_field) or 0 for i in issues)
        sprint_results.append({"sprint_name": sprint["name"], "completed_points": completed_points})

    avg_velocity = sum(s["completed_points"] for s in sprint_results) / len(sprint_results) if sprint_results else 0
    return {
        "board_id": board_id,
        "sprints_analyzed": sprint_results,
        "average_velocity": avg_velocity,
        "source": "real_jira",
    }


# ---------------------------------------------------------------------
# Prompt: Epic-sizing template
# ---------------------------------------------------------------------
@mcp.prompt()
def epic_sizing_prompt(epic_id: str) -> str:
    """
    Server-defined Epic-sizing prompt template, reusing Module 3's
    XML-tag + chain-of-thought pattern. Looks up the real Epic file
    from the synthetic corpus and returns a fully-populated prompt —
    not a blank template — ready to send to Claude.
    """
    epic_path = os.path.join("app", "data", "synthetic_corpus", "epics", f"{epic_id}.md")

    if not os.path.exists(epic_path):
        return f"No Epic found with ID {epic_id}."

    with open(epic_path, "r") as f:
        epic_content = f.read()  # whole file content, same "reuse the paragraph" spirit as RAG chunking

    return (
        "<epic_context>\n"
        f"{epic_content}"
        "\n</epic_context>\n"
        "<instructions>\n"
        f"Estimate the size of this Epic using the Fibonacci scale {FIBONACCI_SCALE}. "
        "Weigh two factors: (1) the overall scope of work described, and "
        "(2) any cross-team dependencies mentioned.\n"
        "</instructions>\n"
        "<reasoning>\n"
        "Before answering, work through: (1) which similar historical Epics "
        "this resembles, (2) any cross-team dependencies mentioned, "
        "(3) complexity signals from the scope of work described.\n"
        "</reasoning>\n"
        "<answer>\n"
        "Output only the single number from the scale above — no explanation, no extra text.\n"
        "</answer>"
    )


# ---------------------------------------------------------------------
# Resource: audit log
# ---------------------------------------------------------------------
@mcp.resource("audit://log")
def audit_log_resource() -> str:
    """
    Read-only MCP resource exposing the SOX-conscious audit log.
    """
    entries = get_audit_log()  # everything logged so far, oldest first
    return json.dumps(entries, indent=2)


# ---------------------------------------------------------------------
# Entry point: run the server over stdio transport.
# ---------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()