# voice/__init__.py
# Lazy package — import submodules directly to avoid pulling in all audio
# dependencies when only one submodule is needed.
# from voice.microphone import Microphone
# from voice.sarvam_stt import SarvamSTT
# from voice.tts import TTS

__all__ = ["Microphone", "SarvamSTT", "TTS"]


def __getattr__(name: str):
    if name == "Microphone":
        from voice.microphone import Microphone
        return Microphone
    if name == "SarvamSTT":
        from voice.sarvam_stt import SarvamSTT
        return SarvamSTT
    if name == "TTS":
        from voice.tts import TTS
        return TTS
    raise AttributeError(f"module 'voice' has no attribute {name!r}")
