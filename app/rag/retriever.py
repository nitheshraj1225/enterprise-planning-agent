"""
app/rag/retriever.py

Module 5 (RAG and Agentic Search) — chunking + embedding + storing the
synthetic corpus into Chroma (build_index), and semantic similarity search
over it (retrieve).
"""

import os
import chromadb

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


if __name__ == "__main__":
    results = retrieve("What is the estimate for a billing engine migration?", category="epics")
    print(results)