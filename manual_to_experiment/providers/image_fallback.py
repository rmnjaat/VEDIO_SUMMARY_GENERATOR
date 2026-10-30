"""Pillow text slide — fallback image provider (no GPU, no API)."""
from .base import ImageProvider
from stage4_images.fallback_slide import create_fallback_slide


class FallbackSlideProvider(ImageProvider):
    """Generates styled text slides using Pillow. Always works, no dependencies."""

    def generate(self, prompt: str, output_path: str, **kwargs) -> str:
        section = kwargs.get("section", "")
        step_number = kwargs.get("step_number", "")
        return create_fallback_slide(
            step_title=prompt[:80],
            section_name=section,
            step_number=step_number,
            output_path=output_path,
        )
