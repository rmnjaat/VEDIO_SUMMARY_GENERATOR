"""
Video Transcript Generator
Usage:
    python main.py <video_path> --provider <groq|assemblyai|gemini>
"""

import argparse
import os
import sys

from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Load .env file
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.transcript_generator import TranscriptGenerator

API_KEYS = {
    "groq": os.environ.get("GROQ_API_KEY", ""),
    "assemblyai": os.environ.get("ASSEMBLYAI_API_KEY", ""),
    "gemini": os.environ.get("GEMINI_API_KEY", ""),
}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def main():
    parser = argparse.ArgumentParser(description="Generate transcripts from video lectures")
    parser.add_argument("video", help="Path to the video file")
    parser.add_argument(
        "--provider", "-p",
        required=True,
        choices=["groq", "assemblyai", "gemini"],
        help="Transcription provider to use",
    )
    args = parser.parse_args()

    api_key = API_KEYS.get(args.provider, "")
    if not api_key:
        print(f"Error: No API key found for '{args.provider}'.")
        print(f"Set it in main.py or via environment variable {args.provider.upper()}_API_KEY")
        sys.exit(1)

    generator = TranscriptGenerator(
        video_path=args.video,
        provider_name=args.provider,
        api_key=api_key,
        output_dir=OUTPUT_DIR,
    )

    print("=" * 60)
    print("  VIDEO TRANSCRIPT GENERATOR")
    print("=" * 60)
    print()

    result = generator.generate()

    print()
    print("=" * 60)
    print("  DONE!")
    print(f"  Transcript: {result['transcript']}")
    print(f"  Timestamps: {result['timestamps']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
