import os
from groq import Groq
from .base import TranscriptionProvider, TranscriptResult


class GroqProvider(TranscriptionProvider):

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    @property
    def name(self) -> str:
        return "groq"

    @property
    def max_chunk_size_mb(self) -> int:
        return 24  # Groq limit is 25MB, keep 1MB buffer

    def _transcribe_chunk(self, audio_path: str, chunk_index: int, chunk_offset_sec: float) -> dict:
        """Transcribe a single audio chunk. Returns dict with text and segments."""
        with open(audio_path, "rb") as f:
            response = self.client.audio.transcriptions.create(
                file=(os.path.basename(audio_path), f.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
                language="en",
            )

        segments = []
        if hasattr(response, "segments") and response.segments:
            for seg in response.segments:
                segments.append({
                    "start": seg["start"] + chunk_offset_sec,
                    "end": seg["end"] + chunk_offset_sec,
                    "text": seg["text"],
                })

        return {
            "text": response.text,
            "segments": segments,
        }

    def transcribe(self, audio_paths: list[str]) -> TranscriptResult:
        all_text = []
        all_segments = []
        chunk_offset = 0.0

        for i, path in enumerate(audio_paths):
            print(f"  [{self.name}] Transcribing chunk {i + 1}/{len(audio_paths)}: {os.path.basename(path)}")
            result = self._transcribe_chunk(path, i, chunk_offset)
            all_text.append(result["text"])
            all_segments.extend(result["segments"])

            # Estimate offset for next chunk from segments
            if result["segments"]:
                chunk_offset = result["segments"][-1]["end"]

        plain_text = "\n\n".join(all_text)
        timestamped = self._format_timestamps(all_segments)

        return TranscriptResult(text=plain_text, timestamped_text=timestamped)

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
