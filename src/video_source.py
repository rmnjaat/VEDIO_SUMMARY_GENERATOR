import os
import subprocess
import math


class VideoSource:
    SUPPORTED_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}

    def __init__(self, video_path: str):
        self.video_path = os.path.abspath(video_path)
        self._validate()

    def _validate(self):
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video not found: {self.video_path}")
        ext = os.path.splitext(self.video_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{ext}'. Supported: {self.SUPPORTED_FORMATS}"
            )

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.video_path))[0]

    def get_duration_seconds(self) -> float:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.video_path,
            ],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())

    def extract_audio(self, output_dir: str, fmt: str = "mp3") -> str:
        """Extract full audio from video. Returns path to audio file."""
        os.makedirs(output_dir, exist_ok=True)
        audio_path = os.path.join(output_dir, f"{self.name}.{fmt}")
        if os.path.exists(audio_path):
            return audio_path
        subprocess.run(
            [
                "ffmpeg", "-i", self.video_path,
                "-vn", "-acodec", "libmp3lame", "-ab", "64k", "-ar", "16000",
                "-ac", "1", "-y", audio_path,
            ],
            capture_output=True, check=True,
        )
        return audio_path

    def extract_and_chunk(self, output_dir: str, max_size_mb: int = 24) -> list[str]:
        """Extract audio and split into chunks under max_size_mb.

        Returns list of chunk file paths in order.
        """
        audio_path = self.extract_audio(output_dir)
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

        if file_size_mb <= max_size_mb:
            return [audio_path]

        # Calculate how many chunks we need
        num_chunks = math.ceil(file_size_mb / max_size_mb)
        duration = self.get_duration_seconds()
        chunk_duration = duration / num_chunks

        chunk_paths = []
        for i in range(num_chunks):
            start = i * chunk_duration
            chunk_path = os.path.join(output_dir, f"{self.name}_chunk_{i:03d}.mp3")
            chunk_paths.append(chunk_path)
            if os.path.exists(chunk_path):
                continue
            subprocess.run(
                [
                    "ffmpeg", "-i", audio_path,
                    "-ss", str(start), "-t", str(chunk_duration),
                    "-acodec", "libmp3lame", "-ab", "64k", "-ar", "16000",
                    "-ac", "1", "-y", chunk_path,
                ],
                capture_output=True, check=True,
            )

        return chunk_paths
