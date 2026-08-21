"""
app/prompts/technique_demos.py

Module 3 (Prompt Engineering Techniques) — demonstrates 4 named techniques
applied to the real Epic-sizing prompt, each with a before/after comparison.
Runs mock-first via Conversation(), zero API cost.
"""

from app.agent.conversation import Conversation

SAMPLE_EPIC = {
    "title": "Migrate billing engine for Payments Platform",
    "description": (
        "Migrate the legacy billing engine to the new platform for the "
        "Payments Platform team. This involves reworking the invoicing "
        "logic, coordinating with the Core Banking team on a shared "
        "dependency, and running parallel validation before cutover."
    ),
}


def demo_clarity_and_specificity() -> dict:
    scale = (1, 2, 3, 5, 8, 13, 21)

    before_prompt = (
        f"Estimate this Epic: {SAMPLE_EPIC['title']} — "
        f"{SAMPLE_EPIC['description']}"
    )

    after_prompt = (
        f"Estimate the size of this Epic using the Fibonacci scale "
        f"{scale}.\n\n"
        f"Epic title: {SAMPLE_EPIC['title']}\n"
        f"Epic description: {SAMPLE_EPIC['description']}\n\n"
        f"Weigh two factors: (1) the overall scope of work described, "
        f"and (2) any cross-team dependencies mentioned. "
        f"Output only the single number from the scale above — no "
        f"explanation, no extra text."
    )

    convo_before = Conversation()
    before_response = convo_before.send(before_prompt)

    convo_after = Conversation()
    after_response = convo_after.send(after_prompt)

    return {
        "before_prompt": before_prompt,
        "before_response": before_response,
        "after_prompt": after_prompt,
        "after_response": after_response,
    }


def demo_xml_tags() -> dict:
    scale = (1, 2, 3, 5, 8, 13, 21)

    before_prompt = (
        f"Estimate the size of this Epic using the Fibonacci scale "
        f"{scale}. The Epic is titled {SAMPLE_EPIC['title']} and "
        f"{SAMPLE_EPIC['description']}. "
        f"Weigh two factors: (1) the overall scope of work described "
        f"and (2) any cross-team dependencies mentioned. "
        f"Output only the single number from the scale above and no "
        f"explanation, no extra text."
    )

    after_prompt = (
        "<epic_context>"
        f"Epic title: {SAMPLE_EPIC['title']}\n"
        f"Epic description: {SAMPLE_EPIC['description']}"
        "</epic_context>"
        "<instructions>"
        f"Estimate the size of this Epic using the Fibonacci scale "
        f"{scale}. Weigh two factors: (1) the overall scope of work "
        f"described, and (2) any cross-team dependencies mentioned. "
        f"Output only the single number from the scale above — no "
        f"explanation, no extra text."
        "</instructions>"
    )

    convo_before = Conversation()
    before_response = convo_before.send(before_prompt)

    convo_after = Conversation()
    after_response = convo_after.send(after_prompt)

    return {
        "before_prompt": before_prompt,
        "before_response": before_response,
        "after_prompt": after_prompt,
        "after_response": after_response,
    }


def demo_few_shot_examples() -> dict:
    scale = (1, 2, 3, 5, 8, 13, 21)

    before_prompt = (
        f"Estimate the size of this Epic using the Fibonacci scale "
        f"{scale}. The Epic is titled {SAMPLE_EPIC['title']} and "
        f"{SAMPLE_EPIC['description']}. "
        f"Weigh two factors: (1) the overall scope of work described "
        f"and (2) any cross-team dependencies mentioned. "
        f"Output only the single number from the scale above and no "
        f"explanation, no extra text."
    )

    after_prompt = (
        "Example 1:\n"
        "Epic: Migrate notification service for Payments Platform\n"
        "Estimate: 1\n\n"
        "Example 2:\n"
        "Epic: Migrate document management system for Payments Platform\n"
        "Estimate: 2\n\n"
        "Example 3:\n"
        "Epic: Migrate billing engine for Risk & Compliance\n"
        "Estimate: 21\n\n"
        "Now estimate this Epic using the same scale.\n"
        f"Epic: {SAMPLE_EPIC['title']} — {SAMPLE_EPIC['description']}\n"
        f"Estimate using the Fibonacci scale {scale}. Weigh the same "
        f"two factors: (1) overall scope, (2) cross-team dependencies. "
        f"Output only the number, no explanation."
    )

    convo_before = Conversation()
    before_response = convo_before.send(before_prompt)

    convo_after = Conversation()
    after_response = convo_after.send(after_prompt)

    return {
        "before_prompt": before_prompt,
        "before_response": before_response,
        "after_prompt": after_prompt,
        "after_response": after_response,
    }


def demo_chain_of_thought_scaffolding() -> dict:
    scale = (1, 2, 3, 5, 8, 13, 21)

    before_prompt = (
        f"Estimate the size of this Epic using the Fibonacci scale "
        f"{scale}. The Epic is titled {SAMPLE_EPIC['title']} and "
        f"{SAMPLE_EPIC['description']}. "
        f"Weigh two factors: (1) the overall scope of work described "
        f"and (2) any cross-team dependencies mentioned. "
        f"Output only the single number from the scale above and no "
        f"explanation, no extra text."
    )

    after_prompt = (
        "<reasoning>\n"
        f"Before answering, work through: (1) which similar historical "
        f"Epics this resembles, (2) any cross-team dependencies "
        f"mentioned in the description, (3) complexity signals from "
        f"the scope of work described.\n"
        "</reasoning>\n"
        "<answer>\n"
        f"Using the Fibonacci scale {scale}, estimate the size of this "
        f"Epic: {SAMPLE_EPIC['title']} — {SAMPLE_EPIC['description']}. "
        f"Output only the single number, no explanation.\n"
        "</answer>"
    )

    convo_before = Conversation()
    before_response = convo_before.send(before_prompt)

    convo_after = Conversation()
    after_response = convo_after.send(after_prompt)

    return {
        "before_prompt": before_prompt,
        "before_response": before_response,
        "after_prompt": after_prompt,
        "after_response": after_response,
    }


def run_all_demos() -> None:
    demos = [
        ("Clarity & Specificity", demo_clarity_and_specificity),
        ("XML-Tag Structuring", demo_xml_tags),
        ("Few-Shot Examples", demo_few_shot_examples),
        ("Chain-of-Thought Scaffolding", demo_chain_of_thought_scaffolding),
    ]

    for name, fn in demos:
        result = fn()
        print(f"\n{'=' * 60}")
        print(f"TECHNIQUE: {name}")
        print(f"{'=' * 60}")
        print(f"\n--- BEFORE ---\nPrompt: {result['before_prompt']}\n")
        print(f"Response: {result['before_response']}\n")
        print(f"--- AFTER ---\nPrompt: {result['after_prompt']}\n")
        print(f"Response: {result['after_response']}\n")


if __name__ == "__main__":
    run_all_demos()