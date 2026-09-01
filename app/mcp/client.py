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
from pydantic import AnyUrl  # resource URIs are typed, not plain strings — see read_resource() below
from mcp.client.stdio import stdio_client, StdioServerParameters  # launches the server subprocess, gives raw I/O streams
from mcp.client.session import ClientSession  # speaks the actual MCP protocol over those streams


async def main():
    # Same command as running the server manually — client launches it as a subprocess
    server_params = StdioServerParameters(command="python", args=["app/mcp/server.py"])

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
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


if __name__ == "__main__":
    asyncio.run(main())  # entry point for any async program