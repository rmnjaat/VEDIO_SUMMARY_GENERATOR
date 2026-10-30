"""Coqui XTTS v2 — local voice-cloning TTS provider."""
from .base import TTSProvider
from stage5_audio.tts import generate_audio as _generate


class XTTSProvider(TTSProvider):
    """Voice-cloning TTS using Coqui XTTS v2 (runs locally, free)."""

    def __init__(self, reference_voice: str | None = None, language: str = "en"):
        self.reference_voice = reference_voice
        self.language = language

    def generate(self, text: str, output_path: str, **kwargs) -> tuple[str, float]:
        ref = kwargs.get("reference_voice", self.reference_voice)
        lang = kwargs.get("language", self.language)
        return _generate(text, output_path, reference_voice=ref, language=lang)
