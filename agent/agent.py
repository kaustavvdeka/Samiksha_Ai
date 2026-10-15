"""
agent/agent.py
==============
The main SamikshaAgent class — the central coordinator.

Pipeline for each user command:
  1. Add user text to AgentState.
  2. Planner calls LLM → gets tool_calls or a direct text response.
  3. If tool_calls:
       a. Executor runs them (with permission checks).
       b. Results are added back to the state.
       c. Planner calls LLM again for a final natural-language response.
  4. If text: use it directly.
  5. Add the assistant's response to the state.
  6. Return the response string (caller will pass it to TTS).

Memory integration:
  - Conversation turns are persisted to SQLite for session continuity.
  - The in-session state.messages list is the working context window.
"""

import time
from typing import Optional

from agent.planner import Planner
from agent.executor import Executor
from agent.state import AgentState
from llm.base import LLMMessage
from llm.provider import get_llm_provider
from memory.memory import Memory
from logger import get_logger

log = get_logger(__name__)


class SamikshaAgent:
    """
    The top-level AI agent.

    Usage:
        agent = SamikshaAgent()
        response = agent.process("Open YouTube")
        # → "Opening YouTube."
    """

    def __init__(self) -> None:
        self.llm = get_llm_provider()
        self.planner = Planner(self.llm)
        self.executor = Executor()
        self.memory = Memory()
        self.state = AgentState()
        log.info("Samiksha agent initialised")

    def process(self, user_text: str) -> str:
        """
        Process a user command and return the agent's response.

        This is the main entry point called from the voice loop.

        Args:
            user_text: The transcribed (or typed) user command.

        Returns:
            A string response suitable for speaking via TTS.
        """
        start_time = time.monotonic()
        log.info("Processing user input", extra={"text": user_text})

        # 1. Store in conversation state
        self.state.add_user_message(user_text)

        # 2. Ask the planner what to do
        try:
            llm_response = self.planner.plan(self.state)
        except RuntimeError as exc:
            raw_err = str(exc)
            log.error("Planner failed", extra={"error": raw_err})
            if "429" in raw_err or "RESOURCE_EXHAUSTED" in raw_err:
                error_msg = "My AI request quota has been reached. Please wait a moment or try again."
            elif "401" in raw_err or "403" in raw_err:
                error_msg = "Authentication failed. Please verify your API key in .env."
            else:
                error_msg = f"Sorry, I couldn't process that: {raw_err[:100]}"
            self.state.add_assistant_message(error_msg)
            return error_msg

        # 3a. LLM wants to call tools
        if llm_response.has_tool_calls:
            tool_results: list[str] = []
            tool_summaries: list[str] = []

            for call in llm_response.tool_calls:
                tool_name, result = self.executor.execute_one(call)
                tool_results.append(result)
                tool_summaries.append(f"{tool_name}: {result}")
                log.info(
                    "Tool result recorded",
                    extra={"tool": tool_name, "result": result[:80]},
                )

            # 3b. Ask the LLM for a final human response based on tool results
            try:
                summary_prompt = (
                    "Actions executed on computer:\n"
                    + "\n".join(f"- {s}" for s in tool_summaries)
                    + "\nGive a brief, natural voice response directly to the user summarising what was done."
                )
                summary_messages = list(self.state.messages) + [
                    LLMMessage(role="user", content=summary_prompt)
                ]
                final_response = self.planner.plan_messages(summary_messages)
                response_text = final_response.content.strip() or "; ".join(tool_results)
            except Exception:
                # If the follow-up LLM call fails, just speak the raw tool result
                response_text = "; ".join(tool_results)



        # 3c. LLM returned a direct text response (no tools needed)
        else:
            response_text = llm_response.content.strip()
            if not response_text:
                response_text = "I'm not sure how to help with that."

        # 4. Persist the assistant's response in state and memory
        self.state.add_assistant_message(response_text)
        self.state.trim()

        # Save conversation turns to SQLite for future reference
        self.memory.add_turn("user", user_text)
        self.memory.add_turn("assistant", response_text)
        self.memory.trim_history()

        elapsed = time.monotonic() - start_time
        log.info(
            "Turn complete",
            extra={
                "response": response_text[:80],
                "elapsed_s": round(elapsed, 2),
            },
        )

        return response_text

    def reset_session(self) -> None:
        """Start a fresh conversation (new session, memory preserved)."""
        self.state = AgentState()
        log.info("Session reset")
