"""
MCP Server for the Enterprise Planning Intelligence Agent.

This exposes 4 tools over the Model Context Protocol (MCP) using local
stdio transport. Any MCP-compatible client (Claude Desktop, Claude Code,
the MCP Inspector, or a custom script) can discover and call these tools
without needing project-specific tool-calling code like Module 4's
hand-rolled tool_choice loop.

All 4 tools are MOCKED this week (Wednesday) — they return realistic,
hardcoded structured data. Thursday swaps erp_record_fetch and
finance_policy_retrieve's bodies for real Jira API calls, keeping the
same function signature and same dict shape, so nothing downstream
(the LLM's understanding of the tool, the client code) needs to change.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))  # so "app.audit..." resolves when run directly
import json
FIBONACCI_SCALE = (1, 2, 3, 5, 8, 13, 21)
from app.audit.logger import get_audit_log
from mcp.server.fastmcp import FastMCP

# FastMCP is the high-level MCP server class. Passing a name here is
# just an identifier the server reports to clients (shown in the
# Inspector UI, for example) — it's not used for routing.
mcp = FastMCP("enterprise-planning-agent")


# ---------------------------------------------------------------------
# Tool 1: erp_record_fetch
# ---------------------------------------------------------------------
# @mcp.tool() reads this function's type hints and docstring to
# auto-generate the JSON Schema a client needs to call it correctly.
# Compare this to Module 4, where we hand-wrote input_schema dicts —
# FastMCP generates that schema for us from ordinary Python.
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
    # Thursday-equivalent tools (Jira) will replace this body with an
    # actual HTTP request, but keep this same dict shape.
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
# Tool 5: prompt_request
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
# Resources are read-only — a client fetches data at a fixed URI,
# rather than calling a function with arguments like a tool. Content
# must be a string/bytes, so entries get JSON-serialized here.
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
# stdio is our documented Architecture decision for this phase — the
# server reads/writes MCP messages over stdin/stdout. Remote transports
# (HTTP/SSE + OAuth 2.1/PKCE) are explicitly deferred to Phase 2.
if __name__ == "__main__":
    mcp.run()