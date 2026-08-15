"""
app/agent/structured_output_demo.py

Building with the Claude API — Module 1, final Lesson: "Structured output"

This is a STANDALONE demonstration, not wired into Conversation yet.

There are two ways to get structured (JSON) output from Claude:
  1. Message/prompt-based (what this file demonstrates): instruct Claude in
     the prompt to respond only in valid JSON matching a given shape. Simple
     to build, but not strictly enforced by the API — Claude could drift
     from the exact schema or add stray text around the JSON.
  2. Tool-forced schema (the real, production-grade version): define the
     desired fields as a tool's input schema and force Claude to "call" it
     via `tool_choice`, which the API actually enforces. This is the same
     mechanism Module 4 (Tool Use) is built on.

This project deliberately starts with approach #1 here, matching what the
"Building with the Claude API" course lesson taught, and will upgrade to
approach #2 once the real tool-use loop is built in Module 4 — building the
production version once, correctly, rather than twice.

Cost control:
    Mock-first, same pattern as client.py and conversation.py. No network
    call, no tokens spent, unless USE_REAL_API is flipped to True.
"""

import json

from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS

# The exact JSON shape we're asking Claude to return. Kept simple on
# purpose for this lesson — the real Epic-sizing schema will grow once
# this becomes the tool-forced version in Module 4.
EPIC_SIZING_INSTRUCTIONS = """
You are an enterprise planning assistant. Given a short description of an
Epic, respond with ONLY a valid JSON object — no other text before or
after it — matching exactly this shape:

{
  "epic_id": "<string, the Epic identifier if mentioned, else null>",
  "size_estimate": <integer, story points from 1-13>,
  "confidence": <float, 0.0-1.0>,
  "rationale": "<string, one sentence explaining the estimate>"
}
"""


def get_structured_epic_estimate(epic_description: str, use_real: bool = USE_REAL_API) -> dict:
    """
    Sends an Epic description to Claude with instructions to respond in a
    fixed JSON shape, parses the response with json.loads(), and returns
    a Python dict.

    Returns a dict either way (mock or real), so calling code doesn't need
    to know or care which one ran.
    """
    if not use_real:
        # Mock response mimics the exact JSON shape a real call should
        # produce, so downstream parsing code can be written and tested
        # against it without spending any tokens.
        mock_json_text = json.dumps({
            "epic_id": "EPIC-142",
            "size_estimate": 8,
            "confidence": 0.72,
            "rationale": (
                "[MOCK — no API call made] Based on similar historical "
                "Epics of comparable scope."
            ),
        })
        return json.loads(mock_json_text)

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        system=EPIC_SIZING_INSTRUCTIONS,
        messages=[{"role": "user", "content": epic_description}],
    )
    raw_text = response.content[0].text

    # This is exactly the fragility approach #1 has that approach #2
    # (tool-forced schema) doesn't: we're trusting Claude followed
    # instructions closely enough that json.loads() won't blow up. If
    # Claude added any stray text around the JSON, this raises an error —
    # a concrete, demonstrable reason to upgrade to tool-forced schemas
    # once the real tool-use loop exists.
    return json.loads(raw_text)


if __name__ == "__main__":
    # Run this file directly to see structured-output mechanics without
    # spending any tokens:
    #   python -m app.agent.structured_output_demo
    result = get_structured_epic_estimate(
        "Epic-142: migrate legacy reporting module to the new dashboard."
    )
    print("Parsed structured result:")
    print(result)
    print(f"\nType check — this is a real Python dict: {type(result)}")
    print(f"Direct field access works: result['size_estimate'] = {result['size_estimate']}")