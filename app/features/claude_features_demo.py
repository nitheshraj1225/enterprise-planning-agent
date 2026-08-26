"""
app/features/claude_features_demo.py

Module 6 (Features of Claude) — five small demos:
  extended_thinking_demo, prompt_caching_demo, citations_demo,
  vision_demo, pdf_demo. Each ties back to a real piece of this project
  rather than being a standalone tech demo. Mock-first, same pattern as
  the rest of the project.
"""

import base64  # converts binary file data (images, PDFs) into text the API can accept

# Reused from Module 1's client.py: get_client() builds the Anthropic client,
# USE_REAL_API is the global mock/real toggle, TEST_MODEL/TEST_MAX_TOKENS are
# the shared model + token-limit settings used everywhere in this project.
from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS

# Reused from Module 3: a real, already-written Epic description to test against,
# instead of writing a new sample Epic just for this file.
from app.prompts.technique_demos import SAMPLE_EPIC

# Reused from Module 5: the RAG retrieval function — citations_demo grounds
# its answer in real retrieved chunks, not a hardcoded string.
from app.rag.retriever import retrieve

# The folder generate_sample_assets.py wrote its files into.
ASSETS_DIR = "app/data/synthetic_assets"


def extended_thinking_demo(epic_description: str = SAMPLE_EPIC, use_real: bool = USE_REAL_API):
    if not use_real:
        # Mock mode: return a shape that matches what the real branch below
        # returns, so calling code doesn't need to know which mode it's in.
        return {
            "thinking": "[MOCK] Comparable Epics in this category average 8-13 points; "
                        "this one has a cross-team dependency, pushing it toward the higher end.",
            "answer": "[MOCK — no API call made] Estimated size: 13 story points.",
        }

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        # This is the actual extended-thinking feature: Claude reasons in a
        # separate "thinking" block before its final answer. budget_tokens
        # caps how much reasoning it's allowed to spend before answering.
        thinking={"type": "enabled", "budget_tokens": 1024},
        messages=[{"role": "user", "content": f"Estimate the size of this Epic:\n\n{epic_description}"}],
    )

    # response.content is a list of blocks — with thinking enabled, one
    # block has type "thinking" (the reasoning) and another has type "text"
    # (the final answer). This pulls each one out by type.
    thinking_block = next((b.thinking for b in response.content if b.type == "thinking"), None)
    text_block = next((b.text for b in response.content if b.type == "text"), None)
    return {"thinking": thinking_block, "answer": text_block}


def prompt_caching_demo(sizing_policy_text: str, use_real: bool = USE_REAL_API):
    if not use_real:
        return {
            "first_call": "[MOCK] cache_creation_input_tokens: 1200, cache_read_input_tokens: 0",
            "second_call": "[MOCK] cache_creation_input_tokens: 0, cache_read_input_tokens: 1200",
        }

    client = get_client()

    # cache_control marks this system-prompt block as cacheable. "ephemeral"
    # is currently the only cache type the API offers — it expires after a
    # short idle window (a few minutes), which is fine for back-to-back calls.
    system_blocks = [{
        "type": "text",
        "text": sizing_policy_text,
        "cache_control": {"type": "ephemeral"},
    }]

    # First call: no cache exists yet, so Claude has to process the full
    # sizing_policy_text and write it into the cache (a "cache write").
    first = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        system=system_blocks,
        messages=[{"role": "user", "content": "Summarize the sizing policy in one sentence."}],
    )
    # Second call: same system_blocks, so the API recognizes the cached
    # content and reads it back instead of reprocessing it (a "cache read"
    # — cheaper and faster than the first call).
    second = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        system=system_blocks,
        messages=[{"role": "user", "content": "What's the Fibonacci scale used for sizing?"}],
    )

    # .usage on each response reports token counts, including how many were
    # cache writes vs. cache reads — that's the actual proof caching worked.
    return {"first_call_usage": first.usage, "second_call_usage": second.usage}


def citations_demo(query_text: str, use_real: bool = USE_REAL_API):
    # Reuse Module 5's retrieve() to get real, grounded source chunks —
    # same call pattern you already built and tested.
    results = retrieve(query_text, category="epics", n_results=2)
    documents = results["documents"][0]  # [0] because query_texts always returns a list of lists

    if not use_real:
        return {
            "answer": "[MOCK — no API call made] Based on EPIC-0213, the billing engine "
                      "migration is estimated at 13 story points.",
            "sources_available": documents,
        }

    client = get_client()
    # Each retrieved chunk becomes its own "document" content block, with
    # citations enabled — this tells Claude "you may cite this specific
    # source when you use it in your answer."
    content_blocks = [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": doc},
            "citations": {"enabled": True},
        }
        for doc in documents
    ]
    # The actual question comes last, after all the source documents.
    content_blocks.append({"type": "text", "text": query_text})

    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        messages=[{"role": "user", "content": content_blocks}],
    )
    # Returned as raw content blocks (not just .text) because citation
    # responses include extra citation metadata alongside the answer text.
    return response.content


def vision_demo(image_path: str = f"{ASSETS_DIR}/dashboard_screenshot.png", use_real: bool = USE_REAL_API):
    if not use_real:
        return ("[MOCK — no API call made] The dashboard shows 4 Epics with story point "
                 "estimates ranging from 1 to 21, with EPIC-0034 as the largest.")

    # Open the image file in binary mode ("rb") and base64-encode it — the
    # API only accepts image bytes as a base64 text string, not raw binary.
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [
                # An "image" content block, base64-encoded, with its media type declared.
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_data}},
                {"type": "text", "text": "What does this Epic sizing dashboard show?"},
            ],
        }],
    )
    return response.content[0].text


def pdf_demo(pdf_path: str = f"{ASSETS_DIR}/epic_report.pdf", use_real: bool = USE_REAL_API):
    if not use_real:
        return ("[MOCK — no API call made] The report covers 3 Epics related to billing "
                 "engine migration, with estimates of 13, 21, and 1 story points respectively.")

    # Same base64 pattern as vision_demo, just reading a PDF file instead of a PNG.
    with open(pdf_path, "rb") as f:
        pdf_data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = get_client()
    response = client.messages.create(
        model=TEST_MODEL,
        max_tokens=TEST_MAX_TOKENS,
        messages=[{
            "role": "user",
            "content": [
                # A "document" content block for the PDF — same shape as the
                # image block, different type and media_type.
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_data}},
                {"type": "text", "text": "Summarize this Epic report in 2 sentences."},
            ],
        }],
    )
    return response.content[0].text


# Runs each of the 5 demos in sequence and prints the result, so you can
# see all of Module 6 working in one command.
if __name__ == "__main__":
    print("=== Extended Thinking ===")
    print(extended_thinking_demo())

    print("\n=== Prompt Caching ===")
    # A long, repeated string just to give the cache something non-trivial
    # to cache — real sizing policy text would work the same way.
    sample_policy = "Epics are sized on the Fibonacci scale: 1, 2, 3, 5, 8, 13, 21. " * 50
    print(prompt_caching_demo(sample_policy))

    print("\n=== Citations ===")
    print(citations_demo("What is the estimate for the billing engine migration?"))

    print("\n=== Vision ===")
    print(vision_demo())

    print("\n=== PDF ===")
    print(pdf_demo())