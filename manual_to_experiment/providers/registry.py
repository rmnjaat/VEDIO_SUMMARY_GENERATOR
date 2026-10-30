"""Provider registry — register and retrieve providers by name.

Supports multiple providers per type (TTS, Image, Video).
Select the active provider at runtime via config.
"""
from .base import TTSProvider, ImageProvider, VideoProvider

_registry = None


class ProviderRegistry:
    """Central registry for all AI providers."""

    def __init__(self):
        self._tts: dict[str, TTSProvider] = {}
        self._image: dict[str, ImageProvider] = {}
        self._video: dict[str, VideoProvider] = {}
        self._active_tts: str | None = None
        self._active_image: str | None = None
        self._active_video: str | None = None

    # ── Register ──────────────────────────────────────────────────
    def register_tts(self, name: str, provider: TTSProvider):
        self._tts[name] = provider
        if self._active_tts is None:
            self._active_tts = name

    def register_image(self, name: str, provider: ImageProvider):
        self._image[name] = provider
        if self._active_image is None:
            self._active_image = name

    def register_video(self, name: str, provider: VideoProvider):
        self._video[name] = provider
        if self._active_video is None:
            self._active_video = name

    # ── Select active ─────────────────────────────────────────────
    def set_active_tts(self, name: str):
        if name not in self._tts:
            raise ValueError(f"TTS provider '{name}' not registered. Available: {list(self._tts.keys())}")
        self._active_tts = name

    def set_active_image(self, name: str):
        if name not in self._image:
            raise ValueError(f"Image provider '{name}' not registered. Available: {list(self._image.keys())}")
        self._active_image = name

    def set_active_video(self, name: str):
        if name not in self._video:
            raise ValueError(f"Video provider '{name}' not registered. Available: {list(self._video.keys())}")
        self._active_video = name

    # ── Get active ────────────────────────────────────────────────
    def get_tts(self) -> TTSProvider:
        if not self._active_tts:
            raise RuntimeError("No TTS provider registered")
        return self._tts[self._active_tts]

    def get_image(self) -> ImageProvider:
        if not self._active_image:
            raise RuntimeError("No Image provider registered")
        return self._image[self._active_image]

    def get_video(self) -> VideoProvider:
        if not self._active_video:
            raise RuntimeError("No Video provider registered")
        return self._video[self._active_video]

    # ── List available ────────────────────────────────────────────
    def list_tts(self) -> list[str]:
        return list(self._tts.keys())

    def list_image(self) -> list[str]:
        return list(self._image.keys())

    def list_video(self) -> list[str]:
        return list(self._video.keys())


def get_registry() -> ProviderRegistry:
    """Get or create the global provider registry singleton."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
