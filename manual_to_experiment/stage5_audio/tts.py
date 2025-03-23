"""Text-to-speech using Google Cloud TTS."""
import os
from google.cloud import texttospeech


def generate_audio(narration: str, output_path: str, voice_name: str = "en-US-Neural2-F") -> tuple[str, float]:
    """Convert narration text to an MP3 audio file.

    Args:
        narration: The text to speak.
        output_path: Where to save the MP3.
        voice_name: Google TTS voice identifier.

    Returns:
        Tuple of (output_path, duration_seconds).
    """
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=narration)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=voice_name,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0,
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.audio_content)

    # Get duration from the generated file
    from moviepy.editor import AudioFileClip
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()

    return output_path, duration
