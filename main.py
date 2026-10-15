"""
main.py
=======
Samiksha AI Voice Computer Agent — entry point.

Voice loop:
  1. Listen via microphone
  2. Sarvam AI → text
  3. Agent (LLM + tools) → response
  4. Local TTS → speak response
  5. Repeat

Run:
    python main.py            # Full voice loop
    python main.py --text     # Text-only mode (type commands, no microphone)
    python main.py --milestone1  # Test Milestone 1: mic → STT → TTS only
"""

import warnings
warnings.filterwarnings("ignore", message=".*urllib3.*doesn't match a supported version.*")

import argparse
import sys
import time

from config.settings import settings  # noqa — loads .env early
from logger import get_logger

log = get_logger("main")


# --------------------------------------------------------------------------- #
# Startup health checks
# --------------------------------------------------------------------------- #

def check_tts(tts) -> bool:
    """Ping the local TTS server and warn if it's not running."""
    if tts.health_check():
        print("✅  TTS server is running.")
        return True
    else:
        print(
            "⚠️  TTS server is NOT running.\n"
            "   Start it with:  cd ../Text_To_speech_api && uvicorn app:app --port 8000\n"
            "   The agent will still respond in text — speech will be skipped."
        )
        return False


def check_environment(mode: str = "voice") -> bool:
    """
    Validate that required API keys in .env are configured and not placeholders.
    Returns True if prerequisites are met, False otherwise.
    """
    ready = True

    if mode in ("voice", "milestone1"):
        if not settings.is_sarvam_configured:
            print("\n" + "!" * 62)
            print("⚠️  SARVAM_API_KEY is not configured in .env!")
            print("   Current value is a placeholder.")
            print("   To use voice transcription:")
            print("     1. Get a free API key at: https://www.sarvam.ai")
            print("     2. Update .env: SARVAM_API_KEY=your_actual_key")
            print("!" * 62 + "\n")
            ready = False

    if mode in ("voice", "text"):
        if not settings.is_llm_configured:
            print("\n" + "!" * 62)
            print("⚠️  LLM_API_KEY is not configured in .env!")
            print(f"   Current provider is '{settings.llm_provider}' with a placeholder key.")
            print("   Options to resolve:")
            print("     1. Provide your OpenAI key in .env:")
            print("        LLM_API_KEY=sk-...")
            print("     2. OR test immediately offline without any API key:")
            print("        Set LLM_PROVIDER=mock in .env")
            print("     3. OR use a local Ollama model:")
            print("        Set LLM_PROVIDER=local in .env")
            print("!" * 62 + "\n")
            ready = False

    return ready


# --------------------------------------------------------------------------- #
# Milestone 1 — Raw echo loop (mic → STT → TTS, no LLM)
# --------------------------------------------------------------------------- #

def run_milestone1() -> None:
    """
    Milestone 1 test loop.
    Speaks back exactly what it hears — no agent, no LLM.
    """
    from voice.microphone import Microphone
    from voice.sarvam_stt import SarvamSTT
    from voice.tts import TTS

    print("\n" + "="*60)
    print("  SAMIKSHA — Milestone 1: Echo Test")
    print("  Speak → STT → TTS echo back")
    print("  Press Ctrl+C to quit")
    print("="*60 + "\n")

    if not check_environment("milestone1"):
        print("Please configure SARVAM_API_KEY in .env before running Milestone 1.")
        return

    mic = Microphone()
    stt = SarvamSTT()
    tts = TTS()

    check_tts(tts)

    while True:
        try:
            # Record
            wav_path = mic.record_to_wav()
            if not wav_path:
                print("🔇  No speech detected. Listening again…\n")
                continue

            # Transcribe
            print("⏳  Transcribing…")
            try:
                text = stt.transcribe(wav_path)
            finally:
                wav_path.unlink(missing_ok=True)


            if not text:
                print("🔇  Nothing detected. Listening again…\n")
                continue

            print(f"📝  You said: {text}")

            # Speak back
            tts.speak(text)

        except KeyboardInterrupt:
            print("\n\n👋  Goodbye!")
            break
        except Exception as exc:
            log.error("Milestone 1 error", extra={"error": str(exc)})
            print(f"❌  Error: {exc}\n")
            # If authentication failed, do not loop continuously
            if "authentication failed" in str(exc).lower() or "403" in str(exc) or "401" in str(exc):
                print("Authentication error detected. Exiting loop. Please check your SARVAM_API_KEY in .env.")
                break
            time.sleep(1)


