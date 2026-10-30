"""Create styled text slides as fallback when image generation fails."""
import os
from PIL import Image, ImageDraw, ImageFont


# Dark gradient-style colors
BG_COLOR = (26, 26, 46)       # dark navy
TEXT_COLOR = (255, 255, 255)   # white
ACCENT_COLOR = (99, 140, 255) # blue accent
MUTED_COLOR = (160, 160, 180) # grey for subtitle


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Try to load a good font, fall back to default."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",              # macOS
        "/System/Library/Fonts/SFNSText.ttf",               # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def create_fallback_slide(
    step_title: str,
    section_name: str,
    step_number: str,
    output_path: str,
) -> str:
    """Create a styled 1920x1080 slide with step info.

    Args:
        step_title: Main text (e.g. "Connect Water Supply").
        section_name: Section label (e.g. "Initial Setup").
        step_number: Step label (e.g. "Step 3" or "Intro").
        output_path: Where to save the PNG.

    Returns:
        The output_path.
    """
    img = Image.new("RGB", (1920, 1080), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_large = _get_font(72)
    font_medium = _get_font(36)
    font_small = _get_font(28)

    # Step number (top-left area)
    draw.text((120, 80), step_number.upper(), fill=ACCENT_COLOR, font=font_medium)

    # Section name (below step number)
    if section_name:
        draw.text((120, 130), section_name, fill=MUTED_COLOR, font=font_small)

    # Main title (centered vertically)
    # Word-wrap if too long
    words = step_title.split()
    lines = []
    current = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) > 35:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))

    total_height = len(lines) * 90
    y_start = (1080 - total_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_large)
        text_w = bbox[2] - bbox[0]
        x = (1920 - text_w) // 2
        draw.text((x, y_start + i * 90), line, fill=TEXT_COLOR, font=font_large)

    # Bottom accent line
    draw.rectangle([120, 1000, 1800, 1004], fill=ACCENT_COLOR)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
