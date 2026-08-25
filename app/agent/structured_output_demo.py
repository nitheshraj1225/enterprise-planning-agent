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
"Building with the Claude API" course lesson taught, and upgrades to
approach #2 below — building the production version once, correctly.

Cost control:
    Mock-first, same pattern as client.py and conversation.py. No network
    call, no tokens spent, unless USE_REAL_API is flipped to True.
"""

import json
from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS

# The exact JSON shape we're asking Claude to return (approach #1).
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

# Tool schema for approach #2 — the tool-forced version.
EPIC_SIZING_TOOL = {
    "name": "record_epic_estimate",
    "description": "Record a structured size estimate for an Epic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "epic_id": {"type": "string"},
            "size_estimate": {
                "type": "integer",
                "enum": [1, 2, 3, 5, 8, 13, 21]
            },
            "confidence": {"type": "number"},
            "rationale": {"type": "string"},
        },
        "required": ["epic_id", "size_estimate", "confidence", "rationale"],
    },
}


def get_structured_epic_estimate(epic_description: str, use_real: bool = USE_REAL_API) -> dict:
    """
    Approach #1: message-based structured output. Sends an Epic description
    to Claude with instructions to respond in a fixed JSON shape, parses the
    response with json.loads(), and returns a Python dict.
    """
    if not use_real:
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
    # instructions closely enough that json.loads() won't blow up.
    return json.loads(raw_text)


def get_structured_epic_estimate_tool_forced(epic_description: str, use_real: bool = USE_REAL_API) -> dict:
    """
    Approach #2: tool-forced structured output (Module 4 upgrade). Forces
    Claude to "call" a tool matching EPIC_SIZING_TOOL's schema — the API
    itself enforces the shape, no json.loads() needed.
    """
    if not use_real:
        return {
            "epic_id": "EPIC-142",
            "size_estimate": 8,
            "confidence": 0.72,
            "rationale": "[MOCK — no API call made] Based on similar historical Epics of comparable scope.",
        }

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        tools=[EPIC_SIZING_TOOL],
        tool_choice={"type": "tool", "name": "record_epic_estimate"},
        messages=[{"role": "user", "content": epic_description}],
    )
    return response.content[0].input


if __name__ == "__main__":
    print("=== Message-based version (Module 1) ===")
    result = get_structured_epic_estimate(
        "Epic-142: migrate legacy reporting module to the new dashboard."
    )
    print(result)

    print("\n=== Tool-forced version (Module 4 upgrade) ===")
    result_v2 = get_structured_epic_estimate_tool_forced(
        "Epic-142: migrate legacy reporting module to the new dashboard."
    )
    print(result_v2)
    print(f"\nType check: {type(result_v2)}")
    print(f"Direct field access: result_v2['size_estimate'] = {result_v2['size_estimate']}")