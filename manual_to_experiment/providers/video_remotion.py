"""Remotion — local React-based video rendering provider."""
from .base import VideoProvider
from stage6_video.renderer import render_video as _render


class RemotionProvider(VideoProvider):
    """Video rendering using Remotion (local, free, React-based)."""

    def render(self, scenes: list[dict], images_dir: str, audio_dir: str, output_path: str, **kwargs) -> str:
        return _render(scenes, images_dir, audio_dir, output_path)
