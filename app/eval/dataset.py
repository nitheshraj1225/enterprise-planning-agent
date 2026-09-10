"""
app/eval/dataset.py

The real eval harness's golden dataset — closes the gap flagged repeatedly
in CONTEXT.md and Interview-Prep.md as the project's single highest-priority
open item ("I don't have a measured retrieval failure to point to yet...").

Each case targets the RAG layer (app/rag/retriever.py's hybrid_search),
not Module 2's structured-output demo — the eval harness scores what the
Architecture doc's Success Metrics table actually promises: retrieval
recall, groundedness, and correct abstention, against the real 500-doc
synthetic corpus, not a mock.

Workflow: each case is either ANSWERABLE (a real fact lives in the corpus,
so the harness checks the right source chunk was retrieved AND that a
generated answer stays grounded in it) or an ABSTENTION case (nothing in
the corpus answers it, so the harness checks the system correctly says so
instead of inventing a plausible-sounding number).

Deliberately small (12 cases) and hand-verified against real corpus files
rather than auto-generated — a golden dataset that wasn't independently
checked against the source data isn't actually a check on anything.
"""

EVAL_DATASET = [
    # --- Answerable: Epics ---
    {
        "case_id": "EPIC-lookup-1",
        "query": "What is the story point estimate for the notification service migration Epic for Payments Platform?",
        "category": "epics",
        "expect_abstain": False,
        "expected_source_file": "EPIC-0001.md",
        "note": "Direct fact lookup — EPIC-0001, 1 story point, In Progress.",
    },
    {
        "case_id": "EPIC-lookup-2",
        "query": "What is EPIC-0002 about and what team owns it?",
        "category": "epics",
        "expect_abstain": False,
        "expected_source_file": "EPIC-0002.md",
        "note": "Direct fact lookup by explicit Epic ID.",
    },

    # --- Answerable: Sizing policies ---
    {
        "case_id": "SIZE-lookup-1",
        "query": "What does an 8-point Epic typically represent under our sizing policy?",
        "category": "sizing_policies",
        "expect_abstain": False,
        "expected_source_file": "SIZE-0001.md",
        "note": "SIZE-0001: multi-team dependency or external approval requirement.",
    },
    {
        "case_id": "SIZE-lookup-2",
        "query": "Which Epic is used as the representative example for an 8-point sizing policy?",
        "category": "sizing_policies",
        "expect_abstain": False,
        "expected_source_file": "SIZE-0001.md",
        "note": "Tests whether retrieval surfaces the cross-referenced EPIC-0295 pointer inside SIZE-0001.",
    },

    # --- Answerable: Finance policies ---
    {
        "case_id": "FIN-lookup-1",
        "query": "What approval is required for a Customer-Facing project with spend above $25,000?",
        "category": "finance_policies",
        "expect_abstain": False,
        "expected_source_file": "FIN-0001.md",
        "note": "FIN-0001: Compliance Officer sign-off required.",
    },

    # --- Answerable: ERP records ---
    {
        "case_id": "ERP-lookup-1",
        "query": "What is the allocated budget and utilization percentage for project PRJ-0001?",
        "category": "erp_records",
        "expect_abstain": False,
        "expected_source_file": "ERP-0001.md",
        "note": "ERP-0001: $761,000 budget, 98% utilization, CC-400 Product.",
    },

    # --- Answerable: Velocity reports ---
    {
        "case_id": "VEL-lookup-1",
        "query": "How many story points did the Core Banking team complete in Sprint 15?",
        "category": "velocity_reports",
        "expect_abstain": False,
        "expected_source_file": "VEL-0001.md",
        "note": "VEL-0001: 22 of 26 committed points, Sprint 15, Q2 FY26.",
    },

    # --- Answerable: cross-category (no category filter — tests hybrid_search's exact-ID recall) ---
    {
        "case_id": "CROSS-lookup-1",
        "query": "EPIC-0001 status and story points",
        "category": None,
        "expect_abstain": False,
        "expected_source_file": "EPIC-0001.md",
        "note": "Deliberately no category filter and a short, ID-heavy query — the exact scenario hybrid_search's BM25 half exists for (pure semantic search under-ranks exact IDs).",
    },

    # --- Abstention: fabricated IDs that don't exist in the corpus ---
    {
        "case_id": "ABSTAIN-fake-epic",
        "query": "What is the story point estimate for EPIC-9999?",
        "category": "epics",
        "expect_abstain": True,
        "expected_source_file": None,
        "note": "EPIC-9999 does not exist (corpus only has EPIC-0001 through EPIC-0300) — system must abstain, not invent a plausible number.",
    },
    {
        "case_id": "ABSTAIN-fake-sizing",
        "query": "What is the sizing criteria for a 34-point Epic?",
        "category": "sizing_policies",
        "expect_abstain": True,
        "expected_source_file": None,
        "note": "The Fibonacci sizing scale used in this project tops out at 21 (see EPIC_SIZING_TOOL) — 34-point policy docs don't exist in the corpus.",
    },

    # --- Abstention: real-sounding question, genuinely out of corpus scope ---
    {
        "case_id": "ABSTAIN-out-of-scope-1",
        "query": "What is our company's policy on cryptocurrency payments to vendors?",
        "category": None,
        "expect_abstain": True,
        "expected_source_file": None,
        "note": "Plausible-sounding enterprise question with zero coverage anywhere in the synthetic corpus (finance_policies only covers approval-threshold sign-off rules) — the highest-value abstention test, since it's the kind of question a real user might actually ask.",
    },
    {
        "case_id": "ABSTAIN-out-of-scope-2",
        "query": "Which vendor manages our disaster recovery data center failover?",
        "category": None,
        "expect_abstain": True,
        "expected_source_file": None,
        "note": "Another realistic-sounding but genuinely uncovered question — infra/vendor management isn't part of this corpus's 5 categories.",
    },
]
