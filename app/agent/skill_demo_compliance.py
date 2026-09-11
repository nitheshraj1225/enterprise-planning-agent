"""
Agent Skills demo driver.

Runs a live Claude Agent SDK session with Agent Skills enabled, so the
`compliance-report` skill (.claude/skills/compliance-report/SKILL.md) can be
discovered and dispatched the same way it would be in production: the skill's
name + description are pre-loaded into the system prompt, and Claude decides
on its own to read the full SKILL.md and run the bundled script when the
user's request matches it (progressive disclosure).

Must be run from the project root, with the Claude Agent SDK installed
(`pip install claude-agent-sdk`) and ANTHROPIC_API_KEY set.

Run as a module (not as a script) so the "app" package resolves:
    python -m app.agent.skill_demo_compliance "Generate a compliance report for August 2026"
"""

import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from app.audit.logger import log_event


async def run_skill_demo(prompt: str) -> None:
    options = ClaudeAgentOptions(
        cwd=".",
        # Skills only load from disk if their source is listed here.
        # "project" picks up .claude/skills/, "user" picks up ~/.claude/skills/.
        setting_sources=["user", "project"],
        # "all" lets Claude choose among every discovered skill based on its
        # name + description, rather than restricting to an explicit list.
        skills="all",
        # The skill's script needs the Bash tool to actually execute.
        allowed_tools=["Bash", "Read"],
    )

    print(f"--- Prompt ---\n{prompt}\n")
    print("--- Agent run ---")

    saw_skill_load = False

    # Messages from query() are typed dataclass instances (SystemMessage,
    # AssistantMessage, ResultMessage, ...) — NOT dicts with a "type" key.
    # The SDK's own docs pattern is to isinstance()-check the message object
    # itself, then its content blocks (TextBlock, ToolUseBlock, ...).
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, SystemMessage):
            # subtype "init" carries the session's startup data, including
            # which skills were discovered — print the raw dataclass so the
            # actual field names are visible on your machine even if the
            # exact attribute name differs across SDK versions.
            if getattr(message, "subtype", None) == "init":
                print(f"[system/init] {message!r}")
                saw_skill_load = True

        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"[tool call] {block.name}: {block.input}")

        elif isinstance(message, ResultMessage):
            print(f"\n--- Run complete (subtype={message.subtype}) ---")

    if not saw_skill_load:
        print("\n[warning] No system/init message was observed — "
              "check that setting_sources includes 'project' and the skill directory exists.")

    log_event(
        actor="agent:skill_demo",
        action="compliance_report_skill_invoked",
        details={"prompt": prompt},
    )


def main():
    prompt = " ".join(sys.argv[1:]) or "Generate a compliance report covering all logged activity."
    asyncio.run(run_skill_demo(prompt))


if __name__ == "__main__":
    main()
