import assemblyai as aai
from .base import TranscriptionProvider, TranscriptResult


class AssemblyAIProvider(TranscriptionProvider):

    def __init__(self, api_key: str):
        aai.settings.api_key = api_key

    @property
    def name(self) -> str:
        return "assemblyai"

    @property
    def max_chunk_size_mb(self) -> int:
        return 2200  # AssemblyAI supports up to ~2.2GB uploads, so no chunking needed

    def transcribe(self, audio_paths: list[str]) -> TranscriptResult:
        """AssemblyAI handles large files natively, so we use only the first
        (full) audio file. If chunks were created, we transcribe each and merge."""
        all_text = []
        all_utterances = []

        for i, path in enumerate(audio_paths):
            print(f"  [{self.name}] Transcribing chunk {i + 1}/{len(audio_paths)}: {path}")
            config = aai.TranscriptionConfig(
                speech_models=["universal-3-pro", "universal-2"],
                language_detection=True,
            )
            transcript = aai.Transcriber(config=config).transcribe(path)

            if transcript.status == "error":
                raise RuntimeError(f"Transcription failed: {transcript.error}")

            all_text.append(transcript.text)

            if transcript.words:
                all_utterances.extend(transcript.words)

        plain_text = "\n\n".join(all_text)
        timestamped = self._format_timestamps(all_utterances)

        return TranscriptResult(text=plain_text, timestamped_text=timestamped)

    @staticmethod
    def _format_timestamps(words: list) -> str:
        if not words:
            return ""

        lines = []
        current_line_words = []
        current_start = None
        last_end = 0

        for word in words:
            start_ms = word.start
            if current_start is None:
                current_start = start_ms

            current_line_words.append(word.text)

            # Group into ~30-second blocks for readable timestamps
            if (start_ms - current_start) >= 30_000 and len(current_line_words) > 0:
                ts = _ms_to_hms(current_start)
                lines.append(f"[{ts}] {' '.join(current_line_words)}")
                current_line_words = []
                current_start = None

        # Flush remaining
        if current_line_words and current_start is not None:
            ts = _ms_to_hms(current_start)
            lines.append(f"[{ts}] {' '.join(current_line_words)}")

        return "\n".join(lines)


def _ms_to_hms(ms: int) -> str:
    seconds = ms / 1000
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
