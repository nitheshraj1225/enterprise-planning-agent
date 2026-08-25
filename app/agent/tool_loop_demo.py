"""
app/agent/tool_loop_demo.py

Module 4 (Tool Use with Claude) — the real multi-turn tool loop. Unlike
structured_output_demo.py's forced single call, Claude here decides for
itself whether it needs to call a tool, reads the result, and decides
again whether it needs another tool or is ready to answer.

Cost control:
    Mock-first, same pattern as the rest of the project. No network call,
    no tokens spent, unless USE_REAL_API is flipped to True.
"""

from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS

VELOCITY_LOOKUP_TOOL = {
    "name": "fetch_velocity_report",
    "description": "Look up a team's historical velocity report by team name.",
    "input_schema": {
        "type": "object",
        "properties": {
            "team_name": {"type": "string"},
        },
        "required": ["team_name"],
    },
}


def fetch_velocity_report(team_name: str) -> str:
    """
    The REAL function that executes the tool. Mocked for now — returns
    fixed text mimicking what a real lookup against
    app/data/synthetic_corpus/velocity_reports/ would return.
    """
    return f"Team {team_name} averaged 23 story points/sprint over the last 6 sprints."


def run_tool_loop(user_question: str, use_real: bool = USE_REAL_API) -> str:
    """
    Runs the multi-turn tool loop: sends the question to Claude, and keeps
    executing any tool Claude requests and feeding the result back, until
    Claude's stop_reason is no longer "tool_use" — at which point its
    final text answer is returned.
    """
    if not use_real:
        mock_tool_result = fetch_velocity_report("Alpha")
        return (
            f"[MOCK — no API call made] Based on the velocity lookup "
            f"({mock_tool_result}), Team Alpha has a stable, predictable "
            f"velocity — no red flags for this quarter's planning."
        )

    client = get_client()
    messages = [{"role": "user", "content": user_question}]

    while True:
        response = client.messages.create(
            model=TEST_MODEL,
            max_tokens=TEST_MAX_TOKENS,
            tools=[VELOCITY_LOOKUP_TOOL],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_call = response.content[0]
            tool_result = fetch_velocity_report(tool_call.input["team_name"])

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": tool_result,
                }]
            })
        else:
            return response.content[0].text


if __name__ == "__main__":
    result = run_tool_loop("What was Team Alpha's velocity last quarter?")
    print("Multi-turn tool loop result:")
    print(result)