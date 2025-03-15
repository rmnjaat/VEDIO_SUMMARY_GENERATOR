"""
Analyze a transcript — choose which pipeline to run.

Modes:
  tree  → Scanner + Architect → structured JSON content tree
  doc   → Scanner + Doc Writer → plain-text documentation page (Kafka-style)
  blog  → Scanner + Topic Splitter + Section Writer + Finalizer
           → comprehensive blog post(s), one per major topic

Output goes into: output/generated/<title>_<mode>_<datetime>/

Usage:
    python analyze.py <transcript_file> --mode tree
    python analyze.py <transcript_file> --mode doc
    python analyze.py <transcript_file> --mode blog

Examples:
    python analyze.py output/transcripts/12_timestamps.txt --mode tree --title "LSM Trees" --duration "04:00:00"
    python analyze.py output/transcripts/12_timestamps.txt --mode blog --title "LSM Trees" --duration "04:00:00"
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from personafication.backends import GeminiBackend, GeminiTextBackend
from personafication.pipeline import (
    AnalysisPipeline,
    DocWriterPipeline,
    BlogWriterPipeline,
    load_transcript_as_document,
)

GENERATED_DIR = os.path.join(PROJECT_ROOT, "output", "generated")
MANIFEST_PATH = os.path.join(GENERATED_DIR, "manifest.json")


def update_manifest(run_dir: str, saved_files: list[dict]):
    """Append new files to output/generated/manifest.json for the viewer."""
    manifest = []
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, IOError):
            manifest = []

    manifest.extend(saved_files)

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def make_run_dir(title: str, mode: str) -> str:
    """Create a unique run folder: output/generated/<title>_<mode>_<datetime>/"""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{slug}_{mode}_{ts}"
    run_dir = os.path.join(GENERATED_DIR, run_name)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def unique_path(path: str) -> str:
    """If *path* already exists, append _1, _2, … before the extension."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


def main():
    parser = argparse.ArgumentParser(description="Analyze a transcript into structured output")
    parser.add_argument("transcript", help="Path to the transcript .txt file")
    parser.add_argument(
        "--mode", "-m",
        choices=["tree", "doc", "blog"],
        required=True,
        help="'tree' = JSON content tree, 'doc' = plain-text doc page, "
             "'blog' = comprehensive blog post(s) split by topic",
    )
    parser.add_argument("--title", "-t", default=None, help="Title for the content")
    parser.add_argument("--duration", "-d", default=None, help="Total duration (HH:MM:SS)")
    parser.add_argument("--chunk-size", type=int, default=4000, help="Max words per chunk (default: 4000)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to use")
    parser.add_argument("--output-dir", "-o", default=None, help="Override output directory (default: auto-created run folder)")
    args = parser.parse_args()

    if not os.path.exists(args.transcript):
        print(f"Error: File not found: {args.transcript}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    title = args.title or os.path.splitext(os.path.basename(args.transcript))[0].replace("_", " ").title()

    # Create run directory
    if args.output_dir:
        run_dir = args.output_dir
        os.makedirs(run_dir, exist_ok=True)
    else:
        run_dir = make_run_dir(title, args.mode)

    mode_labels = {"tree": "CONTENT TREE (JSON)", "doc": "DOCUMENTATION (TXT)", "blog": "BLOG POST(S)"}
    mode_label = mode_labels[args.mode]

    print("=" * 60)
    print(f"  TRANSCRIPT ANALYZER — {mode_label}")
    print("=" * 60)
    print(f"  Transcript : {args.transcript}")
    print(f"  Mode       : {args.mode}")
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

    run_folder_rel = os.path.relpath(run_dir, PROJECT_ROOT)

    if args.mode == "tree":
        pipeline = AnalysisPipeline(llm=json_backend)
        result = pipeline.run(doc, save_dir=run_dir)
        out_path = os.path.join(run_dir, "content_tree.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        update_manifest(run_dir, [{
            "name": "content_tree.json",
            "type": "json",
            "category": "analysis",
            "desc": f"Content tree — {title}",
            "path": f"{run_folder_rel}/content_tree.json",
        }])

        print()
        print("=" * 60)
        print("  DONE!")
        print(f"  Run folder: {run_dir}")
        print(f"  Output    : {out_path}")
        print("=" * 60)

    elif args.mode == "doc":
        text_backend = GeminiTextBackend(api_key=api_key, model_name=args.model)
        pipeline = DocWriterPipeline(llm=json_backend, text_llm=text_backend)
        result = pipeline.run(doc, save_dir=run_dir)
        out_path = os.path.join(run_dir, "doc.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(result)

        update_manifest(run_dir, [{
            "name": "doc.txt",
            "type": "txt",
            "category": "doc",
            "desc": f"Documentation — {title}",
            "path": f"{run_folder_rel}/doc.txt",
        }])

        print()
        print("=" * 60)
        print("  DONE!")
        print(f"  Run folder: {run_dir}")
        print(f"  Output    : {out_path}")
        print("=" * 60)

    else:  # blog
        text_backend = GeminiTextBackend(api_key=api_key, model_name=args.model)
        pipeline = BlogWriterPipeline(llm=json_backend, text_llm=text_backend)
        results = pipeline.run(doc, save_dir=run_dir)

        saved_paths = []
        manifest_entries = []
        for slug, content in results:
            fname = f"{slug}.txt"
            out_path = os.path.join(run_dir, fname)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            saved_paths.append(out_path)
            # Extract title from first line of content for the manifest desc
            first_line = content.split('\n', 1)[0].strip() or slug
            manifest_entries.append({
                "name": fname,
                "type": "txt",
                "category": "blog",
                "desc": f"Blog: {first_line}",
                "path": f"{run_folder_rel}/{fname}",
            })

        update_manifest(run_dir, manifest_entries)

        print()
        print("=" * 60)
        print("  DONE!")
        print(f"  Run folder: {run_dir}")
        print(f"  Generated {len(saved_paths)} file(s):")
        for p in saved_paths:
            print(f"    - {os.path.basename(p)}")
        print("=" * 60)


if __name__ == "__main__":
    main()
