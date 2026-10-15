"""
llm/base.py
===========
Abstract base class for all LLM providers.

Design principle:
  The agent NEVER imports OpenAI, Anthropic, or any specific SDK directly.
  It always talks to a BaseLLM subclass.
  To switch models (GPT-4o → Claude → Llama), only llm/provider.py changes.

Data classes:
  LLMMessage  — a single message in the conversation history.
  LLMResponse — the model's reply, including optional tool calls.

Implementing a new provider:
  1. Create a class that extends BaseLLM.
  2. Implement chat() and optionally chat_with_tools().
  3. Register it in llm/provider.py.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    """
    A single message in the conversation.

    Attributes:
        role:    "system" | "user" | "assistant" | "tool"
        content: The text content of the message.
        name:    Optional: tool name (used in tool result messages).
    """
    role: str
    content: str
    name: str | None = None


@dataclass
class ToolCall:
    """
    Represents a single tool invocation requested by the LLM.

    Attributes:
        id:        Unique call ID (used to match results back to the LLM).
        tool_name: Name of the tool to call (must exist in the tool registry).
        arguments: Dict of argument name → value.
    """
    id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """
    The full response from an LLM call.

    Attributes:
        content:    The text reply (may be empty if tool_calls are present).
        tool_calls: List of tool calls the model wants to execute.
        finish_reason: Why the model stopped: "stop" | "tool_calls" | "length".
    """
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLM(ABC):
    """
    Abstract interface every LLM provider must implement.

    Methods:
        chat:             Simple text-in / text-out.
        chat_with_tools:  Tool-calling capable chat (for the agent planner).
    """

    @abstractmethod
    def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        """
        Send messages to the model and get a text response.

        Args:
            messages: Full conversation history including system prompt.

        Returns:
            LLMResponse with text content.
        """
        ...

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """
        Send messages with tool definitions; model may request tool calls.

        Args:
            messages: Full conversation history.
            tools:    List of tool schemas in OpenAI function-calling format.

        Returns:
            LLMResponse which may contain tool_calls.
        """
        ...
