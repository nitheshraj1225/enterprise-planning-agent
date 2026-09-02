"""
MCP Client for the Enterprise Planning Intelligence Agent.
Author: Nithesh Bongoni

Course topics: "Implementing a Client — Using ClientSession" +
"Accessing Resources" + "Prompts in the Client"

server.py exposes tools, a resource, and a prompt template; this file
is the CLIENT that connects and uses all three, replacing the Inspector
(a generic test tool) with real code.

Analogy: server.py is a kitchen that cooks dishes (tools) on request,
keeps a readable logbook (the audit://log resource), and has a printed
recipe card (the epic_sizing_prompt template) it can hand you filled
in for a specific dish. This file is the waiter — connects, reads the
menu, places an order, reads the logbook, and asks for a recipe card.
Maps to Architecture's "FastAPI Agent Endpoint → MCP Server" arrow,
written by hand.
"""

import asyncio
from pathlib import Path
import mcp.types as types
from app.agent.client import get_client, TEST_MODEL
from pydantic import AnyUrl  # resource URIs are typed, not plain strings — see read_resource() below
from mcp.client.stdio import stdio_client, StdioServerParameters  # launches the server subprocess, gives raw I/O streams
from mcp.client.session import ClientSession  # speaks the actual MCP protocol over those streams

async def handle_sampling_message(context, params):
    """
    Real Sampling handler — the CLIENT side of MCP Sampling. When the
    server sends a sampling/createMessage request (e.g. jira_epic_lookup
    asking for a clarifying question on a thin Epic description), this
    is what actually calls Claude, replacing the Inspector's stub-model
    echo from earlier testing with a genuine answer.

    Workflow: pull the server's prompt text out of params.messages ->
    call Claude via the same get_client()/TEST_MODEL this project
    already uses everywhere else -> wrap Claude's answer back into the
    CreateMessageResult shape the MCP protocol expects -> return it.
    """
    prompt_text = params.messages[-1].content.text  # the server's actual ask

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=params.maxTokens,
        messages=[{"role": "user", "content": prompt_text}],
    )

    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(type="text", text=response.content[0].text),
        model=TEST_MODEL,
        stopReason="endTurn",
    )

async def handle_list_roots(context):
    """
    Real Roots handler — the CLIENT side of MCP Roots. Declares the one
    directory this client is willing to let the server read Epic files
    from, enforced server-side in epic_sizing_prompt before any file is
    opened.

    Workflow: find the project root relative to this file -> point at
    the one directory that should be in-bounds (the synthetic corpus)
    -> return it as a declared Root.
    """
    project_root = Path(__file__).resolve().parents[2]  # app/mcp/client.py -> project root
    corpus_dir = project_root / "app" / "data" / "synthetic_corpus"
    return types.ListRootsResult(
        roots=[types.Root(uri=f"file://{corpus_dir}", name="Synthetic Corpus")]
    )


async def main():
    # Same command as running the server manually — client launches it as a subprocess
    server_params = StdioServerParameters(command="python", args=["app/mcp/server.py"])

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream, sampling_callback=handle_sampling_message, list_roots_callback=handle_list_roots) as session:
            await session.initialize()  # protocol handshake, required before any real calls

            # Discovery — what tools does the server offer?
            tools_response = await session.list_tools()
            print("Available tools:", [t.name for t in tools_response.tools])

            # Invocation — actually call one, with real arguments
            result = await session.call_tool("erp_record_fetch", {"record_id": "ERP-4821"})
            print("Result:", result)

            # Discovery — what resources does the server offer?
            resources_response = await session.list_resources()
            print("Available resources:", [str(r.uri) for r in resources_response.resources])

            # Access — read the audit log resource. AnyUrl() converts the
            # plain string into the URI type read_resource() expects.
            resource_result = await session.read_resource(AnyUrl("audit://log"))
            print("Resource content:", resource_result.contents[0].text)

            # Discovery — what prompt templates does the server offer?
            prompts_response = await session.list_prompts()
            print("Available prompts:", [p.name for p in prompts_response.prompts])

            # Fetch — get the template filled in for a real Epic
            prompt_result = await session.get_prompt("epic_sizing_prompt", {"epic_id": "EPIC-0001"})
            print("Prompt content:", prompt_result.messages[0].content.text)

            # Roots — the prompt call above (EPIC-0001) already proves the
            # normal case still works now that Roots checking is wired in.
            # This proves the boundary is actually enforced, not just
            # declared: a path-traversal epic_id should be refused, not read.
            blocked_result = await session.get_prompt("epic_sizing_prompt", {"epic_id": "../../../etc/passwd"})
            print("Roots boundary test (should be refused):", blocked_result.messages[0].content.text)

            # Sampling — call the tool on a thin-description Epic and let
            # our real handle_sampling_message() answer the server's
            # clarifying-question request, instead of the Inspector's stub.
            epic_result = await session.call_tool("jira_epic_lookup", {"epic_key": "EPA-6"})
            print("Epic lookup (with real Sampling):", epic_result)


if __name__ == "__main__":
    asyncio.run(main())  # entry point for any async program