"""
Tests for non-404 Jira HTTP error handling in jira_epic_lookup and
jira_velocity_fetch (app/mcp/server.py).

A non-404 error status (401/403/429/5xx) previously hit a bare
raise_for_status() with no except clause, propagating as an unhandled
requests.exceptions.HTTPError. Both tools now catch that and return a
structured error result, the same pattern as their existing 404/timeout
branches. Mocks requests.get directly — no real Jira or MCP client/transport
needed, since @mcp.tool() leaves the underlying functions directly callable.
"""

import asyncio
from unittest.mock import MagicMock, patch

import requests

from app.mcp.server import jira_epic_lookup, jira_velocity_fetch


def _run(coro):
    return asyncio.run(coro)


def _fake_error_response(status_code):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} error")
    return resp


@patch("app.mcp.server.requests.get")
def test_jira_epic_lookup_non_404_http_error_returns_structured_error(mock_get):
    mock_get.return_value = _fake_error_response(500)
    # ctx is never touched — the error returns before any sampling call.
    ctx = object()

    result = _run(jira_epic_lookup(epic_key="EPA-1", ctx=ctx))

    assert "error" in result
    assert result["epic_key"] == "EPA-1"


@patch("app.mcp.server.requests.get")
def test_jira_velocity_fetch_field_lookup_http_error_returns_structured_error(mock_get):
    # The story-points field lookup is the first (and, here, only) call.
    mock_get.return_value = _fake_error_response(429)
    ctx = MagicMock()  # unused — the error returns before report_progress/info

    result = _run(jira_velocity_fetch(board_id=2, ctx=ctx))

    assert "error" in result
    assert result["board_id"] == 2
    assert "average_velocity" not in result
    ctx.report_progress.assert_not_called()
    ctx.info.assert_not_called()
