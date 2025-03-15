"""
Generate a structured documentation page from a timestamped transcript.

Takes a timestamped transcript (e.g., [00:00:00] some words...) and produces
a clean, structured documentation file in the style of official docs
(like Apache Kafka's documentation pages).

Pipeline: Transcript → Scanner (per chunk, JSON) → Doc Writer (plain text)

Output goes into: output/generated/<title>_doc_<datetime>/

Usage:
    python generate_doc.py <timestamps_file> [--title "Title"] [--duration "04:00:00"]

Example:
    python generate_doc.py output/transcripts/12_timestamps.txt --title "LSM Trees" --duration "04:00:00"
"""

import argparse
import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from personafication.backends import GeminiBackend, GeminiTextBackend
from personafication.pipeline import DocWriterPipeline, load_transcript_as_document

GENERATED_DIR = os.path.join(PROJECT_ROOT, "output", "generated")


def make_run_dir(title: str) -> str:
    """Create a unique run folder: output/generated/<title>_doc_<datetime>/"""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{slug}_doc_{ts}"
    run_dir = os.path.join(GENERATED_DIR, run_name)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate structured documentation from a timestamped transcript"
    )
    parser.add_argument("transcript", help="Path to the timestamped transcript .txt file")
    parser.add_argument("--title", "-t", default=None, help="Title for the document")
    parser.add_argument("--duration", "-d", default=None, help="Total duration (HH:MM:SS)")
    parser.add_argument("--chunk-size", type=int, default=4000, help="Max words per chunk (default: 4000)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to use")
    parser.add_argument("--output-dir", "-o", default=None, help="Override output directory")
    args = parser.parse_args()

    if not os.path.exists(args.transcript):
        print(f"Error: File not found: {args.transcript}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    title = args.title or os.path.splitext(os.path.basename(args.transcript))[0].replace("_", " ").title()

    if args.output_dir:
        run_dir = args.output_dir
        os.makedirs(run_dir, exist_ok=True)
    else:
        run_dir = make_run_dir(title)

    out_path = os.path.join(run_dir, "doc.txt")

    print("=" * 60)
    print("  DOCUMENTATION GENERATOR")
    print("=" * 60)
    print(f"  Transcript : {args.transcript}")
    print(f"  Title      : {title}")
    print(f"  Duration   : {args.duration or 'unknown'}")
    print(f"  Model      : {args.model}")
    print(f"  Chunk size : {args.chunk_size} words")
    print(f"  Run folder : {run_dir}")
    print("=" * 60)
    print()

    doc = load_transcript_as_document(
        transcript_path=args.transcript,
        title=title,
        total_duration=args.duration,
        max_chunk_words=args.chunk_size,
    )
    print(f"Loaded transcript: {len(doc.chunks)} chunk(s)")

    json_backend = GeminiBackend(api_key=api_key, model_name=args.model)
    text_backend = GeminiTextBackend(api_key=api_key, model_name=args.model)

    pipeline = DocWriterPipeline(llm=json_backend, text_llm=text_backend)
    doc_text = pipeline.run(doc)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc_text)

    print()
    print("=" * 60)
    print("  DONE!")
    print(f"  Run folder: {run_dir}")
    print(f"  Output    : {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
