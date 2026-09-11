"""
app/agent/subagent_critique.py

Module 9 / Introduction to Subagents — chain-of-verification pattern.
A second agent critiques the first agent's Epic-sizing draft for
groundedness before it's returned, reusing the same judge mechanism
already proven in app/eval/harness.py's judge_answer().

Workflow: epic_id -> retrieve real evidence -> generate a sizing draft
from that evidence -> critique the draft's rationale against the same
evidence -> return the draft with a verified/reason flag attached,
never silently retried or discarded on a failed verification.
"""

from app.agent.client import get_client, USE_REAL_API, TEST_MODEL
from app.rag.retriever import hybrid_search
from app.agent.structured_output_demo import get_structured_epic_estimate_tool_forced

CRITIQUE_MAX_TOKENS = 120


def critique_epic_estimate(draft: dict, retrieved: list, use_real: bool = USE_REAL_API) -> dict:
    """
    Workflow: draft rationale + retrieved evidence -> independent verdict
    -> {"verified": bool, "reason": str}
    """
    context = "\n\n".join(c["document"] for c in retrieved)

    if not use_real:
        rationale_terms = [t for t in draft["rationale"].lower().split() if len(t) > 3]
        has_support = any(term in context.lower() for term in rationale_terms) and len(context.strip()) > 0
        if has_support:
            return {"verified": True, "reason": "[MOCK] rationale terms found in retrieved evidence"}
        return {"verified": False, "reason": "[MOCK] rationale terms not found in retrieved evidence"}

    client = get_client()
    instruction = (
        "Check whether the rationale below is actually supported by the "
        "evidence in the Context. Flag it as not verified if it makes any "
        "claim the context doesn't actually back up."
    )
    prompt = (
        f"{instruction}\n\nContext:\n{context}\n\n"
        f"Draft rationale: {draft['rationale']}\n\n"
        "Respond in exactly this format, with nothing before it:\n"
        "VERDICT: PASS or VERDICT: FAIL\n"
        "REASON: <one sentence>"
    )
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=CRITIQUE_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.content[0].text.strip()
    verdict_text = raw_text.upper()

    verified = None
    reason = "no reason parsed"
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("VERDICT:"):
            verified = "PASS" in stripped.upper() and "FAIL" not in stripped.upper()
        if stripped.upper().startswith("REASON:"):
            reason = stripped.split(":", 1)[1].strip()

    if verified is None:
        verified = "PASS" in verdict_text and "FAIL" not in verdict_text

    return {"verified": verified, "reason": reason}


def get_verified_epic_estimate(epic_id: str, use_real: bool = USE_REAL_API) -> dict:
    """
    Workflow: hybrid_search -> get_structured_epic_estimate_tool_forced
    -> critique_epic_estimate -> merged result (draft + verified + reason)

    This is the end-to-end chain-of-verification flow: the sizing agent
    produces a draft, the critique subagent checks it against the same
    real evidence, and the caller always sees both the draft and whether
    it was actually verified - a failed verification is surfaced, never
    hidden or silently retried (matches this project's existing
    human-in-the-loop pattern, e.g. create_action_request).
    """
    retrieved = hybrid_search(epic_id, category="epics")
    context = "\n\n".join(c["document"] for c in retrieved)
    draft = get_structured_epic_estimate_tool_forced(context, use_real=use_real)

    verification = critique_epic_estimate(draft, retrieved, use_real=use_real)

    return {
        **draft,
        "verified": verification["verified"],
        "verification_reason": verification["reason"],
    }


if __name__ == "__main__":
    # Free by default:  python -m app.agent.subagent_critique
    # Real Haiku calls: python -m app.agent.subagent_critique --real
    import sys
    result = get_verified_epic_estimate("EPIC-0001", use_real="--real" in sys.argv)
    print(result)