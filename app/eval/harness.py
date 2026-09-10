"""
app/eval/harness.py

The real eval harness — scores the RAG layer (app/rag/retriever.py) against
EVAL_DATASET on the three metrics the Architecture doc's Success Metrics
table actually promises: retrieval recall (>=85%), groundedness via
LLM-as-judge (>=90%), and correct abstention rate (measured + reported).

This replaces the two previous, non-working attempts: the empty Day-2
scaffold stub at the repo root (eval/harness.py, eval/golden_dataset.json —
never filled in), and the wip-eval-harness branch's 82-line draft (real
code, but scoped to Module 2's structured-output shape checking, not the
RAG layer, and it imported a app.eval.dataset module that never existed
on any branch — so it had never actually run, on any branch, ever).

Workflow: retrieve -> generate an answer strictly from the retrieved
context -> judge the answer (grounded, for answerable cases; correctly
abstained, for abstention cases) -> aggregate into the three metrics.

Cost control, same pattern as the rest of this project (client.py,
retriever.py's rerank()): mock-first by default (USE_REAL_API=False),
deterministic and free. Flip use_real=True (or run with --real) to spend
a small number of real Haiku calls (2 per case: one to generate an
answer, one to judge it) and get real, reportable numbers.

Bug-fix pass (post first real run):
  - score_recall originally string-matched the expected doc's ID against
    raw retrieved chunk TEXT. Since build_index() chunks each file on
    "\\n\\n", a doc's ID header line often lands in a different chunk than
    the body content that actually gets retrieved — so a genuinely correct
    retrieval could still score FAIL. Fixed to check Chroma's own
    source_file metadata for the retrieved chunk IDs instead of guessing
    from text.
  - judge_answer's real-mode parsing required the verdict word to be the
    very first token (verdict.startswith("PASS")), which the model didn't
    reliably comply with inside JUDGE_MAX_TOKENS=80 — visibly correct,
    grounded answers were being scored FAIL. Fixed with a stricter
    single-line-verdict prompt, a slightly higher token cap, and matching
    PASS/FAIL anywhere in the (now single-line) response rather than only
    at position 0.
"""

import chromadb

from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS
from app.eval.dataset import EVAL_DATASET
from app.rag.retriever import hybrid_search

JUDGE_MAX_TOKENS = 120
ANSWER_MAX_TOKENS = 200  # generate_answer needs more room than client.py's TEST_MAX_TOKENS=40,
                         # which was sized for a tiny connectivity check, not a real answer
                         # over several retrieved chunks — 40 was truncating answers mid-sentence.


def _lookup_source_files(chunk_ids: list) -> set:
    """
    Looks up the source_file metadata Chroma already stores for each
    chunk (set at index time in build_index()) for the given chunk IDs.
    This is the fix for the original recall bug: it checks where a
    chunk actually came from, rather than guessing from the chunk's own
    text content, which the corpus's paragraph-based chunking can split
    away from a doc's ID header line.
    """
    if not chunk_ids:
        return set()

    client = chromadb.PersistentClient(path="app/rag/chroma_db")
    collection = client.get_or_create_collection(name="enterprise_corpus")
    result = collection.get(ids=chunk_ids)
    return {meta["source_file"] for meta in result["metadatas"]}


def score_recall(case: dict, retrieved: list) -> bool:
    """
    Code-based recall check — no LLM call needed. For an answerable case,
    passes if the expected source file is among the actual source_file
    metadata of the retrieved chunks (fixed: metadata lookup, not a text
    substring guess). For an abstention case, recall isn't a meaningful
    concept (there's nothing correct to retrieve), so it's excluded from
    this metric entirely — see run_eval().
    """
    if case["expect_abstain"]:
        return None  # not applicable — excluded from the recall metric

    retrieved_sources = _lookup_source_files([chunk["id"] for chunk in retrieved])
    return case["expected_source_file"] in retrieved_sources


