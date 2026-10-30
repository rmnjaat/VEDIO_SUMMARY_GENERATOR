"""Google Imagen 3 — cloud image generation provider."""
from google import genai
from .base import ImageProvider
from stage4_images.imagen import generate_image as _generate


class ImagenProvider(ImageProvider):
    """Image generation using Google Imagen 3 (uses Gemini credits)."""

    def __init__(self, client: genai.Client):
        self.client = client

    def generate(self, prompt: str, output_path: str, **kwargs) -> str:
        return _generate(self.client, prompt, output_path)
