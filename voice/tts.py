"""
voice/tts.py
============
Text-to-Speech abstraction layer wired to your local TTS repository
(github.com/kaustavvdeka/Text_To_speech_api).

Architecture:
  Your TTS repo runs as a FastAPI server at http://localhost:8000.
  It exposes:
      POST /tts
      Body: {"text": "...", "voice": "nova", "model": "tts-1"}
      Response: MP3 audio bytes (Content-Type: audio/mpeg)

  This module is the ONLY place that knows about that HTTP interface.
  If you ever replace the TTS backend, only this file changes.

Public interface:
    tts = TTS()
    tts.speak("Opening YouTube.")          # synthesise + play
    mp3 = tts.synthesise("Hello world")   # just get the bytes

Usage:
    from voice.tts import TTS
    tts = TTS()
    tts.speak("Samiksha is ready.")
"""

import requests

from config.settings import settings
from logger import get_logger


log = get_logger(__name__)


class TTS:
    """
    Text-to-Speech using the locally running TTS FastAPI service.

    The TTS server must be started separately before the agent runs:
        cd Text_To_speech_api
        uvicorn app:app --host 0.0.0.0 --port 8000

    Design:
      - speak()      → synthesise + play audio (blocking)
      - synthesise() → return raw MP3 bytes (useful for testing)
    """

    def __init__(
        self,
        api_url: str | None = None,
        voice: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_url = (api_url or settings.tts_api_url).rstrip("/")
        self.voice = voice or settings.tts_voice
        self.model = model or settings.tts_model

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it through the speakers.

        Args:
            text: The text to synthesise and speak aloud.

        On failure, logs the error and prints a fallback message to the
        console rather than crashing the agent loop.
        """
        print(f"\n🔊  Samiksha: {text}")  # Always show text regardless of TTS health

        try:
            mp3_bytes = self.synthesise(text)
            from voice.audio import play_mp3_bytes  # deferred: avoids audio chain at import time
            play_mp3_bytes(mp3_bytes)
        except RuntimeError as exc:
            log.warning(
                "TTS service failed — attempting system audio fallback",
                extra={"error": str(exc)},
            )
            self._fallback_system_speak(text)

    def _fallback_system_speak(self, text: str) -> None:
        """Fallback to high-quality in-process Edge-TTS neural voice or native macOS say command."""
        # 1. Try in-process Edge-TTS neural voice first
        try:
            import asyncio
            import edge_tts
            import re
            from voice.audio import play_mp3_bytes

            is_hindi = any("\u0900" <= ch <= "\u097f" for ch in text)
            edge_voice = (
                "hi-IN-SwaraNeural"
                if is_hindi
                else ("hi-IN-SwaraNeural" if self.voice in ("swara", "hindi") else "en-IN-NeerjaNeural")
            )
            clean_text = re.sub(r"[*#_`~>\[\]]", "", text).strip() or text

            async def _generate() -> bytes:
                comm = edge_tts.Communicate(clean_text, edge_voice)
                chunks = []
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
                return b"".join(chunks)

            audio_data = asyncio.run(_generate())
            if audio_data:
                play_mp3_bytes(audio_data)
                return
        except Exception as exc:
            log.debug(
                "Direct Edge-TTS fallback unavailable, trying system say",
                extra={"error": str(exc)},
            )

        # 2. Native macOS say command (offline fallback)
        import platform
        import shutil
        import subprocess

        if platform.system() == "Darwin" and shutil.which("say"):
            try:
                subprocess.run(["say", text], check=False, timeout=15)
                return
            except Exception:
                pass

        print(
            "[TTS] The response was generated, but voice playback failed. "
            "Check that your TTS server is running."
        )


    def synthesise(self, text: str) -> bytes:
        """
        Send text to the TTS service and return the raw MP3 bytes.

        Args:
            text: Text to synthesise.

        Returns:
            MP3 audio as bytes.

        Raises:
            RuntimeError: If the TTS service is unreachable or returns an error.
        """
        if not text or not text.strip():
            raise ValueError("Cannot synthesise empty text.")

        log.info(
            "Sending text to TTS",
            extra={"text_preview": text[:60], "voice": self.voice},
        )

        try:
            response = requests.post(
                f"{self.api_url}/tts",
                json={
                    "text": text,
                    "voice": self.voice,
                    "model": self.model,
                },
                timeout=60,  # Allow time for cold-start on free Render tier
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "TTS service is not reachable. "
                "Make sure your TTS server is running: "
                "cd Text_To_speech_api && uvicorn app:app --port 8000"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                "TTS service timed out. It may be starting up (cold start). "
                "Try again in a few seconds."
            ) from exc

        if response.status_code != 200:
            raise RuntimeError(
                f"TTS service returned HTTP {response.status_code}: {response.text[:200]}"
            )

        log.debug(
            "TTS response received",
            extra={"bytes": len(response.content)},
        )
        return response.content

    def health_check(self) -> bool:
        """
        Ping the TTS service health endpoint.

        Returns:
            True if the server is healthy, False otherwise.
        """
        try:
            r = requests.get(f"{self.api_url}/health", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
