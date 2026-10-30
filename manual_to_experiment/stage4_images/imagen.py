"""Generate images using Gemini Imagen 3 API."""
import os
from google import genai
from google.genai import types
from PIL import Image
import io


STYLE_PREFIX = (
    "Instructional product photography style. Clean white background. "
    "Professional, clear, well-lit. No text overlays. "
)
STYLE_SUFFIX = " Realistic, educational, suitable for a how-to video."


def generate_image(client: genai.Client, visual_hint: str, output_path: str) -> str:
    """Generate a 1920x1080 image from a visual hint using Imagen 3.

    Args:
        client: A google.genai.Client instance.
        visual_hint: Description of what the image should show.
        output_path: Where to save the PNG file.

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If image generation fails.
    """
    full_prompt = STYLE_PREFIX + visual_hint + STYLE_SUFFIX

    response = client.models.generate_images(
        model="imagen-3.0-generate-001",
        prompt=full_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
        ),
    )

    if not response.generated_images:
        raise RuntimeError(f"Imagen returned no images for: {visual_hint[:80]}")

    image_bytes = response.generated_images[0].image.image_bytes
    img = Image.open(io.BytesIO(image_bytes))
    img = img.resize((1920, 1080), Image.LANCZOS)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
