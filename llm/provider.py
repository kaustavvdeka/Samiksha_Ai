"""
llm/provider.py
===============
Concrete LLM implementations + factory function.

Supported providers (set LLM_PROVIDER in .env):
  "openai"    — OpenAI GPT-4o (default)
  "anthropic" — Anthropic Claude
  "local"     — Any OpenAI-compatible local server (Ollama, LM Studio, etc.)

To add a new provider:
  1. Create a class inheriting BaseLLM below.
  2. Add a mapping in get_llm_provider().

Design note:
  We use the OpenAI SDK for all three providers because:
    - Anthropic's messages API is compatible in structure.
    - Ollama / LM Studio expose an OpenAI-compatible endpoint.
  This avoids importing multiple SDKs for Milestone 2.
  A dedicated AnthropicLLM can be added later without changing the agent.
"""

import json
from typing import Any

from openai import OpenAI, APIConnectionError, APIStatusError

from config.settings import settings
from llm.base import BaseLLM, LLMMessage, LLMResponse, ToolCall
from logger import get_logger

log = get_logger(__name__)


# ============================================================
# OpenAI / GPT-4o provider
# ============================================================

class OpenAILLM(BaseLLM):
    """
    LLM provider backed by the OpenAI API (GPT-4o, GPT-4-turbo, etc.).

    Set in .env:
        LLM_PROVIDER=openai
        LLM_API_KEY=sk-...
        LLM_MODEL=gpt-4o
    """

    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.llm_api_key)
        self.model = settings.llm_model
        log.info("OpenAI LLM initialised", extra={"model": self.model})

    def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        """Text-only chat call."""
        openai_messages = _to_openai_messages(messages)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
            )
            return LLMResponse(
                content=resp.choices[0].message.content or "",
                finish_reason=resp.choices[0].finish_reason,
            )
        except APIConnectionError as exc:
            raise RuntimeError(
                "I can't connect to the AI model right now. "
                "Check your internet connection and LLM_API_KEY."
            ) from exc
        except APIStatusError as exc:
            if exc.status_code in (401, 403):
                raise RuntimeError(
                    f"OpenAI authentication failed (HTTP {exc.status_code}): Invalid or incorrect API key. "
                    "Please check that LLM_API_KEY in .env is set to your actual key from https://platform.openai.com/api-keys, "
                    "or set LLM_PROVIDER=mock in .env for offline testing."
                ) from exc
            raise RuntimeError(
                f"LLM API error {exc.status_code}: {exc.message}"
            ) from exc

    def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Tool-calling chat — the model may respond with tool calls."""
        openai_messages = _to_openai_messages(messages)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=tools,
                tool_choice="auto",
            )
        except APIConnectionError as exc:
            raise RuntimeError(
                "I can't connect to the AI model right now."
            ) from exc
        except APIStatusError as exc:
            if exc.status_code in (401, 403):
                raise RuntimeError(
                    f"OpenAI authentication failed (HTTP {exc.status_code}): Invalid or incorrect API key. "
                    "Please check that LLM_API_KEY in .env is set to your actual key from https://platform.openai.com/api-keys, "
                    "or set LLM_PROVIDER=mock in .env for offline testing."
                ) from exc
            raise RuntimeError(
                f"LLM API error {exc.status_code}: {exc.message}"
            ) from exc

        choice = resp.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls: list[ToolCall] = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        tool_name=tc.function.name,
                        arguments=args,
                    )
                )
            log.info(
                "LLM requested tool calls",
                extra={"tools": [t.tool_name for t in tool_calls]},
            )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )


# ============================================================
# Local / Ollama / LM Studio provider (OpenAI-compatible)
# ============================================================

class LocalLLM(BaseLLM):
    """
    LLM provider pointing to a local OpenAI-compatible server.

    Examples: Ollama, LM Studio, vLLM, text-generation-webui.

    Set in .env:
        LLM_PROVIDER=local
        LLM_API_KEY=not-needed   (or leave as placeholder)
        LLM_MODEL=llama3          (your local model name)
        LLM_BASE_URL=http://localhost:11434/v1   (Ollama default)
    """

    def __init__(self) -> None:
        import os
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        api_key = settings.llm_api_key or "not-needed"
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = settings.llm_model
        log.info(
            "Local LLM initialised",
            extra={"model": self.model, "base_url": base_url},
        )

    def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        openai_messages = _to_openai_messages(messages)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
            )
            return LLMResponse(
                content=resp.choices[0].message.content or "",
                finish_reason=resp.choices[0].finish_reason,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Local LLM is not responding: {exc}. "
                "Make sure Ollama / LM Studio is running."
            ) from exc

    def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        openai_messages = _to_openai_messages(messages)
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=tools,
                tool_choice="auto",
            )
        except Exception as exc:
            raise RuntimeError(
                f"Local LLM is not responding: {exc}."
            ) from exc

        choice = resp.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls: list[ToolCall] = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, tool_name=tc.function.name, arguments=args)
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )


# ============================================================
# Mock / Offline rule-based provider
# ============================================================

class MockLLM(BaseLLM):
    """
    Offline tool-calling provider for testing system automation
    without requiring external API keys or network connection.
    """

    def __init__(self) -> None:
        log.info("Mock LLM initialised (offline rule-based mode)")

    def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        last_msg = messages[-1].content if messages else ""
        return LLMResponse(content=f"Processed: {last_msg}")

    def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        last_msg = messages[-1].content if messages else ""

        # Follow-up summary after tools ran
        if any(m.role == "tool" for m in messages[-4:]):
            return LLMResponse(content="I've completed that action for you.")

        lower = last_msg.lower().strip()

        # YouTube search / open
        if "youtube" in lower:
            query = lower.replace("search youtube for", "").replace("search youtube", "").replace("open youtube and search for", "").replace("open youtube", "").strip()
            query = query or "machine learning tutorials"
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_yt", tool_name="search_youtube", arguments={"query": query})],
                finish_reason="tool_calls",
            )

        # Google search
        if "search google" in lower or "search for" in lower or "google" in lower:
            query = lower.replace("search google for", "").replace("search google", "").replace("search for", "").strip()
            query = query or "Swin Transformer paper"
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_g", tool_name="search_google", arguments={"query": query})],
                finish_reason="tool_calls",
            )

        # Open Application
        if lower.startswith("open ") and not any(w in lower for w in ("website", "url", "file", "project")):
            app = lower.replace("open", "").strip().title()
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_app", tool_name="open_application", arguments={"application": app})],
                finish_reason="tool_calls",
            )

        # Close Application
        if lower.startswith("close "):
            app = lower.replace("close", "").strip()
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_close", tool_name="close_application", arguments={"application": app})],
                finish_reason="tool_calls",
            )

        # Time
        if "time" in lower:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_time", tool_name="get_current_time", arguments={})],
                finish_reason="tool_calls",
            )

        # Screenshot
        if "screenshot" in lower:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_ss", tool_name="take_screenshot", arguments={})],
                finish_reason="tool_calls",
            )

        # Custom workflow
        if "start coding" in lower:
            return LLMResponse(
                content="",
                tool_calls=[ToolCall(id="call_mock_wf", tool_name="execute_custom_workflow", arguments={"name": "start coding"})],
                finish_reason="tool_calls",
            )

        return LLMResponse(content=f"Understood: '{last_msg}'. How else can I help?")


# ============================================================
# Helper utilities
# ============================================================

def _to_openai_messages(messages: list[LLMMessage]) -> list[dict]:
    """Convert LLMMessage list to the dict format OpenAI expects."""
    result = []
    for m in messages:
        msg: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.name:
            msg["name"] = m.name
        result.append(msg)
    return result


# ============================================================
# Google Gemini Provider (via OpenAI compatibility endpoint)
# ============================================================

class GeminiLLM(BaseLLM):
    """
    LLM provider backed by Google Gemini via its OpenAI-compatible endpoint.

    Supports automatic fallback across Gemini models (e.g. gemini-2.5-flash-lite,
    gemini-3.5-flash) if one model's free-tier rate limit or quota is exhausted.

    Set in .env:
        LLM_PROVIDER=gemini
        LLM_API_KEY=your_gemini_api_key
        LLM_MODEL=gemini-2.5-flash-lite
    """

    FALLBACK_MODELS = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]


    def __init__(self) -> None:
        raw_model = settings.llm_model.strip()
        if not raw_model or raw_model in ("gemini", "gemini-flash"):
            raw_model = "gemini-2.5-flash-lite"
        self.model = raw_model
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        log.info("Gemini LLM initialised", extra={"model": self.model})

    def _call_with_fallback(self, func, **kwargs) -> Any:
        """Try configured model first; if rate-limited (429) or overloaded (503), try fallbacks."""
        models_to_try = [self.model] + [m for m in self.FALLBACK_MODELS if m != self.model]
        last_exc: Exception | None = None

        for m in models_to_try:
            try:
                return func(model=m, **kwargs)
            except Exception as exc:
                last_exc = exc
                err_str = str(exc)
                if any(code in err_str for code in ("429", "RESOURCE_EXHAUSTED", "503", "404")):
                    log.warning(
                        "Gemini model error, trying fallback model",
                        extra={"failed_model": m, "error": err_str[:120]},
                    )
                    continue
                # Other errors (e.g. invalid arguments) should raise immediately
                raise

        raise RuntimeError(f"All Gemini models failed. Last error: {last_exc}") from last_exc

    def chat(self, messages: list[LLMMessage]) -> LLMResponse:
        openai_messages = _to_openai_messages(messages)
        try:
            resp = self._call_with_fallback(
                self.client.chat.completions.create,
                messages=openai_messages,
                max_tokens=1000,
            )
            return LLMResponse(
                content=resp.choices[0].message.content or "",
                finish_reason=resp.choices[0].finish_reason,
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini API error: {exc}") from exc

    def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        openai_messages = _to_openai_messages(messages)
        try:
            resp = self._call_with_fallback(
                self.client.chat.completions.create,
                messages=openai_messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000,
            )
        except Exception as exc:
            raise RuntimeError(f"Gemini API error: {exc}") from exc

        choice = resp.choices[0]
        message = choice.message
        content = message.content or ""
        tool_calls: list[ToolCall] = []

        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        tool_name=tc.function.name,
                        arguments=args,
                    )
                )
            log.info(
                "Gemini chose tools",
                extra={"tools": [t.tool_name for t in tool_calls]},
            )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )


# ============================================================
# Factory
# ============================================================

def get_llm_provider() -> BaseLLM:
    """
    Instantiate and return the configured LLM provider.

    Reads LLM_PROVIDER from .env and returns the matching implementation.
    Add new providers here — the rest of the agent stays unchanged.
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return OpenAILLM()
    elif provider == "gemini":
        return GeminiLLM()
    elif provider == "local":
        return LocalLLM()
    elif provider == "mock":
        return MockLLM()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER='{provider}'. "
            "Supported values: 'gemini', 'openai', 'local', 'mock'."
        )
