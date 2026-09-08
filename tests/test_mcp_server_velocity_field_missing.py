"""
Test for the story-points-field-missing abstention in jira_velocity_fetch
(app/mcp/server.py).

Per this project's groundedness principle (never invent, abstain when data
is missing — see CONTEXT.md's Success Metrics), jira_velocity_fetch must
NOT silently return average_velocity: 0 when the Jira site's story-points
custom field can't be found — that would look like a real, ground-truthed
answer to whatever calls it. Instead it must return a structured error
result and stop before querying any sprints. This test exercises that
directly by mocking requests.get (the field-lookup call) to return a field
list with no story-points field — no real Jira or MCP client/transport
needed, since @mcp.tool() leaves the underlying function directly callable.
"""

import asyncio
from unittest.mock import MagicMock, patch

from app.mcp.server import jira_velocity_fetch


class _FakeContext:
    """Minimal stand-in for mcp.server.fastmcp.Context. Not expected to be
    touched in this test — the field-missing abstention must return before
    any progress/info reporting happens."""

    async def report_progress(self, progress, total, message):
        raise AssertionError("report_progress should not be called when the story-points field is missing")

    async def info(self, message):
        raise AssertionError("info should not be called when the story-points field is missing")


def _run(coro):
    return asyncio.run(coro)


def _fake_fields_response(field_names):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [{"id": f"customfield_{i}", "name": name} for i, name in enumerate(field_names)]
    return resp


@patch("app.mcp.server.requests.get")
def test_missing_story_points_field_returns_abstention_not_zero(mock_get):
    # Field list has no "Story Point Estimate" / "Story points" entry —
    # the exact case _get_story_points_field_id() returns None for.
    mock_get.return_value = _fake_fields_response(["Summary", "Status", "Priority"])
    ctx = _FakeContext()

    result = _run(jira_velocity_fetch(board_id=2, ctx=ctx))

    assert "error" in result
    assert "average_velocity" not in result
    assert "sprints_analyzed" not in result
    assert result["board_id"] == 2
    # Only the field-lookup call should have fired — no sprint or search calls.
    mock_get.assert_called_once()
