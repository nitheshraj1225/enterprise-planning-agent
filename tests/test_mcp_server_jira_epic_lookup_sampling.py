"""
Tests for the sampling-threshold logic in jira_epic_lookup (app/mcp/server.py).

When an Epic's description is too thin (< 40 chars after stripping) to size
confidently, jira_epic_lookup uses MCP Sampling to ask the client's LLM to
draft a clarifying question. These tests exercise that threshold directly by
mocking requests.get (the Jira API call) and stubbing
ctx.request_context.session.create_message() — no real Jira or MCP
client/transport needed, since @mcp.tool() leaves the underlying function
directly callable.
"""

import asyncio
from unittest.mock import MagicMock, patch

import mcp.types as types

from app.mcp.server import jira_epic_lookup


class _FakeSession:
    """Records every create_message() call so tests can assert whether
    sampling fired at all, not just what it returned."""

    def __init__(self, reply_text="Can you clarify the acceptance criteria?"):
        self._reply_text = reply_text
        self.create_message_calls = []

    async def create_message(self, messages, max_tokens):
        self.create_message_calls.append({"messages": messages, "max_tokens": max_tokens})
        return types.CreateMessageResult(
            role="assistant",
            content=types.TextContent(type="text", text=self._reply_text),
            model="fake-model",
        )


class _FakeRequestContext:
    def __init__(self, session):
        self.session = session


class _FakeContext:
    """Minimal stand-in for mcp.server.fastmcp.Context — duck-types only
    the .request_context.session.create_message() path jira_epic_lookup uses."""

    def __init__(self, session):
        self.request_context = _FakeRequestContext(session)


def _run(coro):
    return asyncio.run(coro)


def _adf(text):
    """Minimal ADF doc wrapping a single text run — enough for
    _extract_description_text to walk and extract `text` verbatim."""
    return {"content": [{"content": [{"type": "text", "text": text}]}]}


def _fake_jira_response(summary, status_name, description_adf):
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "fields": {
            "summary": summary,
            "status": {"name": status_name},
            "description": description_adf,
        }
    }
    return resp


@patch("app.mcp.server.requests.get")
def test_thin_description_triggers_sampling_and_attaches_question(mock_get):
    # Sparsest possible input (no description at all) — the case the
    # sampling escape hatch exists for.
    mock_get.return_value = _fake_jira_response("Epic with no description", "To Do", None)
    session = _FakeSession(reply_text="What's the target completion quarter?")
    ctx = _FakeContext(session)

    result = _run(jira_epic_lookup(epic_key="EPA-1", ctx=ctx))

    assert result["description"] == ""
    assert len(session.create_message_calls) == 1
    assert result["clarifying_question"] == "What's the target completion quarter?"


@patch("app.mcp.server.requests.get")
def test_short_description_under_40_triggers_sampling(mock_get):
    # General below-threshold case, distinct from the empty-string edge case.
    mock_get.return_value = _fake_jira_response(
        "Epic with a short description", "To Do", _adf("Needs work")
    )
    session = _FakeSession()
    ctx = _FakeContext(session)

    result = _run(jira_epic_lookup(epic_key="EPA-2", ctx=ctx))

    assert len(session.create_message_calls) == 1
    assert "clarifying_question" in result


@patch("app.mcp.server.requests.get")
def test_description_exactly_40_chars_does_not_trigger_sampling(mock_get):
    # Exact boundary: len(description.strip()) < 40 is strict, so exactly
    # 40 chars must NOT trigger sampling — catches a <= vs < regression.
    description = "x" * 40  # exactly 40 chars
    mock_get.return_value = _fake_jira_response(
        "Epic at the boundary", "To Do", _adf(description)
    )
    session = _FakeSession()
    ctx = _FakeContext(session)

    result = _run(jira_epic_lookup(epic_key="EPA-3", ctx=ctx))

    assert len(session.create_message_calls) == 0
    assert "clarifying_question" not in result


@patch("app.mcp.server.requests.get")
def test_description_above_40_chars_does_not_trigger_sampling(mock_get):
    # A normal, healthy description should never invoke sampling at all.
    description = "This Epic covers the full onboarding flow redesign end to end."
    mock_get.return_value = _fake_jira_response(
        "Epic with a healthy description", "In Progress", _adf(description)
    )
    session = _FakeSession()
    ctx = _FakeContext(session)

    result = _run(jira_epic_lookup(epic_key="EPA-4", ctx=ctx))

    assert len(session.create_message_calls) == 0
    assert "clarifying_question" not in result


class _FailingSession:
    """Session whose create_message() always raises — stands in for a
    client that doesn't support the (optional) MCP Sampling capability,
    or any other sampling failure."""

    async def create_message(self, messages, max_tokens):
        raise RuntimeError("client does not support sampling")


class _NonTextSession:
    """Session that returns a spec-legal but non-text sampling result."""

    async def create_message(self, messages, max_tokens):
        return types.CreateMessageResult(
            role="assistant",
            content=types.ImageContent(type="image", data="ZmFrZQ==", mimeType="image/png"),
            model="fake-model",
        )


@patch("app.mcp.server.requests.get")
def test_sampling_failure_degrades_gracefully_without_clarifying_question(mock_get):
    # Thin description would normally trigger sampling, but the session's
    # create_message() raises — the whole lookup must still succeed.
    mock_get.return_value = _fake_jira_response("Epic with no description", "To Do", None)
    ctx = _FakeContext(_FailingSession())

    result = _run(jira_epic_lookup(epic_key="EPA-6", ctx=ctx))

    assert result["epic_key"] == "EPA-6"
    assert "clarifying_question" not in result


@patch("app.mcp.server.requests.get")
def test_non_text_sampling_content_degrades_gracefully(mock_get):
    # Sampling succeeds, but the client returned ImageContent instead of
    # TextContent — accessing .text directly would raise AttributeError.
    mock_get.return_value = _fake_jira_response("Epic with no description", "To Do", None)
    ctx = _FakeContext(_NonTextSession())

    result = _run(jira_epic_lookup(epic_key="EPA-7", ctx=ctx))

    assert result["epic_key"] == "EPA-7"
    assert "clarifying_question" not in result


@patch("app.mcp.server.requests.get")
def test_whitespace_padding_is_stripped_before_length_check(mock_get):
    # Raw length is 42 (>= 40), but the stripped length is only 2 — proves
    # .strip() is applied before the length check, not just decorative.
    description = " " * 40 + "hi"
    mock_get.return_value = _fake_jira_response(
        "Epic with padded description", "To Do", _adf(description)
    )
    session = _FakeSession()
    ctx = _FakeContext(session)

    result = _run(jira_epic_lookup(epic_key="EPA-5", ctx=ctx))

    assert len(session.create_message_calls) == 1
    assert "clarifying_question" in result
