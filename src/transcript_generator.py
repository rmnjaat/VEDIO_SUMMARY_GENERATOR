import os
from .video_source import VideoSource
from .providers.base import TranscriptionProvider
from .providers import PROVIDERS


def unique_path(path: str) -> str:
    """If *path* already exists, append _1, _2, … before the extension."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


class TranscriptGenerator:

    def __init__(self, video_path: str, provider_name: str, api_key: str, output_dir: str):
        """
        Args:
            video_path: Path to the video file on disk.
            provider_name: One of 'groq', 'assemblyai', 'gemini'.
            api_key: API key for the chosen provider.
            output_dir: Directory where transcripts will be saved.
        """
        if provider_name not in PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider_name}'. Choose from: {list(PROVIDERS.keys())}"
            )

        self.video = VideoSource(video_path)
        self.provider: TranscriptionProvider = PROVIDERS[provider_name](api_key=api_key)
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self) -> dict[str, str]:
        """Run the full pipeline: extract audio -> chunk -> transcribe -> save.

        Returns dict with paths to the generated files.
        """
        print(f"Video: {self.video.video_path}")
        print(f"Provider: {self.provider.name}")
        print(f"Output: {self.output_dir}")
        print()

        # Step 1: Extract audio and split into chunks
        temp_dir = os.path.join(self.output_dir, ".temp_audio")
        print("Step 1: Extracting audio from video...")
        chunks = self.video.extract_and_chunk(
            output_dir=temp_dir,
            max_size_mb=self.provider.max_chunk_size_mb,
        )
        print(f"  Audio extracted: {len(chunks)} chunk(s)\n")

        # Step 2: Transcribe
        print("Step 2: Transcribing audio...")
        result = self.provider.transcribe(chunks)
        print("  Transcription complete.\n")

        # Step 3: Save output files (never overwrite existing)
        print("Step 3: Saving transcripts...")
        transcript_path = unique_path(os.path.join(
            self.output_dir, f"{self.video.name}_transcript.txt"
        ))
        timestamps_path = unique_path(os.path.join(
            self.output_dir, f"{self.video.name}_timestamps.txt"
        ))

        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(result.text)

        with open(timestamps_path, "w", encoding="utf-8") as f:
            f.write(result.timestamped_text)

        print(f"  Saved: {transcript_path}")
        print(f"  Saved: {timestamps_path}")

        return {
            "transcript": transcript_path,
            "timestamps": timestamps_path,
        }