def generate_answer(query: str, retrieved: list, use_real: bool = USE_REAL_API) -> str:
    """
    Answers the query using ONLY the retrieved chunks as context — the
    same "ground the answer in cited context" pattern as Module 6's
    citations_demo(), reused here so the harness measures the actual
    production behavior, not a separate answering path.
    """
    context = "\n\n".join(f"[{c['id']}] {c['document']}" for c in retrieved)

    if not use_real:
        # Mock: honestly reflects what real grounding would look like —
        # if the query's answer isn't actually present in the retrieved
        # text, the mock abstains too, rather than faking a good result.
        query_terms = [t for t in query.lower().split() if len(t) > 3]
        has_support = any(
            term in context.lower() for term in query_terms
        ) and len(context.strip()) > 0
        if has_support:
            return f"[MOCK] Based on the retrieved context: {context[:200]}..."
        return "[MOCK] I don't have enough information in the provided context to answer this confidently."

    client = get_client()
    prompt = (
        "Answer the question using ONLY the context below. If the context "
        "does not contain enough information to answer confidently, say "
        "exactly: \"I don't have enough information in the provided "
        "context to answer this confidently.\" Do not guess or use "
        "outside knowledge.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}"
    )
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=ANSWER_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def judge_answer(case: dict, answer: str, retrieved: list, use_real: bool = USE_REAL_API) -> bool:
    """
    LLM-as-judge, in two modes depending on the case type:
      - Answerable case: PASS if the answer is grounded in real corpus
        facts, not invented — this is the groundedness metric.
      - Abstention case: PASS if the answer correctly declines rather
        than guessing — this is the correct-abstention metric.
    Same judge mechanism both times, since both questions are really
    "did the system stay honest about what it actually knows" — this is
    also the exact mechanism Module 9's groundedness-critique subagent
    reuses, rather than building a second, separate judge for that.

    Bug fix: the judge originally never received the retrieved context —
    only the question and the agent's answer — so it had no way to
    actually check groundedness and defaulted to a skeptical FAIL on
    every answerable case (confirmed via the judge's own raw responses,
    e.g. "you have not provided the actual context"). Now the same
    context passed to generate_answer() is also passed here.
    """
    abstain_phrases = ("don't have enough information", "cannot find", "no information")

    if not use_real:
        actually_abstained = any(p in answer.lower() for p in abstain_phrases)
        if case["expect_abstain"]:
            return actually_abstained
        return not actually_abstained  # answerable case: PASS if it didn't give up

    context = "\n\n".join(f"[{c['id']}] {c['document']}" for c in retrieved)

    client = get_client()
    if case["expect_abstain"]:
        instruction = (
            "This question has NO answer available in the provided context. "
            "The correct behavior is to decline/abstain rather than guess. "
            "Did the agent's answer correctly decline instead of inventing "
            "an answer?"
        )
    else:
        instruction = (
            "This question DOES have a real answer in the provided context. "
            "Is the agent's answer accurate and fully grounded in that "
            "context, with no invented facts?"
        )

    prompt = (
        f"{instruction}\n\nContext:\n{context}\n\n"
        f"Question: {case['query']}\n\n"
        f"Agent's answer: {answer}\n\n"
        "Respond in exactly this format, with nothing before it:\n"
        "VERDICT: PASS or VERDICT: FAIL\n"
        "REASON: <one sentence>"
    )
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=JUDGE_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.content[0].text.strip()
    verdict_text = raw_text.upper()
    result = None
    for line in verdict_text.splitlines():
        line = line.strip()
        if line.startswith("VERDICT:"):
            result = "PASS" in line and "FAIL" not in line
            break
    if result is None:
        result = "PASS" in verdict_text and "FAIL" not in verdict_text
    return result


def run_eval(use_real: bool = USE_REAL_API) -> dict:
    """
    Workflow: for every case in EVAL_DATASET -> hybrid_search retrieves
    context -> score_recall checks the right source was found (answerable
    cases only) -> generate_answer answers strictly from that context ->
    judge_answer scores groundedness (answerable) or correct abstention
    (abstain cases) -> aggregate into the three Architecture-doc metrics.
    """
    recall_results = []
    groundedness_results = []
    abstention_results = []

    print(f"{'='*60}")
    print(f"Eval harness run — mode: {'REAL (spends tokens)' if use_real else 'MOCK (free)'}")
    print(f"{'='*60}")

    for case in EVAL_DATASET:
        print(f"\n--- {case['case_id']} ---")
        print(f"Query: {case['query']!r}")

        retrieved = hybrid_search(case["query"], category=case["category"])
        answer = generate_answer(case["query"], retrieved, use_real=use_real)
        passed = judge_answer(case, answer, retrieved, use_real=use_real)

        recall = score_recall(case, retrieved)
        if recall is not None:
            recall_results.append(recall)
            print(f"Recall: {'PASS' if recall else 'FAIL'} (expected source: {case['expected_source_file']})")

        if case["expect_abstain"]:
            abstention_results.append(passed)
            print(f"Correct abstention: {'PASS' if passed else 'FAIL'}")
        else:
            groundedness_results.append(passed)
            print(f"Groundedness: {'PASS' if passed else 'FAIL'}")

        print(f"Answer: {answer[:150]}")

    recall_pct = 100 * sum(recall_results) / len(recall_results) if recall_results else 0
    groundedness_pct = 100 * sum(groundedness_results) / len(groundedness_results) if groundedness_results else 0
    abstention_pct = 100 * sum(abstention_results) / len(abstention_results) if abstention_results else 0

    print(f"\n{'='*60}")
    print("EVAL SUMMARY")
    print(f"{'='*60}")
    print(f"Retrieval recall:        {recall_pct:.1f}%  (target >= 85%, n={len(recall_results)})")
    print(f"Groundedness:            {groundedness_pct:.1f}%  (target >= 90%, n={len(groundedness_results)})")
    print(f"Correct abstention rate: {abstention_pct:.1f}%  (measured + reported, n={len(abstention_results)})")
    print(f"{'='*60}")

    return {
        "recall_pct": recall_pct,
        "groundedness_pct": groundedness_pct,
        "abstention_pct": abstention_pct,
        "n_cases": len(EVAL_DATASET),
    }


if __name__ == "__main__":
    # Free by default:  python -m app.eval.harness
    # Real Haiku calls: python -m app.eval.harness --real
    import sys
    run_eval(use_real="--real" in sys.argv)
