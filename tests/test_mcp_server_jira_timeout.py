"""
Test for Jira request timeout handling in jira_epic_lookup (app/mcp/server.py).

Every Jira HTTP call in this module now passes timeout=JIRA_TIMEOUT_SECONDS,
so an unresponsive Jira endpoint can't hang the tool call forever. This test
confirms the OTHER half of that fix: when requests.get actually raises
requests.exceptions.Timeout, jira_epic_lookup must catch it and return a
clear structured error result — not hang (impossible to test directly, but
covered by the timeout kwarg itself) and not propagate an unhandled
exception up through the MCP tool call. Mocks requests.get directly — no
real Jira or MCP client/transport needed, since @mcp.tool() leaves the
underlying function directly callable.
"""

import asyncio
from unittest.mock import patch

import requests

from app.mcp.server import jira_epic_lookup


def _run(coro):
    return asyncio.run(coro)


@patch("app.mcp.server.requests.get")
def test_jira_timeout_returns_clear_error_not_unhandled_exception(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
    # ctx is never touched — the timeout is caught before any sampling
    # call would happen, so a bare object() catches any regression that
    # tries to use it (an AttributeError, instead of silent success).
    ctx = object()

    result = _run(jira_epic_lookup(epic_key="EPA-1", ctx=ctx))

    assert result["error"] == "Jira request timed out while fetching Epic EPA-1"
    assert result["epic_key"] == "EPA-1"
    mock_get.assert_called_once()
    # The timeout kwarg is what actually prevents the hang in production.
    _, call_kwargs = mock_get.call_args
    assert call_kwargs["timeout"] == 10
