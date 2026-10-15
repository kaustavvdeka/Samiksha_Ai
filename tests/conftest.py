"""
tests/conftest.py
=================
Pytest configuration: sets up a dummy .env before tests run,
so test imports don't fail on missing required env vars.
"""
import os
import pytest


def pytest_configure(config):
    """Inject placeholder environment variables before any test imports."""
    os.environ.setdefault("SARVAM_API_KEY", "test_sarvam_key")
    os.environ.setdefault("LLM_API_KEY", "test_llm_key")
    os.environ.setdefault("LLM_PROVIDER", "openai")
    os.environ.setdefault("LLM_MODEL", "gpt-4o")
    os.environ.setdefault("TTS_API_URL", "http://localhost:8000")
    os.environ.setdefault("LOG_LEVEL", "WARNING")   # Quieter during tests
    os.environ.setdefault("MEMORY_DB_PATH", ":memory:")  # In-memory for tests
