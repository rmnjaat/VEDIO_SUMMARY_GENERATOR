"""Abstract base classes for pluggable AI providers.

Each provider type defines a minimal interface. Implementations can
use any backend (local model, cloud API, etc.) as long as they
conform to the interface.
"""
from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Interface for text-to-speech providers."""

    @abstractmethod
    def generate(self, text: str, output_path: str, **kwargs) -> tuple[str, float]:
        """Generate speech audio from text.

        Args:
            text: The narration text to speak.
            output_path: Where to save the audio file.
            **kwargs: Provider-specific options (voice, language, etc.)

        Returns:
            Tuple of (output_path, duration_seconds).
        """

    def get_name(self) -> str:
        return self.__class__.__name__


class ImageProvider(ABC):
    """Interface for image generation providers."""

    @abstractmethod
    def generate(self, prompt: str, output_path: str, **kwargs) -> str:
        """Generate an image from a text prompt.

        Args:
            prompt: Description of what the image should show.
            output_path: Where to save the image (PNG).
            **kwargs: Provider-specific options (size, style, etc.)

        Returns:
            The output_path on success.
        """

    def get_name(self) -> str:
        return self.__class__.__name__


class VideoProvider(ABC):
    """Interface for video rendering providers."""

    @abstractmethod
    def render(self, scenes: list[dict], images_dir: str, audio_dir: str, output_path: str, **kwargs) -> str:
        """Assemble scenes into a final video.

        Args:
            scenes: List of scene dicts with narration, visual_hint, duration, etc.
            images_dir: Directory containing scene_N.png files.
            audio_dir: Directory containing scene_N.wav/.mp3 files.
            output_path: Where to save the final video.
            **kwargs: Provider-specific options (fps, transitions, etc.)

        Returns:
            Path to the rendered video.
        """

    def get_name(self) -> str:
        return self.__class__.__name__
