# CLAUDE.md

## Project Overview
Enterprise Planning Intelligence Agent — a portfolio project built alongside the CCAR-P certification path. An agentic system over Jira + synthetic ERP/finance data: RAG retrieval, a custom MCP server/client, tool-use loops, guardrails, an audit log, and an eval harness.
Full build history, decisions, and rationale: @CONTEXT.md

## Commands
- Activate venv (every new terminal): `source venv/bin/activate`
- Run any module from the project root (`~/enterprise-planning-agent`), never from `~`:
  - `python -m app.agent.structured_output_demo`
  - `python -m app.agent.tool_loop_demo`
  - `python -m app.rag.retriever`
  - `python -m app.features.claude_features_demo`
  - `python -m app.mcp.client`
- Run the MCP server directly, not with `-m` (the Inspector invokes it as a standalone script):
  `python app/mcp/server.py`
- Run the MCP Inspector: `npx @modelcontextprotocol/inspector`

## Architecture