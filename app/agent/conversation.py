"""
app/agent/conversation.py

Building with the Claude API — Module 1, Lessons 4-5: "Multi-turn
conversations" + "System prompts" + "Temperature"

The Claude API is stateless: every call is a fresh, blank-slate request with
no memory of anything sent before. This module creates the *illusion* of
memory by holding a running list of every message (both user and assistant)
and resending that full history on every call. Claude isn't remembering —
we're re-showing it the whole transcript each time.

System prompts are handled separately from `messages` on purpose: the
Claude API takes `system` as its own top-level argument on
`client.messages.create(...)`, not as an entry in the messages list. It's
set once per conversation and applies to every turn, rather than being
resent as part of the back-and-forth history.

Temperature controls how much randomness Claude uses when picking its next
token — low values (near 0) favor consistent, repeatable answers; high
values (near 1) favor varied, more creative ones. This project defaults to
temperature=0 because Epic-sizing estimates need to be consistent and
defensible, not creative — the same question with the same data should
produce the same answer, which directly supports the groundedness metric
the eval harness measures.

This is also the foundation the agent's tool-use loop will build on later
(Module 4: Tool Use), so it's built here as real, reusable project code
rather than throwaway notebook code.

Streaming vs. complete message (Module 1, Lesson: "Streaming"):
    This module deliberately uses the COMPLETE MESSAGE pattern (wait for the
    full response, then use it) rather than streaming (processing the
    response token-by-token as it arrives). This was an evaluated choice,
    not an oversight:
      - The SOX-conscious audit log needs the full, final response text to
        log as one clean entry — streaming would mean reconstructing the
        complete text from chunks before logging anyway.
      - The upcoming tool-use loop (Module 4) needs a complete, well-formed
        structured response to detect and parse tool calls — parsing a
        tool-call decision mid-stream is significantly more complex than
        waiting for the finished response.
      - The eval harness scores complete answers, not partial ones.
    Streaming's real benefit — a more responsive feel for a human watching
    the UI — is a presentation-layer concern, not a core-agent-logic one.
    If added later, it belongs at the Streamlit UI layer (Day 22), sitting
    on top of this same complete-message backend, not built into
    Conversation itself.

Cost control:
    Reuses the same mock-first pattern as client.py. By default, Conversation
    runs in MOCK mode — no network call, no tokens spent. Flip
    USE_REAL_API = True in client.py (or pass use_real=True when creating a
    Conversation) only when you deliberately want real responses.
"""

from app.agent.client import get_client, USE_REAL_API, TEST_MODEL, TEST_MAX_TOKENS

# Default system prompt: keeps every Conversation groundedness-first by
# default, directly supporting the project's eval harness goals (no
# invented answers, no silent guessing).
DEFAULT_SYSTEM_PROMPT = (
    "You are an enterprise planning assistant. Only answer using "
    "information explicitly provided to you; if information is missing, "
    "say so rather than guessing."
)


class Conversation:
    """
    Holds a running multi-turn conversation with Claude, including an
    optional system prompt and a temperature setting that both apply to
    the whole conversation.

    Usage:
        convo = Conversation()
        reply_1 = convo.send("What's blocking Epic-142?")
        reply_2 = convo.send("What about the dependency on finance approval?")
        # convo.messages now holds all 4 entries (2 user, 2 assistant) —
        # reply_2 was generated with full awareness of the first exchange,
        # and both replies were shaped by the system prompt and temperature.
    """

    def __init__(
        self,
        use_real: bool = USE_REAL_API,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0,
    ):
        # This list is the entire "memory" of the conversation. Nothing
        # about it is special to Claude — it's a plain Python list that we
        # resend in full on every call.
        self.messages = []
        self.use_real = use_real
        # Can be None if a caller explicitly wants no system prompt at all
        # (e.g. Conversation(system_prompt=None)) — send() below handles
        # that case so we never pass system=None to the real API.
        self.system_prompt = system_prompt
        self.temperature = temperature

    def _add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def _add_assistant_message(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    def send(self, user_text: str) -> str:
        """
        Adds `user_text` as a new user turn, sends the FULL message history
        (plus the system prompt, if set) to Claude — or returns a mock reply
        — records Claude's reply as a new assistant turn, and returns the
        reply text.
        """
        self._add_user_message(user_text)

        if not self.use_real:
            active_system = self.system_prompt or "(none set)"
            mock_reply = (
                f"[MOCK RESPONSE — no API call made] "
                f"(turn {len(self.messages)}, system_prompt='{active_system}', "
                f"temperature={self.temperature}) "
                f"Acknowledged: '{user_text}'. This mock has no real awareness "
                f"of prior turns, the system prompt, or temperature — a real "
                f"call would, because the full message history, system "
                f"prompt, and temperature are sent each time."
            )
            self._add_assistant_message(mock_reply)
            return mock_reply

        client = get_client()

        # No `stream` argument here — this is a deliberate complete-message
        # call, not an oversight. See the module docstring's "Streaming vs.
        # complete message" section for why: audit logging and the upcoming
        # tool-use loop both need the full, finished response, not chunks.

        # Build the call arguments, only including `system` when it's
        # actually set — passing system=None to the SDK raises a type
        # error rather than being treated as "no system prompt."
        call_kwargs = {
            "model": TEST_MODEL,
            "max_tokens": TEST_MAX_TOKENS,
            "messages": self.messages,
            "temperature": self.temperature,
        }
        if self.system_prompt:
            call_kwargs["system"] = self.system_prompt

        response = client.messages.create(**call_kwargs)
        reply_text = response.content[0].text
        self._add_assistant_message(reply_text)
        return reply_text


if __name__ == "__main__":
    # Run this file directly to see multi-turn + system prompt mechanics
    # without spending any tokens:
    #   python -m app.agent.conversation
    convo = Conversation()
    print(convo.send("What's blocking Epic-142?"))
    print(convo.send("What about the dependency on the finance approval?"))
    print(f"\nFull message history ({len(convo.messages)} entries):")
    for m in convo.messages:
        print(f"  {m['role']}: {m['content'][:60]}...")

    # Confirm the None case works without erroring:
    print("\n--- Testing with no system prompt ---")
    convo_no_system = Conversation(system_prompt=None)
    print(convo_no_system.send("Quick test with no system prompt set."))
