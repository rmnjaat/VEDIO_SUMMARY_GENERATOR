import os
import mlx_whisper
from .base import TranscriptionProvider, TranscriptResult


class MLXProvider(TranscriptionProvider):
    """Local transcription using MLX Whisper on Apple Silicon. No API key needed."""

    MODEL = "mlx-community/whisper-large-v3-mlx"

    def __init__(self, api_key: str = ""):
        # api_key not needed but accepted to match the interface
        pass

    @property
    def name(self) -> str:
        return "mlx"

    @property
    def max_chunk_size_mb(self) -> int:
        return 500  # Local processing, no upload limit — chunk for memory reasons

    def _transcribe_chunk(self, audio_path: str, chunk_offset_sec: float) -> dict:
        """Transcribe a single audio file using MLX Whisper locally."""
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=self.MODEL,
            verbose=True,
        )

        segments = []
        if result.get("segments"):
            for seg in result["segments"]:
                segments.append({
                    "start": seg["start"] + chunk_offset_sec,
                    "end": seg["end"] + chunk_offset_sec,
                    "text": seg["text"],
                })

        return {
            "text": result.get("text", ""),
            "segments": segments,
        }

    def transcribe(self, audio_paths: list[str]) -> TranscriptResult:
        all_text = []
        all_segments = []
        chunk_offset = 0.0

        for i, path in enumerate(audio_paths):
            print(f"  [{self.name}] Transcribing chunk {i + 1}/{len(audio_paths)}: {os.path.basename(path)}")
            result = self._transcribe_chunk(path, chunk_offset)
            all_text.append(result["text"])
            all_segments.extend(result["segments"])

            if result["segments"]:
                chunk_offset = result["segments"][-1]["end"]
            else:
                chunk_offset += self._get_audio_duration(path)

        plain_text = "\n\n".join(all_text)
        timestamped = self._format_timestamps(all_segments)

        return TranscriptResult(text=plain_text, timestamped_text=timestamped)

    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True,
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    @staticmethod
    def _format_timestamps(segments: list[dict]) -> str:
        lines = []
        for seg in segments:
            ts = _seconds_to_hms(seg["start"])
            lines.append(f"[{ts}] {seg['text'].strip()}")
        return "\n".join(lines)


def _seconds_to_hms(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
