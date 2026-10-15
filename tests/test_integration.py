"""
tests/test_integration.py
=========================
Integration tests for the complete Samiksha pipeline:
Voice / Text -> STT -> Agent -> Planner -> Tool Execution -> TTS output.
"""

import pytest
from unittest.mock import MagicMock, patch

from agent.agent import SamikshaAgent
from llm.base import LLMResponse, ToolCall
from voice.tts import TTS
from voice.sarvam_stt import SarvamSTT


class TestIntegrationPipeline:
    """End-to-end integration tests verifying cross-module communication."""

    def test_voice_to_tts_full_pipeline(self, tmp_path):
        """
        Simulate the complete loop:
        WAV audio -> Sarvam STT transcription -> Agent reasoning -> Tool execution -> TTS synthesis.
        """
        dummy_wav = tmp_path / "command.wav"
        dummy_wav.write_bytes(b"\x00" * 200)

        # 1. Mock Sarvam STT to return a user command
        stt = SarvamSTT()
        mock_stt_response = MagicMock()
        mock_stt_response.status_code = 200
        mock_stt_response.json.return_value = {"transcript": "What time is it?"}

        with patch("requests.post", return_value=mock_stt_response):
            with patch.object(type(stt), "api_key", return_value="test_key"):
                transcribed_text = stt.transcribe(dummy_wav)

        assert transcribed_text == "What time is it?"

        # 2. Agent processes transcribed command with Tool Calling
        with patch("agent.agent.get_llm_provider") as mock_llm_factory:
            mock_llm = MagicMock()
            # Turn 1: LLM selects get_current_time tool
            # Turn 2: LLM provides natural language summary
            mock_llm.chat_with_tools.side_effect = [
                LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCall(id="call_t1", tool_name="get_current_time", arguments={})
                    ],
                    finish_reason="tool_calls",
                ),
                LLMResponse(
                    content="The current time is 2:30 PM.",
                    tool_calls=[],
                    finish_reason="stop",
                ),
            ]
            mock_llm_factory.return_value = mock_llm

            agent = SamikshaAgent()
            agent_response = agent.process(transcribed_text)

        assert "The current time is 2:30 PM." in agent_response

        # 3. Feed agent response to TTS
        tts = TTS(api_url="http://localhost:8000")
        mock_tts_response = MagicMock()
        mock_tts_response.status_code = 200
        mock_tts_response.content = b"fake_mp3_audio_data"

        with patch("requests.post", return_value=mock_tts_response) as mock_tts_post:
            tts_audio = tts.synthesise(agent_response)

        assert tts_audio == b"fake_mp3_audio_data"
        mock_tts_post.assert_called_once()
        assert mock_tts_post.call_args.kwargs["json"]["text"] == "The current time is 2:30 PM."

    def test_multi_step_workflow_integration(self):
        """
        Verify multi-step command execution in the agent:
        e.g. Save memory then recall it.
        """
        with patch("agent.agent.get_llm_provider") as mock_llm_factory:
            mock_llm = MagicMock()
            # Step 1: Agent saves main project path
            mock_llm.chat_with_tools.side_effect = [
                LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="c1",
                            tool_name="save_memory",
                            arguments={"key": "cropguard_dir", "value": "/projects/cropguard"},
                        )
                    ],
                    finish_reason="tool_calls",
                ),
                LLMResponse(
                    content="I have remembered that cropguard_dir is /projects/cropguard.",
                    tool_calls=[],
                    finish_reason="stop",
                ),
                # Step 2: Agent queries memory
                LLMResponse(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="c2",
                            tool_name="get_memory",
                            arguments={"key": "cropguard_dir"},
                        )
                    ],
                    finish_reason="tool_calls",
                ),
                LLMResponse(
                    content="Your project is located at /projects/cropguard.",
                    tool_calls=[],
                    finish_reason="stop",
                ),
            ]
            mock_llm_factory.return_value = mock_llm

            agent = SamikshaAgent()
            resp1 = agent.process("Remember that my project cropguard is at /projects/cropguard")
            assert "cropguard" in resp1

            resp2 = agent.process("Where is my cropguard project?")
            assert "/projects/cropguard" in resp2
