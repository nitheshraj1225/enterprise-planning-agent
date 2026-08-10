# Enterprise Planning Intelligence Agent — Project Context
**Owner:** Nithesh Bongoni  
**Started:** Day 1 (Aug 2026)  
**GitHub:** github.com/nitheshraj1225/enterprise-planning-agent  
**Goal:** Land an Enterprise AI Architect / Principal AI Solution Architect role (H1B sponsor)

---

## Why This Project Exists

Nithesh has 15+ years as a Senior Implementation Consultant in enterprise PPM
(Targetprocess, Clarity), with deep experience in Jira integrations, API
development, enterprise system migrations, and Agile transformations at clients
including AMEX, UBS, Southwest Airlines, Credit Suisse, and Scotia.

The goal is to transition into AI Engineer / Enterprise AI Architect roles. This
project was chosen because:
- It covers every 2026 AI Engineer hiring keyword: RAG, MCP, agents, evals,
  guardrails, deployment, tracing
- The problem domain (enterprise planning, Epic sizing, cross-system
  orchestration) is directly credible given 15 years of lived experience
- It maps perfectly to the target JDs (Gusto Enterprise Applications AI
  Architect, Principal AI Solution Architect — Supply Chain)
- MCP server + eval harness are the two rarest, highest-signal differentiators
  on an AI Architect resume in 2026

---

## Project Definition

**Name:** Enterprise Planning Intelligence Agent

**One-line description:** An agentic AI system built with Claude API + Claude
Code that connects enterprise applications (real Jira, synthetic ERP, Finance),
answers cross-system planning questions, generates explainable Epic sizing
estimates during annual planning, and executes actions with human approval —
fully audited and evaluated.

**User:** An enterprise delivery lead or IT architect working across
disconnected systems (Jira, ERP, Finance) who needs grounded, cited,
cross-system answers without manually stitching data together.

**The one job it does:** Answer "what's the status / what's blocking / what
should we do next / how should we size this Epic" — grounded in real data,
cited to source, human-confirmed before any action fires.

**Origin of the core use case:** Nithesh identified this pain firsthand at
client engagements — specifically an AI-enabled Epic sizing engine for annual
planning where delivery teams wasted time on manual estimation mechanics during
compressed planning cycles instead of focusing on delivery.

---

## Business Pain Statement (Nithesh's words)

*"During compressed annual planning cycles, delivery teams spend
disproportionate time on manual estimation mechanics rather than delivery —
resulting in inconsistent sizing inputs and delayed planning outputs across
the enterprise."*

---

## Why Claude (Architectural Justification)

Claude's large context window handles multi-system data retrieval in a single
call — critical when aggregating across Jira, ERP, and Finance in one agent
turn. Its precise instruction-following ensures structured audit log outputs
are never skipped, which is non-negotiable in a SOX-sensitive enterprise
environment. Anthropic's Constitutional AI approach provides a defensible
safety and explainability story for enterprise governance stakeholders.

---

## Success Metrics

| Metric | Target | Why It's Prioritized This Way |
|---|---|---|
| Groundedness | ≥ 90% | Highest priority — a hallucinated dependency or sizing estimate causes real planning damage |
| Retrieval recall | ≥ 85% | Important but a missed retrieval fails safe (abstain) vs inventing (dangerous) |
| Correct abstention rate | Measured + reported | When evidence is missing, system must say so — never invent. The metric most people forget. |

---

## Architecture

```
User Query
    │
    ▼
Streamlit UI (minimal demo interface)
    │
    ▼
FastAPI Agent Endpoint
    │
    ├── RAG Layer
    │     └── Chroma vector store
    │           └── Synthetic docs: sizing policies, ERP records,
    │                finance data, historical Epic data
    │
    ├── MCP Server (6 tools)
    │     ├── jira_epic_lookup        [REAL Jira API — read]
    │     ├── jira_velocity_fetch     [REAL Jira API — read]
    │     ├── erp_record_fetch        [Mock — read]
    │     ├── finance_policy_retrieve [Mock — read]
    │     ├── check_recent_updates    [Polling simulation]
    │     └── create_action_request   [Write — human confirm required]
    │
    ├── Guardrails
    │     └── Prompt injection defense + input validation
    │
    ├── SOX-Conscious Audit Log
    │     └── Append-only: every agent step, tool call,
    │           human decision, timestamp, reasoning
    │
    └── Eval Harness
          ├── Retrieval recall (≥ 85%)
          ├── Groundedness LLM-as-judge (≥ 90%)
          └── Correct abstention rate
```

