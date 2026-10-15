"""
config/settings.py
==================
Central configuration loaded from environment variables.

All secrets (API keys, URLs) must be in .env — never hard-coded here.

Usage:
    from config.settings import settings
    print(settings.sarvam_api_key)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve the project root (parent of config/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from the project root
load_dotenv(PROJECT_ROOT / ".env")


def is_placeholder(val: str | None) -> bool:
    """Check if a string is empty or contains an unfilled placeholder."""
    if not val:
        return True
    v = val.strip().lower()
    return (
        v.startswith("your_")
        or v.endswith("_here")
        or "placeholder" in v
        or v == "sk-..."
    )


def _require(key: str, fallback_keys: list[str] | None = None) -> str:
    """Read a required environment variable; check fallbacks and raise if missing or placeholder."""
    value = os.getenv(key)
    if not value or is_placeholder(value):
        if fallback_keys:
            for fb in fallback_keys:
                fb_val = os.getenv(fb)
                if fb_val and not is_placeholder(fb_val):
                    return fb_val
        raise EnvironmentError(
            f"Environment variable '{key}' is not set or still contains a placeholder. "
            f"Please update your .env file with a valid key."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    """Read an optional environment variable with a default."""
    return os.getenv(key, default)


class Settings:
    """
    Singleton-style settings object.
    All configuration for the Samiksha agent lives here.
    """

    # ------------------------------------------------------------------ #
    # Sarvam AI — Speech-to-Text
    # ------------------------------------------------------------------ #
    @property
    def sarvam_api_key(self) -> str:
        return _require("SARVAM_API_KEY", fallback_keys=["SARVAM_KEY"])

    @property
    def is_sarvam_configured(self) -> bool:
        key = os.getenv("SARVAM_API_KEY") or os.getenv("SARVAM_KEY", "")
        return bool(key) and not is_placeholder(key)

    @property
    def sarvam_model(self) -> str:
        return _optional("SARVAM_MODEL", "saaras:v3")

    @property
    def sarvam_stt_endpoint(self) -> str:
        return _optional(
            "SARVAM_STT_ENDPOINT",
            "https://api.sarvam.ai/speech-to-text"
        )

    @property
    def sarvam_language_code(self) -> str:
        return _optional("SARVAM_LANGUAGE_CODE", "en-IN")


    # ------------------------------------------------------------------ #
    # LLM Provider
    # ------------------------------------------------------------------ #
    @property
    def llm_provider(self) -> str:
        return _optional("LLM_PROVIDER", "openai").lower()

    @property
    def llm_api_key(self) -> str:
        if self.llm_provider in ("local", "mock"):
            return os.getenv("LLM_API_KEY", "not-needed")
        return _require(
            "LLM_API_KEY",
            fallback_keys=["GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY1"]
        )

    @property
    def is_llm_configured(self) -> bool:
        if self.llm_provider in ("local", "mock"):
            return True
        key = (
            os.getenv("LLM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("LLM_API_KEY1", "")
        )
        return bool(key) and not is_placeholder(key)

    @property
    def llm_model(self) -> str:
        return _optional("LLM_MODEL", "gpt-4o")

    # ------------------------------------------------------------------ #
    # Local TTS Service (your Text_To_speech_api repo)
    # ------------------------------------------------------------------ #
    @property
    def tts_api_url(self) -> str:
        return _optional("TTS_API_URL", "http://localhost:8000")

    @property
    def tts_voice(self) -> str:
        return _optional("TTS_VOICE", "nova")

    @property
    def tts_model(self) -> str:
        return _optional("TTS_MODEL", "tts-1")

    # ------------------------------------------------------------------ #
    # Microphone
    # ------------------------------------------------------------------ #
    @property
    def mic_sample_rate(self) -> int:
        return int(_optional("MIC_SAMPLE_RATE", "16000"))

    @property
    def mic_max_duration(self) -> int:
        return int(_optional("MIC_MAX_DURATION", "10"))

    @property
    def mic_vad_threshold(self) -> float:
        return float(_optional("MIC_VAD_THRESHOLD", "0.003"))

    @property
    def mic_speech_timeout(self) -> float:
        return float(_optional("MIC_SPEECH_TIMEOUT", "7.0"))


    # ------------------------------------------------------------------ #
    # Memory
    # ------------------------------------------------------------------ #
    @property
    def memory_db_path(self) -> Path | str:
        raw = _optional("MEMORY_DB_PATH", "./data/samiksha.db")
        if raw == ":memory:":
            return ":memory:"
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    @property
    def log_level(self) -> str:
        return _optional("LOG_LEVEL", "INFO").upper()

    @property
    def log_file(self) -> Path:
        path = Path(_optional("LOG_FILE", "./logs/samiksha.log"))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    @property
    def confirmation_required_tools(self) -> list[str]:
        raw = _optional(
            "CONFIRMATION_REQUIRED_TOOLS",
            "delete_file,move_file,shutdown_computer,restart_computer,"
            "execute_shell,send_email"
        )
        return [t.strip() for t in raw.split(",") if t.strip()]

    # ------------------------------------------------------------------ #
    # Project paths
    # ------------------------------------------------------------------ #
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def screenshots_dir(self) -> Path:
        d = PROJECT_ROOT / "screenshots"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def temp_audio_dir(self) -> Path:
        d = PROJECT_ROOT / "temp_audio"
        d.mkdir(parents=True, exist_ok=True)
        return d


# Single shared instance used throughout the project
settings = Settings()
