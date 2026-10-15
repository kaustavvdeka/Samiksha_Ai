"""
tests/test_planner.py
=====================
Unit tests for the agent planner and LLM provider factory.
"""

import pytest
from unittest.mock import MagicMock, patch

from agent.planner import Planner
from agent.state import AgentState
from llm.base import BaseLLM, LLMMessage, LLMResponse, ToolCall
from llm.provider import get_llm_provider, OpenAILLM, LocalLLM


class DummyLLM(BaseLLM):
    """Test double implementing BaseLLM."""

    def __init__(self, response: LLMResponse):
        self._response = response

    def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        return self._response

    def chat_with_tools(self, messages: list[LLMMessage], tools: list) -> LLMResponse:
        return self._response


class TestPlanner:
    def test_planner_direct_text_response(self):
        expected_response = LLMResponse(
            content="Hello, I am Samiksha.",
            tool_calls=[],
            finish_reason="stop",
        )
        dummy = DummyLLM(expected_response)
        planner = Planner(dummy)

        state = AgentState()
        state.add_user_message("Hello")
        response = planner.plan(state)

        assert response.content == "Hello, I am Samiksha."
        assert not response.has_tool_calls

    def test_planner_tool_calls_response(self):
        tool_call = ToolCall(
            id="call_99",
            tool_name="open_application",
            arguments={"application": "Brave"},
        )
        expected_response = LLMResponse(
            content="",
            tool_calls=[tool_call],
            finish_reason="tool_calls",
        )
        dummy = DummyLLM(expected_response)
        planner = Planner(dummy)

        state = AgentState()
        state.add_user_message("Open Brave")
        response = planner.plan(state)

        assert response.has_tool_calls
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "open_application"
        assert response.tool_calls[0].arguments["application"] == "Brave"

    def test_planner_multi_step_tool_calls(self):
        tool_call1 = ToolCall(id="c1", tool_name="open_application", arguments={"application": "Brave"})
        tool_call2 = ToolCall(id="c2", tool_name="search_google", arguments={"query": "Swin Transformer"})
        expected_response = LLMResponse(
            content="",
            tool_calls=[tool_call1, tool_call2],
            finish_reason="tool_calls",
        )
        dummy = DummyLLM(expected_response)
        planner = Planner(dummy)

        state = AgentState()
        state.add_user_message("Open Brave and search Google for Swin Transformer")
        response = planner.plan(state)

        assert len(response.tool_calls) == 2
        assert response.tool_calls[0].tool_name == "open_application"
        assert response.tool_calls[1].tool_name == "search_google"


class TestLLMProviderFactory:
    def test_factory_returns_openai_provider(self):
        import os
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            with patch("openai.OpenAI"):
                provider = get_llm_provider()
                assert isinstance(provider, OpenAILLM)

    def test_factory_returns_local_provider(self):
        import os
        with patch.dict(os.environ, {"LLM_PROVIDER": "local"}):
            with patch("openai.OpenAI"):
                provider = get_llm_provider()
                assert isinstance(provider, LocalLLM)

    def test_factory_returns_gemini_provider(self):
        import os
        from llm.provider import GeminiLLM
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "LLM_API_KEY": "test_key"}):
            with patch("openai.OpenAI"):
                provider = get_llm_provider()
                assert isinstance(provider, GeminiLLM)

    def test_factory_returns_mock_provider(self):
        import os
        from llm.provider import MockLLM
        with patch.dict(os.environ, {"LLM_PROVIDER": "mock"}):
            provider = get_llm_provider()
            assert isinstance(provider, MockLLM)

    def test_mock_llm_selects_tool(self):
        from llm.provider import MockLLM
        mock_llm = MockLLM()
        msg = LLMMessage(role="user", content="Open WhatsApp")
        resp = mock_llm.chat_with_tools([msg], [])
        assert resp.has_tool_calls
        assert resp.tool_calls[0].tool_name == "open_application"
        assert resp.tool_calls[0].arguments["application"] == "Whatsapp"

    def test_factory_raises_on_unknown_provider(self):
        import os
        with patch.dict(os.environ, {"LLM_PROVIDER": "unknown_provider"}):
            with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
                get_llm_provider()
