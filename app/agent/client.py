"""
app/agent/client.py

Claude Platform 101 — Lesson 2: "Your first API call"

This module wraps Anthropic client setup and a single test call, built as
real project code rather than a throwaway example. `orchestrator.py` will
later import `get_client()` directly instead of reinventing this.

Cost control:
    By default, `test_connection()` runs in MOCK mode — no network call,
    no tokens spent. Flip `USE_REAL_API = True` (or pass `use_real=True`)
    only when you deliberately want to see one real response.

    When it does run live, it targets claude-haiku-4-5 with a small
    max_tokens cap — a real call this way costs a fraction of a cent.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Toggle this manually when you want a real API call instead of the mock.
USE_REAL_API = False

# Cheapest model, capped output — keeps a "real" test call effectively free.
TEST_MODEL = "claude-haiku-4-5"
TEST_MAX_TOKENS = 40


def get_client():
    """
    Instantiate and return the Anthropic client, reading ANTHROPIC_API_KEY
    from the environment (loaded via .env through python-dotenv, same
    pattern app/main.py already uses).

    Raises a clear error early if the key is missing, rather than letting
    a confusing 401 surface later deep inside the agent loop.
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Check your .env file and that "
            "load_dotenv() ran before get_client() was called."
        )
    return anthropic.Anthropic(api_key=api_key)


class _MockResponse:
    """
    Mimics the shape of a real anthropic.types.Message response just
    enough for this lesson: response.content[0].text

    This lets you write and run code against the real response shape
    without spending any tokens.
    """

    def __init__(self, text: str):
        self.content = [type("Block", (), {"text": text})()]


def test_connection(use_real: bool = USE_REAL_API) -> str:
    """
    Sends one test prompt tied to the project's actual domain — not a
    generic "hello world" — so the first call is already contextually
    relevant to the Enterprise Planning Intelligence Agent.

    Returns the response text either way, so calling code doesn't need
    to know or care whether it was mocked.
    """
    prompt = (
        "In one sentence, explain what an Epic sizing estimate is in "
        "the context of enterprise agile planning."
    )

    if not use_real:
        mock_text = (
            "[MOCK RESPONSE — no API call made] An Epic sizing estimate is "
            "a high-level effort/complexity score assigned to a large body "
            "of work before it's broken into sprint-sized stories, used to "
            "plan capacity across a planning cycle."
        )
        return mock_text

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


if __name__ == "__main__":
    # Run this file directly to see the result:
    #   python -m app.agent.client
    #
    # By default this is FREE (mocked). To see one real Haiku response,
    # set USE_REAL_API = True above, or run:
    #   python -c "from app.agent.client import test_connection; print(test_connection(use_real=True))"
    result = test_connection()
    print(result)