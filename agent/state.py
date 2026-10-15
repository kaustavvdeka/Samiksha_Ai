"""
agent/state.py
==============
Conversation state maintained across turns within a single session.

The state holds:
  - The conversation message history (sent to the LLM each turn)
  - The system prompt
  - A counter for turns (useful for debugging)

Design:
  State is in-memory per session. Persistent cross-session memory
  is handled by the Memory class in memory/memory.py.
"""

from dataclasses import dataclass, field
from llm.base import LLMMessage
from agent.prompts import SYSTEM_PROMPT


@dataclass
class AgentState:
    """
    Maintains the rolling conversation history for the current session.

    The messages list is passed to the LLM on every turn so it has
    full context of the conversation.
    """
    messages: list[LLMMessage] = field(default_factory=list)
    turn_count: int = 0

    def __post_init__(self) -> None:
        # Inject the system prompt as the first message
        self.messages.append(
            LLMMessage(role="system", content=SYSTEM_PROMPT)
        )

    def add_user_message(self, content: str) -> None:
        """Append a user turn to the conversation history."""
        self.messages.append(LLMMessage(role="user", content=content))
        self.turn_count += 1

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant (Samiksha) response to the history."""
        self.messages.append(LLMMessage(role="assistant", content=content))

    def add_tool_result(self, tool_name: str, result: str, call_id: str) -> None:
        """Append a tool result message so the LLM can use it."""
        self.messages.append(
            LLMMessage(
                role="tool",
                content=result,
                name=tool_name,
            )
        )

    def trim(self, max_messages: int = 40) -> None:
        """
        Keep the conversation window manageable.

        Always preserves the system prompt (messages[0]).
        Removes the oldest non-system messages when limit is exceeded.
        """
        if len(self.messages) > max_messages:
            system_msg = self.messages[0]
            self.messages = [system_msg] + self.messages[-(max_messages - 1):]