# --------------------------------------------------------------------------- #
# Full voice loop (Milestones 2+)
# --------------------------------------------------------------------------- #

def run_voice_loop() -> None:
    """
    Full Samiksha voice loop: mic → STT → Agent → TTS.
    """
    print("\n" + "="*60)
    print("  SAMIKSHA — Personal AI Voice Agent")
    print("  Say a command. Press Ctrl+C to quit.")
    print("="*60 + "\n")

    if not check_environment("voice"):
        print("Please configure your .env file before launching the full voice agent.")
        return

    from voice.microphone import Microphone
    from voice.sarvam_stt import SarvamSTT
    from voice.tts import TTS
    from agent.agent import SamikshaAgent

    mic = Microphone()
    stt = SarvamSTT()
    tts = TTS()
    agent = SamikshaAgent()

    check_tts(tts)
    tts.speak("Hello! I'm Samiksha. How can I help you?")

    while True:
        try:
            # Step 1: Listen
            wav_path = mic.record_to_wav()
            if not wav_path:
                print("🔇  No speech detected. Listening again…\n")
                continue

            # Step 2: Transcribe
            print("⏳  Transcribing…")
            try:
                text = stt.transcribe(wav_path)
            except RuntimeError as exc:
                tts.speak(str(exc))
                if "authentication failed" in str(exc).lower() or "403" in str(exc):
                    break
                continue
            finally:
                wav_path.unlink(missing_ok=True)


            if not text:
                print("🔇  Nothing heard. Listening again…\n")
                continue

            print(f"\n🗣  You: {text}")

            # Step 3: Agent processes the command
            try:
                response = agent.process(text)
            except RuntimeError as exc:
                response = str(exc)
                log.error("Agent error", extra={"error": response})

            # Step 4: Speak the response
            tts.speak(response)

        except KeyboardInterrupt:
            tts.speak("Goodbye!")
            print("\n\n👋  Goodbye!")
            break
        except Exception as exc:
            log.error("Unexpected error in voice loop", extra={"error": str(exc)})
            print(f"❌  Unexpected error: {exc}\n")
            time.sleep(1)


# --------------------------------------------------------------------------- #
# Text-only mode (no microphone needed)
# --------------------------------------------------------------------------- #

def run_text_mode() -> None:
    """
    Text-only interaction loop.
    Type commands — no microphone or Sarvam STT needed.
    Useful for testing the agent + tools without voice hardware.
    """
    print("\n" + "="*60)
    print("  SAMIKSHA — Text Mode (no microphone)")
    print("  Type a command and press Enter. Type 'quit' to exit.")
    print("="*60 + "\n")

    check_environment("text")

    from voice.tts import TTS
    from agent.agent import SamikshaAgent

    tts = TTS()
    try:
        agent = SamikshaAgent()
    except EnvironmentError as exc:
        print(f"\n❌ Startup Error: {exc}\n")
        print("Tip: You can set LLM_PROVIDER=mock in .env to test all desktop tools offline.")
        return

    check_tts(tts)

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋  Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            tts.speak("Goodbye!")
            print("👋  Goodbye!")
            break

        try:
            response = agent.process(user_input)
        except RuntimeError as exc:
            response = str(exc)
            log.error("Agent error", extra={"error": response})
            if "authentication failed" in response.lower() or "401" in response:
                print("\nTip: Set LLM_PROVIDER=mock in .env to test without an OpenAI API key.\n")
        tts.speak(response)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Samiksha — Personal AI Voice Computer Agent"
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Run in text-only mode (no microphone, no Sarvam STT)",
    )
    parser.add_argument(
        "--milestone1",
        action="store_true",
        help="Run Milestone 1 echo test (mic → STT → TTS, no LLM)",
    )
    args = parser.parse_args()

    if args.milestone1:
        run_milestone1()
    elif args.text:
        run_text_mode()
    else:
        run_voice_loop()


if __name__ == "__main__":
    main()
