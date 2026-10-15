"""
voice/audio.py
==============
Low-level audio helpers shared across the voice pipeline.

Responsibilities:
  - Play MP3 / WAV audio bytes through the system speaker.
  - Save raw PCM / WAV data to a temp file for STT upload.

Design note:
  MP3 playback uses ffmpeg (via subprocess) to decode to raw PCM,
  then sounddevice plays it. This avoids pydub's audioop dependency
  which was removed in Python 3.13.
  soundfile is used for WAV read/write.
"""

import io
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from logger import get_logger

log = get_logger(__name__)


def play_mp3_bytes(mp3_bytes: bytes) -> None:
    """
    Play MP3 audio bytes through the default output device.

    Supports:
      1. macOS native /usr/bin/afplay (no external dependencies needed)
      2. ffmpeg decode -> sounddevice playback (cross-platform fallback)
      3. ffplay / mpg123 command-line players

    Args:
        mp3_bytes: Raw MP3 data as returned by the TTS API.

    Raises:
        RuntimeError: If no audio player is available or playback fails.
    """
    import platform
    import shutil

    # 1. macOS native afplay (built into every Mac)
    if platform.system() == "Darwin" and shutil.which("afplay"):
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        try:
            tmp.write(mp3_bytes)
            tmp.flush()
            tmp.close()
            log.debug("Playing audio with afplay", extra={"bytes": len(mp3_bytes)})
            subprocess.run(["afplay", tmp.name], check=True)
            return
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"afplay audio playback failed: {exc}") from exc
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    # 2. ffmpeg -> raw PCM -> sounddevice
    if shutil.which("ffmpeg"):
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", "pipe:0",
                    "-f", "s16le",
                    "-acodec", "pcm_s16le",
                    "-ar", "44100",
                    "-ac", "2",
                    "pipe:1",
                ],
                input=mp3_bytes,
                capture_output=True,
                check=True,
            )
            raw_pcm = result.stdout
            samples = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32)
            samples = samples / 32768.0
            samples = samples.reshape(-1, 2)

            log.debug("Playing audio via sounddevice", extra={"bytes": len(mp3_bytes)})
            sd.play(samples, samplerate=44100)
            sd.wait()
            return
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"ffmpeg decode failed: {exc.stderr.decode()[:200]}") from exc
        except Exception as exc:
            raise RuntimeError(f"Audio playback failed: {exc}") from exc

    # 3. Fallback: ffplay or mpg123
    for player in ["ffplay", "mpg123"]:
        if shutil.which(player):
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            try:
                tmp.write(mp3_bytes)
                tmp.flush()
                tmp.close()
                args = [player, "-nodisp", "-autoexit", tmp.name] if player == "ffplay" else [player, "-q", tmp.name]
                subprocess.run(args, check=True)
                return
            finally:
                Path(tmp.name).unlink(missing_ok=True)

    raise RuntimeError(
        "No audio player found. On macOS, afplay is usually available. "
        "On Linux/Windows, install ffmpeg: https://ffmpeg.org/download.html"
    )


def normalize_pcm(pcm_data: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
    """
    Normalize PCM audio float32 array so that its peak reaches target_peak.
    Prevents faint microphone input from being inaudible to STT models.
    """
    if pcm_data.size == 0:
        return pcm_data
    peak = float(np.max(np.abs(pcm_data)))
    if peak > 0.001:  # Only normalize if not pure silence
        return (pcm_data / peak * target_peak).astype(np.float32)
    return pcm_data


def save_wav_bytes(
    pcm_data: np.ndarray, sample_rate: int, normalize: bool = True
) -> Path:
    """
    Save a NumPy PCM array to a temporary WAV file.

    Args:
        pcm_data:    1-D float32 NumPy array of audio samples.
        sample_rate: Sample rate in Hz (e.g. 16000).
        normalize:   Whether to peak-normalize audio volume (default True).

    Returns:
        Path to the temporary WAV file.
    """
    if normalize:
        pcm_data = normalize_pcm(pcm_data)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, dir=None
    )
    tmp_path = Path(tmp.name)
    sf.write(str(tmp_path), pcm_data, sample_rate)
    log.debug("Saved temp WAV", extra={"path": str(tmp_path)})
    return tmp_path

