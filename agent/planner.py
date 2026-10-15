"""
agent/planner.py
================
The planner sends the user's request to the LLM and interprets its response.

Flow:
  1. Build the current message history + tool schemas.
  2. Call the LLM with tool-calling enabled.
  3. If the LLM chose tools → return the list of ToolCall objects.
  4. If the LLM replied with text → return the text.

The planner does NOT execute tools — that's the Executor's job.
"""

from llm.base import BaseLLM, LLMMessage, LLMResponse, ToolCall
from tools.registry import get_tool_schemas
from agent.state import AgentState
from logger import get_logger

log = get_logger(__name__)


class Planner:
    """
    Decides what tools to call (or what text to return) for a given user input.

    Args:
        llm: A BaseLLM implementation (OpenAI, local, etc.).
    """

    def __init__(self, llm: BaseLLM) -> None:
        self.llm = llm

    def plan(self, state: AgentState) -> LLMResponse:
        """
        Ask the LLM what to do given the current conversation state.

        Args:
            state: The current AgentState with conversation history.

        Returns:
            LLMResponse — contains either text content or tool_calls.

        Raises:
            RuntimeError: If the LLM is unavailable.
        """
        return self.plan_messages(state.messages, turn=state.turn_count)

    def plan_messages(
        self,
        messages: list[LLMMessage],
        turn: int = 0,
    ) -> LLMResponse:
        """
        Ask the LLM what to do given an explicit list of LLMMessages.
        """
        tool_schemas = get_tool_schemas()
        log.info(
            "Sending to LLM",
            extra={
                "turn": turn,
                "tools_available": len(tool_schemas),
                "messages": len(messages),
            },
        )

        response = self.llm.chat_with_tools(
            messages=messages,
            tools=tool_schemas,
        )

        if response.has_tool_calls:
            log.info(
                "LLM chose tools",
                extra={"tools": [t.tool_name for t in response.tool_calls]},
            )
        else:
            log.info(
                "LLM replied with text",
                extra={"content_preview": response.content[:80]},
            )

        return response
