"""
MCP Client for the Enterprise Planning Intelligence Agent.
Author: Nithesh Bongoni

Course topic: "Implementing a Client — Using ClientSession"

server.py exposes tools; this file is the CLIENT that connects and uses
them, replacing the Inspector (a generic test tool) with real code.

Analogy: server.py is a kitchen that cooks dishes (tools) on request.
This file is the waiter — connects, reads the menu, places an order,
brings back the result. Maps to Architecture's "FastAPI Agent Endpoint
→ MCP Server" arrow, written by hand.
"""

import asyncio
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


if __name__ == "__main__":
    asyncio.run(main())  # entry point for any async program