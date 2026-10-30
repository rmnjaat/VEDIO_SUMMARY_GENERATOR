"""Text-to-speech using Coqui XTTS v2 (local, free, voice cloning)."""
import os
import wave
import struct

from TTS.api import TTS

# Singleton — model loads once, reused for all scenes
_tts_instance: TTS | None = None
_DEFAULT_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"

# Default reference voice (ships with the project)
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
_DEFAULT_VOICE = os.path.join(_ASSETS_DIR, "reference_voice.wav")


def _get_tts() -> TTS:
    """Load the XTTS v2 model (downloads ~2GB on first run)."""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTS(_DEFAULT_MODEL)
    return _tts_instance


def _get_wav_duration(path: str) -> float:
    """Read the duration of a .wav file in seconds."""
    with wave.open(path, "r") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def _split_into_sentences(text: str, max_chars: int = 230) -> list[str]:
    """Split long text into sentence-sized chunks for better XTTS quality."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) < max_chars:
            current = (current + " " + sent).strip()
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks if chunks else [text]


def generate_audio(
    narration: str,
    output_path: str,
    reference_voice: str | None = None,
    language: str = "en",
) -> tuple[str, float]:
    """Generate speech audio from narration text using XTTS v2.

    For long narrations (>230 chars), splits into sentences, generates
    each separately, then concatenates for better quality.

    Args:
        narration: The text to speak.
        output_path: Where to save the .wav file.
        reference_voice: Path to a reference .wav (3-10 sec) for voice cloning.
                         Falls back to default if not provided.
        language: Language code (default "en").

    Returns:
        Tuple of (output_path, duration_seconds).
    """
    tts = _get_tts()

    speaker_wav = reference_voice or _DEFAULT_VOICE
    if not os.path.exists(speaker_wav):
        raise FileNotFoundError(
            f"Reference voice not found: {speaker_wav}\n"
            f"Place a 3-10 second .wav file at: {_DEFAULT_VOICE}"
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Split long text for better quality
    chunks = _split_into_sentences(narration)

    if len(chunks) == 1:
        # Single chunk — generate directly
        tts.tts_to_file(
            text=narration,
            speaker_wav=speaker_wav,
            language=language,
            file_path=output_path,
        )
    else:
        # Multiple chunks — generate each, concatenate raw WAV data
        temp_paths = []
        for i, chunk in enumerate(chunks):
            temp_path = output_path.replace(".wav", f"_chunk{i}.wav")
            tts.tts_to_file(
                text=chunk,
                speaker_wav=speaker_wav,
                language=language,
                file_path=temp_path,
            )
            temp_paths.append(temp_path)

        _concatenate_wavs(temp_paths, output_path)

        # Cleanup temp chunks
        for tp in temp_paths:
            if os.path.exists(tp):
                os.unlink(tp)

    duration = _get_wav_duration(output_path)
    return output_path, duration


def _concatenate_wavs(input_paths: list[str], output_path: str):
    """Concatenate multiple WAV files into one."""
    if not input_paths:
        return

    # Read first file to get params
    with wave.open(input_paths[0], "r") as first:
        params = first.getparams()
        all_frames = first.readframes(first.getnframes())

    # Append remaining files
    for path in input_paths[1:]:
        with wave.open(path, "r") as wf:
            all_frames += wf.readframes(wf.getnframes())

    # Write concatenated output
    with wave.open(output_path, "w") as out:
        out.setparams(params)
        out.writeframes(all_frames)
