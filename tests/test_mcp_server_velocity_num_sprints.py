"""
Test for the num_sprints=0 boundary in jira_velocity_fetch (app/mcp/server.py).

closed_sprints = sprints_resp.json()["values"][-num_sprints:] previously
treated num_sprints=0 as "no limit" instead of "zero sprints", because
Python's -0 == 0 makes [-0:] equivalent to [0:] (the whole list). This test
mocks all three Jira calls jira_velocity_fetch makes (field lookup, closed
sprints, and — critically — proves the sprint search is never reached at
all when num_sprints=0) — no real Jira or MCP client/transport needed,
since @mcp.tool() leaves the underlying function directly callable.
"""

import asyncio
from unittest.mock import MagicMock, patch

from app.mcp.server import jira_velocity_fetch


class _FakeContext:
    """Minimal stand-in for mcp.server.fastmcp.Context — duck-types only
    the report_progress()/info() calls jira_velocity_fetch uses. Neither
    should fire when there are zero sprints to analyze."""

    async def report_progress(self, progress, total, message):
        raise AssertionError("report_progress should not be called when num_sprints=0")

    async def info(self, message):
        raise AssertionError("info should not be called when num_sprints=0")


def _run(coro):
    return asyncio.run(coro)


def _fake_fields_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [{"id": "customfield_10016", "name": "Story Points"}]
    return resp


def _fake_sprints_response(sprint_names):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"values": [{"id": i, "name": name} for i, name in enumerate(sprint_names)]}
    return resp


@patch("app.mcp.server.requests.post")
@patch("app.mcp.server.requests.get")
def test_num_sprints_zero_returns_zero_sprints_not_all_sprints(mock_get, mock_post):
    # Board has 3 closed sprints on it — if the -0 bug were still present,
    # [-0:] would return all 3 instead of none.
    mock_get.side_effect = [
        _fake_fields_response(),
        _fake_sprints_response(["Sprint 1", "Sprint 2", "Sprint 3"]),
    ]
    ctx = _FakeContext()

    result = _run(jira_velocity_fetch(board_id=2, ctx=ctx, num_sprints=0))

    assert result["sprints_analyzed"] == []
    assert result["average_velocity"] == 0
    # The search/jql endpoint (requests.post) should never be reached —
    # there's nothing to analyze with zero sprints.
    mock_post.assert_not_called()