---

## Tech Stack

| Layer | Technology | Why This Choice |
|---|---|---|
| LLM reasoning | Claude API (claude-sonnet-4-6) | Large context, precise instruction-following, Constitutional AI safety story |
| Agentic coding | Claude Code | Covers CCAR-F exam domain, real workflow signal |
| Agent framework | Native Claude tool-use loop | Full control, fully auditable — no LangChain abstraction hiding tool calls |
| RAG / vector store | Chroma (PoC) → pgvector (prod) | Zero infrastructure for PoC; pgvector documented as production path |
| API layer | FastAPI | Async support, auto Swagger docs, native Pydantic validation |
| UI | Streamlit (minimal) | Demo-able in half a day, not a distraction |
| Real integration | Jira Cloud REST API | Free tier, real API signal on resume |
| Mock integrations | Synthetic ERP + Finance | Same code pattern, no NetSuite free tier available |
| Containerization | Docker | Production-readiness signal |
| Deployment | Hugging Face Spaces / Render | Free tier, public URL for demo |
| Tracing | Custom logger → OpenTelemetry-ready | Observability signal for enterprise hiring managers |
| Eval | Custom harness + LLM-as-judge (Claude) | Shows engineering rigor, not just "it works" |

---

## Scope

### In Scope
- RAG over synthetic enterprise corpus (30-40 docs)
- Real Jira API integration (free cloud tier)
- Custom MCP server with 6 tools
- Multi-step agentic tool-use loop
- Prompt-injection guardrails + input validation
- SOX-conscious append-only audit log
- Eval harness: recall + groundedness + abstention
- Minimal Streamlit UI
- Dockerized + deployed to public URL
- Full request tracing on every LLM and tool call
- CLAUDE.md configuration for Claude Code

### Out of Scope (Deliberately — Documented Production Gaps)
- **Auth/multi-user:** Production would add OAuth2 + RBAC
- **Fine-tuning:** Wrong tool — RAG + prompt engineering is correct layer
- **Real-time streaming:** Polling simulation covers the pattern
- **Real ERP/Finance APIs:** Mocked realistically, same code pattern

---

## Tool Selection Rationale (Interview Answers)

**FastAPI vs Flask vs Django:**
FastAPI because we needed async support for concurrent tool calls, automatic
API docs for the demo, and native Pydantic validation for structured outputs.
Flask is too bare; Django is overkill for an API-only service.

**Chroma vs pgvector:**
Chroma for the PoC — runs in-process, zero infrastructure setup. pgvector is
the production replacement (documented in README) because it integrates with
existing enterprise Postgres infrastructure.

**Claude API vs LangChain:**
Native Claude API because in a SOX-conscious system every agent step must be
fully auditable. LangChain abstracts the tool-calling loop in ways that make
tracing harder — the opposite of what enterprise compliance needs.

**Python 3.11.9 vs 3.14:**
3.14 was too new — pydantic-core and Pillow hadn't built wheels for it yet
(confirmed by a failed install). In production engineering, you run what's
stable and supported, not the bleeding edge. 3.11.9 is the enterprise sweet
spot.

---

## Interview Narrative (2-Sentence Answer)

*"I built an enterprise planning intelligence agent that generates explainable
Epic sizing estimates during annual planning — grounded in real Jira data and
synthetic ERP/finance policy docs via RAG, with a custom MCP server exposing
six enterprise tools, SOX-conscious audit logging, and an eval harness
measuring groundedness, recall, and abstention rate. I deliberately kept the
risk-scoring rule-based and human-confirmed rather than fully automated,
because in an enterprise governance context an unexplainable automated decision
is worse than a slower human-approved one."*

---

## Target Roles

- Enterprise AI Architect
- Enterprise Applications AI Architect (e.g. Gusto JD)
- Principal AI Solution Architect (e.g. Supply Chain JD)
- AI Engineer (enterprise/consulting-focused)

**H1B sponsors to target:** Google, Microsoft, Amazon, Accenture, Deloitte,
Cognizant, SAP, Oracle, Gusto, and mid-size AI-native consultancies.

---

## Portfolio Priority Order

