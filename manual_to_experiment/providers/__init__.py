"""Pluggable provider interfaces for TTS, Image Generation, and Video Rendering.

To add a new provider:
1. Create a class that implements the corresponding base class
2. Register it in the provider registry
3. Select it via config or CLI flag

Example:
    from providers import TTSProvider, ImageProvider, VideoProvider

    class MyCustomTTS(TTSProvider):
        def generate(self, text, output_path, **kwargs):
            # your implementation
            return output_path, duration
"""

from .base import TTSProvider, ImageProvider, VideoProvider
from .registry import ProviderRegistry, get_registry
