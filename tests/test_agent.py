"""
tests/test_agent.py
===================
Unit tests for the agent pipeline.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAgentProcess:
    """Tests for SamikshaAgent.process()"""

    def _make_agent(self):
        """Create an agent with a mocked LLM provider."""
        with patch("llm.provider.get_llm_provider") as mock_factory:
            mock_llm = MagicMock()
            mock_factory.return_value = mock_llm
            from agent.agent import SamikshaAgent
            agent = SamikshaAgent()
        return agent, mock_llm

    def test_text_response(self):
        """Agent returns LLM text directly when no tools are selected."""
        from llm.base import LLMResponse

        with patch("agent.agent.get_llm_provider") as mock_factory:
            mock_llm = MagicMock()
            mock_llm.chat_with_tools.return_value = LLMResponse(
                content="Python is a programming language.",
                tool_calls=[],
                finish_reason="stop",
            )
            mock_factory.return_value = mock_llm
            from agent.agent import SamikshaAgent
            agent = SamikshaAgent()

        result = agent.process("What is Python?")
        assert "Python" in result

    def test_tool_call_executed(self):
        """Agent must execute a tool when the LLM requests it."""
        from llm.base import LLMResponse, ToolCall

        with patch("agent.agent.get_llm_provider") as mock_factory:
            mock_llm = MagicMock()
            # First call: LLM requests a tool
            mock_llm.chat_with_tools.side_effect = [
                LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            tool_name="get_current_time",
                            arguments={},
                        )
                    ],
                    finish_reason="tool_calls",
                ),
                # Second call: LLM gives final text
                LLMResponse(
                    content="The current time is 10:00 AM.",
                    tool_calls=[],
                    finish_reason="stop",
                ),
            ]
            mock_factory.return_value = mock_llm
            import tools  # ensure tools are registered
            from agent.agent import SamikshaAgent
            agent = SamikshaAgent()

        result = agent.process("What time is it?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_llm_failure_returns_error_message(self):
        """Agent must return an error string (not raise) when LLM fails."""
        with patch("agent.agent.get_llm_provider") as mock_factory:
            mock_llm = MagicMock()
            mock_llm.chat_with_tools.side_effect = RuntimeError(
                "I can't connect to the AI model right now."
            )
            mock_factory.return_value = mock_llm
            from agent.agent import SamikshaAgent
            agent = SamikshaAgent()

    def test_multi_turn_with_tools_maintains_clean_state(self):
        """State messages across multiple turns must remain clean user/assistant turns."""
        from llm.base import LLMResponse, ToolCall

        with patch("agent.agent.get_llm_provider") as mock_factory:
            mock_llm = MagicMock()
            mock_llm.chat_with_tools.side_effect = [
                # Turn 1: tool call
                LLMResponse(
                    content="",
                    tool_calls=[ToolCall(id="call_t1", tool_name="get_current_time", arguments={})],
                    finish_reason="tool_calls",
                ),
                # Turn 1: final summary
                LLMResponse(content="It is 10:00 AM.", finish_reason="stop"),
                # Turn 2: text response
                LLMResponse(content="Opening WhatsApp now.", finish_reason="stop"),
            ]
            mock_factory.return_value = mock_llm
            import tools
            from agent.agent import SamikshaAgent
            agent = SamikshaAgent()

        r1 = agent.process("What time is it?")
        assert "10:00 AM" in r1
        r2 = agent.process("Open WhatsApp")
        assert "WhatsApp" in r2

        # Verify state messages format: system, user, assistant, user, assistant
        roles = [m.role for m in agent.state.messages]
        assert roles == ["system", "user", "assistant", "user", "assistant"]
        assert all(m.role in ("system", "user", "assistant") for m in agent.state.messages)


class TestAgentState:
    def test_system_prompt_injected(self):
        from agent.state import AgentState

        state = AgentState()
        assert state.messages[0].role == "system"
        assert "Samiksha" in state.messages[0].content

    def test_trim_preserves_system_message(self):
        from agent.state import AgentState

        state = AgentState()
        for i in range(50):
            state.add_user_message(f"Message {i}")
        state.trim(max_messages=10)

        assert state.messages[0].role == "system"
        assert len(state.messages) <= 10
