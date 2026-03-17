import os
import re
import time
from groq import Groq, RateLimitError
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

    def _transcribe_chunk_with_retry(self, audio_path: str, chunk_index: int, chunk_offset_sec: float, max_retries: int = 5) -> dict:
        """Retry transcription if rate-limited, waiting the time Groq tells us."""
        for attempt in range(max_retries):
            try:
                return self._transcribe_chunk(audio_path, chunk_index, chunk_offset_sec)
            except RateLimitError as e:
                wait_seconds = self._parse_wait_time(str(e))
                if attempt == max_retries - 1:
                    raise
                print(f"  [{self.name}] Rate limited. Waiting {wait_seconds}s before retry (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait_seconds)

    @staticmethod
    def _parse_wait_time(error_message: str) -> int:
        """Extract wait time from Groq rate limit error message."""
        # Matches patterns like "16m45.5s" or "45.5s" or "2m"
        match = re.search(r"try again in (?:(\d+)m)?(\d+(?:\.\d+)?)?s?", error_message)
        if match:
            minutes = int(match.group(1) or 0)
            seconds = float(match.group(2) or 0)
            return int(minutes * 60 + seconds) + 10  # add 10s buffer
        return 120  # default 2 min wait if can't parse

    def transcribe(self, audio_paths: list[str], cache_dir: str = None) -> TranscriptResult:
        all_text = []
        all_segments = []
        chunk_offset = 0.0

        for i, path in enumerate(audio_paths):
            # Check for cached result from a previous run
            cached = self._load_cached_chunk(path, cache_dir)
            if cached:
                print(f"  [{self.name}] Chunk {i + 1}/{len(audio_paths)}: {os.path.basename(path)} (cached)")
                result = cached
            else:
                print(f"  [{self.name}] Transcribing chunk {i + 1}/{len(audio_paths)}: {os.path.basename(path)}")
                result = self._transcribe_chunk_with_retry(path, i, chunk_offset)
                self._save_cached_chunk(path, result, cache_dir)

            all_text.append(result["text"])
            all_segments.extend(result["segments"])

            # Use chunk duration from audio file for offset if no segments
            if result["segments"]:
                chunk_offset = result["segments"][-1]["end"]
            else:
                chunk_offset += self._get_audio_duration(path)

        plain_text = "\n\n".join(all_text)
        timestamped = self._format_timestamps(all_segments)

        return TranscriptResult(text=plain_text, timestamped_text=timestamped)

    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        """Get duration of an audio file using ffprobe."""
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
    def _load_cached_chunk(audio_path: str, cache_dir: str) -> dict | None:
        """Load a previously transcribed chunk result from cache."""
        if not cache_dir:
            cache_dir = os.path.dirname(audio_path)
        import json
        cache_file = os.path.join(cache_dir, os.path.basename(audio_path) + ".cache.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                return json.load(f)
        return None

    @staticmethod
    def _save_cached_chunk(audio_path: str, result: dict, cache_dir: str):
        """Save a transcribed chunk result to cache."""
        if not cache_dir:
            cache_dir = os.path.dirname(audio_path)
        import json
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, os.path.basename(audio_path) + ".cache.json")
        with open(cache_file, "w") as f:
            json.dump(result, f)

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
