# Enterprise Planning Intelligence Agent

An agentic AI system that answers cross-system enterprise planning questions and generates explainable Epic sizing estimates — grounded in real project-tracking data, cited to source, and gated behind human approval before any action fires.

## The problem

During compressed annual planning cycles, delivery teams running Agile/SAFe processes spend a disproportionate share of their time on manual estimation mechanics rather than on delivery itself. The information needed to size work confidently — historical team velocity, capacity, dependencies, budget constraints — typically lives scattered across a project-tracking tool, an ERP system, and finance policy documents that don't talk to each other. That fragmentation, not a lack of process rigor, is what drives inconsistent sizing inputs and delayed planning outputs across the enterprise.

## What it does

The agent answers questions like "what's the status," "what's blocking this," "what should we do next," and "how should we size this Epic" — grounded in real data pulled live from a project-tracking API, cited back to its source, with every step logged for audit. A second, independent agent critiques each sizing estimate's rationale against the same retrieved evidence before it's ever returned, catching plausible-sounding but ungrounded reasoning rather than letting it through unchecked. Any action with a real side effect requires explicit human confirmation before it executes.

## Architecture

```
User Query
    │
    ▼
FastAPI Agent Endpoint
    │
    ├── RAG Layer (Chroma vector store)
    │     └── Synthetic docs: sizing policies, ERP records,
    │          finance data, historical Epic data
    │
    ├── MCP Server (6 tools)
    │     ├── Live project-tracking API integration (read)
    │     ├── Velocity/throughput lookup (read)
    │     ├── ERP record fetch (mock — read)
    │     ├── Finance policy retrieval (mock — read)
    │     ├── Recent-updates polling (simulation)
    │     └── Action request (write — human confirmation required)
    │
    ├── Guardrails
    │     └── Prompt injection defense + input validation,
    │          mapped to the OWASP LLM Top 10
    │
    ├── Append-Only Audit Log
    │     └── Every agent step, tool call, human decision, timestamp, reasoning
    │
    ├── Groundedness-Critique Subagent
    │     └── Independently verifies each sizing draft against retrieved
    │          evidence before it's returned
    │
    └── Eval Harness
          ├── Retrieval recall (≥ 85%)
          ├── Groundedness, LLM-as-judge (≥ 90%)
          └── Correct abstention rate (measured + reported)
```

## Why these choices

**Native Claude tool-use loop, not a framework.** Every agent step needs to be independently auditable — a framework that abstracts away the tool-calling loop makes that harder to guarantee, which matters in a governance-sensitive planning context.

**Groundedness over recall as the top-priority metric.** A missed retrieval fails safe — the system can say "I don't have enough information." A hallucinated fact fails dangerous — it's delivered with the same confident tone as a correct one, and a human is more likely to act on it directly.

**Human approval before any write action.** Rule-based, explainable, human-confirmed decisions are preferable to a faster but unexplainable automated one in an enterprise planning context, where a wrong sizing estimate or dependency claim has real downstream cost.

**Chroma for the proof of concept, pgvector as the documented production path.** Zero infrastructure to get RAG retrieval working during development; pgvector is the natural next step once this runs against an organization's existing Postgres infrastructure.

## Eval results

Measured against a golden dataset spanning all corpus categories, including deliberate abstention cases:

| Metric | Target | Result |
|---|---|---|
| Retrieval recall | ≥ 85% | 87.5% |
| Groundedness (LLM-as-judge) | ≥ 90% | 100% |
| Correct abstention rate | measured + reported | 100% |

## Tech stack

FastAPI · Claude API (Haiku for development, Sonnet for quality-critical calls) · Chroma (RAG) · a custom MCP server with 6 tools · a live project-tracking API integration · Langfuse (tracing) · pytest

## Status

Active development portfolio project. Core RAG, MCP server/client, tool-use loop, groundedness-critique subagent, and eval harness are built and verified against real data. Production-hardening items (real ERP integration, auth/RBAC, real-time streaming, remote MCP transports) are documented and deliberately scoped as next steps, not yet built.
