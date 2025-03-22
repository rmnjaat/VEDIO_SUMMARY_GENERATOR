"""Create a simple text slide as fallback when image generation fails."""
from PIL import Image, ImageDraw, ImageFont


def create_fallback_slide(title: str, output_path: str) -> str:
    """Create a white 1920x1080 slide with centered title text.

    Args:
        title: Text to display on the slide.
        output_path: Where to save the PNG.

    Returns:
        The output_path.
    """
    img = Image.new("RGB", (1920, 1080), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), title, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (1920 - text_w) // 2
    y = (1080 - text_h) // 2

    draw.text((x, y), title, fill="black", font=font)
    img.save(output_path, "PNG")
    return output_path
