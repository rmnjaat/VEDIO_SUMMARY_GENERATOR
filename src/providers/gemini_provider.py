import os
import time
import google.generativeai as genai
from .base import TranscriptionProvider, TranscriptResult


class GeminiProvider(TranscriptionProvider):

    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def max_chunk_size_mb(self) -> int:
        return 2000  # Gemini supports large uploads via File API

    def _upload_file(self, audio_path: str) -> genai.types.File:
        """Upload audio to Gemini File API and wait until it's processed."""
        print(f"  [{self.name}] Uploading {os.path.basename(audio_path)}...")
        uploaded = genai.upload_file(path=audio_path)

        # Poll until file is ACTIVE
        while uploaded.state.name == "PROCESSING":
            time.sleep(5)
            uploaded = genai.get_file(uploaded.name)

        if uploaded.state.name == "FAILED":
            raise RuntimeError(f"Gemini file upload failed for {audio_path}")

        return uploaded

    def _transcribe_chunk(self, audio_path: str, chunk_index: int) -> dict:
        """Transcribe a single audio file via Gemini."""
        uploaded_file = self._upload_file(audio_path)

        prompt = (
            "Generate a complete word-for-word transcript of this audio. "
            "Include timestamps in [HH:MM:SS] format every 2-3 minutes. "
            "Output ONLY the transcript text with timestamps, nothing else."
        )

        print(f"  [{self.name}] Transcribing chunk {chunk_index + 1}...")
        response = self.model.generate_content([uploaded_file, prompt])

        # Clean up uploaded file
        try:
            genai.delete_file(uploaded_file.name)
        except Exception:
            pass

        return response.text

    def transcribe(self, audio_paths: list[str]) -> TranscriptResult:
        all_raw = []

        for i, path in enumerate(audio_paths):
            print(f"  [{self.name}] Processing chunk {i + 1}/{len(audio_paths)}: {os.path.basename(path)}")
            raw_text = self._transcribe_chunk(path, i)
            all_raw.append(raw_text)

        full_text = "\n\n".join(all_raw)

        # Gemini returns timestamps inline, so both outputs are the same
        # Strip timestamps for the plain version
        plain_lines = []
        for line in full_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and "]" in stripped:
                # Remove [HH:MM:SS] prefix
                after_bracket = stripped.index("]") + 1
                plain_lines.append(stripped[after_bracket:].strip())
            else:
                plain_lines.append(stripped)

        plain_text = "\n".join(plain_lines)

        return TranscriptResult(text=plain_text, timestamped_text=full_text)
