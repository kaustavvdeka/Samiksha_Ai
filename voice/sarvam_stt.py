"""
voice/sarvam_stt.py
===================
Sarvam AI Speech-to-Text integration.

Architecture:
  - Sends a WAV file to the Sarvam STT REST endpoint.
  - Returns the transcribed text string.
  - All Sarvam-specific HTTP logic is isolated here.
    The rest of the agent only calls `stt.transcribe(wav_path)`.

Sarvam STT API reference:
  POST https://api.sarvam.ai/speech-to-text
  Headers:
    api-subscription-key: <your key>
  Body (multipart/form-data):
    file: <WAV audio file>
    model: saarika:v2          (default)
    language_code: en-IN       (default; set to "unknown" for auto-detect)

Response JSON:
  {
    "transcript": "transcribed text here",
    "language_code": "en-IN",
    ...
  }

Usage:
    stt = SarvamSTT()
    text = stt.transcribe(wav_path)
"""

from pathlib import Path

import requests

from config.settings import settings
from logger import get_logger

log = get_logger(__name__)

# Sarvam model name for general STT (v2 is deprecated by Sarvam; v3 is active)
_DEFAULT_MODEL = "saaras:v3"
# Language code — "en-IN" default for Indian English, or "unknown" for auto-detect
_DEFAULT_LANG = "en-IN"


class SarvamSTT:
    """
    Speech-to-Text using the Sarvam AI API.

    This class is the ONLY place that knows about Sarvam's HTTP interface.
    Swap this class to use a different STT provider (Whisper, Google, etc.)
    without touching any agent logic.
    """

    def __init__(
        self,
        model: str | None = None,
        language_code: str | None = None,
    ) -> None:
        self.endpoint = settings.sarvam_stt_endpoint
        self.model = model or getattr(settings, "sarvam_model", _DEFAULT_MODEL)
        self.language_code = (
            language_code
            or getattr(settings, "sarvam_language_code", _DEFAULT_LANG)
        )

        # Read the key lazily so tests can patch it
        self._api_key: str | None = None

    @property
    def api_key(self) -> str:
        if not self._api_key:
            self._api_key = settings.sarvam_api_key
        return self._api_key

    def transcribe(self, wav_path: Path) -> str:
        """
        Send a WAV file to Sarvam and return the transcribed text.

        Args:
            wav_path: Path to a mono 16 kHz WAV file.

        Returns:
            Transcribed text, or empty string if nothing was heard.

        Raises:
            RuntimeError: If the Sarvam API is unreachable or returns an error.
        """
        log.info(
            "Sending audio to Sarvam STT",
            extra={"file": str(wav_path), "model": self.model},
        )

        try:
            with open(wav_path, "rb") as audio_file:
                response = requests.post(
                    self.endpoint,
                    headers={"api-subscription-key": self.api_key},
                    files={"file": ("audio.wav", audio_file, "audio/wav")},
                    data={
                        "model": self.model,
                        "language_code": self.language_code,
                    },
                    timeout=30,
                )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(
                "Speech recognition is currently unavailable. "
                "Cannot reach the Sarvam AI server. Check your internet connection."
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                "Speech recognition timed out. Sarvam AI did not respond in time."
            ) from exc

        if response.status_code != 200:
            log.error(
                "Sarvam STT error",
                extra={"status": response.status_code, "body": response.text[:200]},
            )
            if response.status_code in (401, 403):
                raise RuntimeError(
                    f"Sarvam STT authentication failed (HTTP {response.status_code}): Invalid or missing API key. "
                    "Please check that SARVAM_API_KEY in .env is set to your actual key from https://www.sarvam.ai"
                )
            raise RuntimeError(
                f"Sarvam STT returned HTTP {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        transcript = data.get("transcript", "").strip()

        log.info(
            "Transcription received",
            extra={"transcript": transcript[:80]},
        )

        return transcript

    def transcribe_from_pcm(
        self, pcm_data: "np.ndarray", sample_rate: int  # noqa: F821
    ) -> str:
        """
        Convenience method: save PCM to a temp WAV, then transcribe.

        Args:
            pcm_data:    1-D float32 NumPy array.
            sample_rate: Sample rate of the PCM data.

        Returns:
            Transcribed text string.
        """
        from voice.audio import save_wav_bytes  # deferred to avoid import-time audio chain

        wav_path = save_wav_bytes(pcm_data, sample_rate)
        try:
            return self.transcribe(wav_path)
        finally:
            wav_path.unlink(missing_ok=True)  # Clean up the temp file