| Priority | Project | Status |
|---|---|---|
| #1 | Enterprise Planning Intelligence Agent (this project) | 🔨 In progress |
| #2 | Data Analytics → Executive PowerPoint (Claude Code) | ⏳ After Day 28 |
| #3 | Epic Sizing Engine (module inside this project) | ⏳ Future |
| #4 | UAT Support Tool | ⏳ Future |
| #5 | PRD Generation | ⏳ Low priority |

---

## Certification Plan

| Exam | Code | Cost | Target Date |
|---|---|---|---|
| Claude Certified Architect Foundations | CCAR-F | $125 | Day 28 |
| Claude Certified Architect Professional | CCAR-P | $175 | 4-6 weeks after Day 28 |

**Retake policy:** 14-day wait after fail 1, 30-day after fail 2, 90-day
after fail 3. Max 4 attempts per 12 months. Each attempt costs $125/$175.
**Note:** Requires Anthropic Partner Network membership to register.

---

## Daily Certification + Python Schedule

| Day | Certification | Python |
|---|---|---|
| 1 | Claude 101 | None |
| 2 | Claude Platform 101 | None |
| 3 | Building with Claude API (Part 1) | Variables, strings, lists, dicts |
| 4 | Building with Claude API (Part 2) | Functions, loops, file I/O |
| 5 | Building with Claude API (Part 3) | Classes, modules, imports |
| 6 | Building with Claude API (Part 4) | Error handling, try/except |
| 7 | Building with Claude API (finish) | JSON + environment variables |
| 8 | MCP Intro (Part 1) | HTTP requests with httpx |
| 9 | MCP Intro (Part 2) | REST APIs + reading responses |
| 10 | MCP Intro (finish) | Data structures + list comprehensions |
| 11 | MCP Advanced (Part 1) | Writing and reading files |
| 12 | MCP Advanced (Part 2) | Decorators + async basics |
| 13 | MCP Advanced (Part 3) | Async/await pattern |
| 14 | MCP Advanced (finish) | pytest basics |
| 15 | Claude Code 101 | Logging module |
| 16 | Claude Code in Action (Part 1) | Append-only file patterns |
| 17 | Claude Code in Action (Part 2) | Regex + string validation |
| 18 | Claude Code in Action (Part 3) | JSON schema + data validation |
| 19 | Claude Code in Action (finish) | Writing test harnesses |
| 20 | Intro to Subagents | Pandas basics |
| 21 | Intro to Agent Skills | Matplotlib (basic eval charts) |
| 22 | Course review | Streamlit basics |
| 23 | Practice questions | Dockerfile + containerization |
| 24 | Practice questions | None |
| 25 | Mock exam | None |
| 26 | Register for CCAR-F | None |
| 27 | Final review | None |
| 28 | 🎓 TAKE CCAR-F EXAM | None |

---

## How We Work (Coaching Rules)

1. **Explain before execute** — every command is explained before running
2. **You ask "why" before running** — no blind copy-paste
3. **End of every day** — 3-5 senior interview questions, honest feedback
4. **Explain it back** — at key moments you explain what was built to a stakeholder
5. **Answer structure** — every interview answer: What it is → Why it exists → What breaks without it

---

## Day Progress Log

| Day | Project | Cert | Notes |
|---|---|---|---|
| 1 | ✅ Project spec finalized | ❓ Claude 101 | Full strategy session — target roles locked |
| 2 | ✅ Repo + FastAPI + CLAUDE.md | ❓ Claude Platform 101 | Python 3.14→3.11.9 fix via pyenv + Homebrew |
| 3 | ⬅️ Synthetic corpus | Building with Claude API | Resume here |

---

## Environment Setup Notes

- **Mac + pyenv** — Python 3.14 pre-installed but incompatible; fixed with pyenv 3.11.9
- **Homebrew required** for xz (lzma) fix before pyenv install worked cleanly
- **venv activation:** `source venv/bin/activate` (run every new terminal session)
- **API key:** stored in `.env`, excluded from Git via `.gitignore`
- **GitHub auth:** Personal Access Token (PAT) required — not password

---

## Python Resources

| Resource | Use For |
|---|---|
| docs.python.org/3/tutorial | Fundamentals |
| realpython.com | Practical, project-based |
| freeCodeCamp Python (YouTube) | Full beginner course |
| docs.streamlit.io | Day 22 UI |
| docs.pytest.org | Day 14 testing |

---

*Last updated: Day 2 complete. Next: Day 3 — Synthetic corpus build.*
