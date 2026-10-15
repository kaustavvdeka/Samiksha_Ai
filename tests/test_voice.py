"""
tests/test_voice.py
===================
Unit tests for TTS, Sarvam STT, and Microphone modules.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestTTS:
    """Tests for voice/tts.py"""

    def test_speak_prints_text(self, capsys):
        """speak() must always print the text regardless of TTS availability."""
        from voice.tts import TTS

        tts = TTS(api_url="http://localhost:9999")  # Wrong port — should fail gracefully

        with patch.object(tts, "synthesise", side_effect=RuntimeError("TTS down")):
            tts.speak("Hello world")

        captured = capsys.readouterr()
        assert "Hello world" in captured.out

    def test_synthesise_raises_on_empty(self):
        """synthesise() should raise ValueError for empty input."""
        from voice.tts import TTS

        tts = TTS()
        with pytest.raises(ValueError):
            tts.synthesise("")

    def test_synthesise_calls_correct_endpoint(self):
        """synthesise() must POST to /tts with correct JSON body."""
        from voice.tts import TTS

        tts = TTS(api_url="http://localhost:8000", voice="nova")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_mp3_bytes"

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = tts.synthesise("Opening YouTube.")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["text"] == "Opening YouTube."
        assert call_kwargs.kwargs["json"]["voice"] == "nova"
        assert result == b"fake_mp3_bytes"

    def test_health_check_true(self):
        from voice.tts import TTS

        tts = TTS()
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            assert tts.health_check() is True

    def test_health_check_false_on_connection_error(self):
        from voice.tts import TTS
        import requests

        tts = TTS()
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            assert tts.health_check() is False

    def test_synthesise_raises_on_connection_error(self):
        from voice.tts import TTS
        import requests

        tts = TTS()
        with patch(
            "requests.post",
            side_effect=requests.exceptions.ConnectionError,
        ):
            with pytest.raises(RuntimeError, match="not reachable"):
                tts.synthesise("Test")


class TestSarvamSTT:
    """Tests for voice/sarvam_stt.py"""

    def test_transcribe_returns_text(self, tmp_path):
        """transcribe() must return the transcript from a successful response."""
        from voice.sarvam_stt import SarvamSTT

        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"\x00" * 100)  # Dummy WAV

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcript": "Open YouTube please",
            "language_code": "en-IN",
        }

        stt = SarvamSTT()
        with patch("requests.post", return_value=mock_response):
            with patch.object(type(stt), "api_key", new_callable=PropertyMock, return_value="fake_key"):
                result = stt.transcribe(wav_file)

        assert result == "Open YouTube please"

    def test_transcribe_raises_on_connection_error(self, tmp_path):
        from voice.sarvam_stt import SarvamSTT
        import requests

        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"\x00" * 100)

        stt = SarvamSTT()
        with patch("requests.post", side_effect=requests.exceptions.ConnectionError):
            with patch.object(type(stt), "api_key", new_callable=PropertyMock, return_value="fake_key"):
                with pytest.raises(RuntimeError, match="unavailable"):
                    stt.transcribe(wav_file)

    def test_transcribe_raises_on_non_200(self, tmp_path):
        from voice.sarvam_stt import SarvamSTT

        wav_file = tmp_path / "test.wav"
        wav_file.write_bytes(b"\x00" * 100)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorised"

        stt = SarvamSTT()
        with patch("requests.post", return_value=mock_response):
            with patch.object(type(stt), "api_key", new_callable=PropertyMock, return_value="fake_key"):
                with pytest.raises(RuntimeError, match="401"):
                    stt.transcribe(wav_file)


class TestMicrophone:
    """Tests for voice/microphone.py and voice/audio.py normalization"""

    def test_normalize_pcm(self):
        import numpy as np
        from voice.audio import normalize_pcm

        arr = np.array([0.1, -0.2, 0.4, -0.3], dtype=np.float32)
        norm = normalize_pcm(arr, target_peak=0.9)
        assert np.isclose(float(np.max(np.abs(norm))), 0.9)

    def test_normalize_pcm_empty(self):
        import numpy as np
        from voice.audio import normalize_pcm

        arr = np.array([], dtype=np.float32)
        assert len(normalize_pcm(arr)) == 0

    def test_record_fixed_returns_array(self):
        import numpy as np
        from voice.microphone import Microphone

        mic = Microphone(sample_rate=16000, max_duration=1)
        fake_frames = np.zeros((16000, 1), dtype=np.float32)

        with patch("sounddevice.rec", return_value=fake_frames):
            with patch("sounddevice.wait"):
                pcm = mic.record(enable_vad=False)

        assert isinstance(pcm, np.ndarray)
        assert len(pcm) == 16000

    def test_record_to_wav_returns_none_on_empty(self):
        import numpy as np
        from voice.microphone import Microphone

        mic = Microphone()
        with patch.object(mic, "record", return_value=np.array([], dtype=np.float32)):
            result = mic.record_to_wav()
            assert result is None

    def test_record_to_wav_saves_file(self, tmp_path):
        import numpy as np
        from voice.microphone import Microphone

        mic = Microphone(sample_rate=16000)
        fake_pcm = np.ones(16000, dtype=np.float32) * 0.1

        with patch.object(mic, "record", return_value=fake_pcm):
            wav_path = mic.record_to_wav()
            try:
                assert wav_path is not None
                assert wav_path.exists()
                assert wav_path.stat().st_size > 44  # Valid WAV header + data
            finally:
                if wav_path:
                    wav_path.unlink(missing_ok=True)



class TestPermissions:
    """Tests for security/permissions.py"""

    def test_safe_tools(self):
        from security.permissions import PermissionChecker, ActionLevel

        checker = PermissionChecker()
        assert checker.check("open_application") == ActionLevel.SAFE
        assert checker.check("search_google") == ActionLevel.SAFE
        assert checker.check("take_screenshot") == ActionLevel.SAFE

    def test_confirmation_required(self):
        from security.permissions import PermissionChecker, ActionLevel

        checker = PermissionChecker()
        assert checker.check("delete_file") == ActionLevel.CONFIRMATION_REQUIRED
        assert checker.check("shutdown_computer") == ActionLevel.CONFIRMATION_REQUIRED

    def test_blocked_tools(self):
        from security.permissions import PermissionChecker, ActionLevel

        checker = PermissionChecker()
        assert checker.check("execute_arbitrary_shell") == ActionLevel.BLOCKED
        assert checker.check("format_disk") == ActionLevel.BLOCKED
