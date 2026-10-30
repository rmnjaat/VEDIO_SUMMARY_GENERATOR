"""Assemble scene images and audio into a final video."""
import os
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
)
from .subtitles import create_subtitle_clip


def assemble_video(scenes: list[dict], images_dir: str, audio_dir: str, output_path: str) -> str:
    """Combine per-scene images and audio into a single MP4.

    Args:
        scenes: List of scene dicts (need scene_id, narration).
        images_dir: Directory containing scene_N.png files.
        audio_dir: Directory containing scene_N.mp3 files.
        output_path: Where to write the final MP4.

    Returns:
        The output_path.
    """
    clips = []

    for scene in scenes:
        sid = scene["scene_id"]
        img_path = os.path.join(images_dir, f"scene_{sid}.png")
        audio_path = os.path.join(audio_dir, f"scene_{sid}.mp3")

        if not os.path.exists(img_path) or not os.path.exists(audio_path):
            print(f"Skipping scene {sid}: missing files")
            continue

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        image_clip = ImageClip(img_path).set_duration(duration)

        # Add subtitles
        subtitle = create_subtitle_clip(
            scene.get("narration", ""), duration, (1920, 1080)
        )

        video_clip = CompositeVideoClip([image_clip, subtitle])
        video_clip = video_clip.set_audio(audio_clip)
        clips.append(video_clip)

    if not clips:
        raise ValueError("No clips were generated")

    final = concatenate_videoclips(clips, method="compose")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
    )

    # Cleanup
    for clip in clips:
        clip.close()
    final.close()

    return output_path
