"""Generate subtitle overlays for video clips."""
from moviepy.editor import TextClip


def create_subtitle_clip(text: str, duration: float, size: tuple[int, int]):
    """Create a subtitle text clip positioned at the bottom center.

    Args:
        text: The subtitle text.
        duration: How long to show the subtitle.
        size: Video dimensions (width, height).

    Returns:
        A TextClip positioned at bottom-center.
    """
    if not text.strip():
        return TextClip("", fontsize=1, color="white").set_duration(duration)

    # Wrap long text to ~60 chars per line
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 60:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))

    # Keep only last 2 lines to avoid cluttering
    display_text = "\n".join(lines[-2:])

    txt_clip = TextClip(
        display_text,
        fontsize=36,
        color="white",
        stroke_color="black",
        stroke_width=2,
        font="DejaVu-Sans-Bold",
        method="caption",
        size=(size[0] - 100, None),
    ).set_position(("center", size[1] - 120)).set_duration(duration)

    return txt_clip
