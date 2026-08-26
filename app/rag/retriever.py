"""
app/rag/retriever.py

Module 5 (RAG and Agentic Search) — chunking + embedding + storage
(build_index), semantic similarity search (retrieve), keyword search
(bm25_search), combined hybrid search (hybrid_search), and an
LLM-based reranking pass (rerank) over the top hybrid candidates.
"""

import os
import chromadb
from rank_bm25 import BM25Okapi

from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS

CORPUS_DIR = "app/data/synthetic_corpus"
CATEGORIES = ["epics", "erp_records", "velocity_reports", "finance_policies", "sizing_policies"]


def build_index():
    client = chromadb.PersistentClient(path="app/rag/chroma_db")
    collection = client.get_or_create_collection(name="enterprise_corpus")

    chunk_id = 0
    for category in CATEGORIES:
        category_path = os.path.join(CORPUS_DIR, category)
        for filename in os.listdir(category_path):
            filepath = os.path.join(category_path, filename)
            with open(filepath, "r") as f:
                text = f.read()

            chunks = text.split("\n\n")

            for chunk_text in chunks:
                collection.add(
                    documents=[chunk_text],
                    metadatas=[{"category": category, "source_file": filename}],
                    ids=[f"chunk_{chunk_id}"],
                )
                chunk_id += 1

    print(f"Indexed {chunk_id} chunks into Chroma.")


def retrieve(query_text: str, category: str = None, n_results: int = 3):
    client = chromadb.PersistentClient(path="app/rag/chroma_db")
    collection = client.get_or_create_collection(name="enterprise_corpus")

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where={"category": category} if category else None,
    )

    return results


def bm25_search(query_text: str, n_results: int = 3):
    client = chromadb.PersistentClient(path="app/rag/chroma_db")
    collection = client.get_or_create_collection(name="enterprise_corpus")

    all_chunks = collection.get()
    tokenized_corpus = [doc.split() for doc in all_chunks["documents"]]
    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = query_text.split()
    scores = bm25.get_scores(tokenized_query)

    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n_results]

    return [
        {"id": all_chunks["ids"][i], "document": all_chunks["documents"][i], "score": scores[i]}
        for i in ranked_indices
    ]


def hybrid_search(query_text: str, category: str = None, n_results: int = 3, k: int = 60):
    """
    Combines semantic (retrieve) and keyword (bm25_search) rankings using
    Reciprocal Rank Fusion: each chunk's fused score is the sum of
    1 / (k + rank) across every list it appears in. This sidesteps the
    problem that cosine distance and BM25 scores live on different,
    non-comparable scales — RRF only cares about *rank position*, not
    the raw score value, so it merges cleanly regardless of scale.
    """
    semantic_results = retrieve(query_text, category=category, n_results=n_results * 3)
    keyword_results = bm25_search(query_text, n_results=n_results * 3)

    fused_scores = {}
    chunk_lookup = {}

    for rank, chunk_id in enumerate(semantic_results["ids"][0]):
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (k + rank)
        chunk_lookup[chunk_id] = semantic_results["documents"][0][rank]

    for rank, item in enumerate(keyword_results):
        chunk_id = item["id"]
        fused_scores[chunk_id] = fused_scores.get(chunk_id, 0) + 1 / (k + rank)
        chunk_lookup[chunk_id] = item["document"]

    ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)[:n_results]

    return [
        {"id": chunk_id, "document": chunk_lookup[chunk_id], "fused_score": fused_scores[chunk_id]}
        for chunk_id in ranked_ids
    ]


def rerank(query_text: str, candidates: list, use_real: bool = USE_REAL_API):
    """
    Re-scores hybrid_search's top candidates with Claude acting as a
    relevance judge — a slower, more accurate pass over a small shortlist,
    versus the cheap, corpus-wide scoring hybrid_search already did.
    """
    if not use_real:
        return candidates  # mock: candidates already ranked well enough to demo

    client = get_client()
    scored = []
    for candidate in candidates:
        response = client.messages.create(
            model=TEST_MODEL,
            max_tokens=TEST_MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": (
                    f"Query: {query_text}\n\nPassage: {candidate['document']}\n\n"
                    "Rate this passage's relevance to the query from 1-10. "
                    "Respond with ONLY the number."
                ),
            }],
        )
        try:
            relevance = float(response.content[0].text.strip())
        except ValueError:
            relevance = 0
        scored.append({**candidate, "relevance": relevance})

    return sorted(scored, key=lambda c: c["relevance"], reverse=True)


if __name__ == "__main__":
    query = "What is the estimate for a billing engine migration?"

    hybrid_results = hybrid_search(query, category="epics")
    print("Hybrid search results:")
    print(hybrid_results)

    reranked_results = rerank(query, hybrid_results)
    print("\nReranked results:")
    print(reranked_results)