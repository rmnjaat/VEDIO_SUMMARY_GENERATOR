"""Generate images using Imagen 3 via Gemini API."""
import os
import google.generativeai as genai
from PIL import Image
import io


STYLE_PREFIX = (
    "Instructional product photography style. Clean white background. "
    "Professional, clear, well-lit. No text overlays. "
)
STYLE_SUFFIX = " Realistic, educational, suitable for a how-to video."


def generate_image(visual_hint: str, output_path: str) -> str:
    """Generate a 1920x1080 image from a visual hint.

    Args:
        visual_hint: Description of what the image should show.
        output_path: Where to save the PNG file.

    Returns:
        The output_path on success.
    """
    full_prompt = STYLE_PREFIX + visual_hint + STYLE_SUFFIX

    imagen = genai.ImageGenerationModel("imagen-3.0-generate-001")
    result = imagen.generate_images(
        prompt=full_prompt,
        number_of_images=1,
        aspect_ratio="16:9",
    )

    image = result.images[0]
    img = Image.open(io.BytesIO(image._image_bytes))
    img = img.resize((1920, 1080), Image.LANCZOS)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
