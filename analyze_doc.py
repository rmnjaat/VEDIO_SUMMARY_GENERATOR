"""
Analyze a documentation file and build a structured document tree.

Output goes into: output/generated/<title>_doc_analysis_<datetime>/

Usage:
    python analyze_doc.py <doc_file> [--title "Doc Title"]

Example:
    python analyze_doc.py docs/kafka_intro.txt --title "Apache Kafka Introduction"
    python analyze_doc.py docs/kafka_intro.md --title "Apache Kafka Introduction"

Supports: .txt, .md files. For long documents, chunks are created automatically.
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

from personafication.backends import GeminiBackend
from personafication.pipeline import DocAnalysisPipeline, load_document_as_content

GENERATED_DIR = os.path.join(PROJECT_ROOT, "output", "generated")


def make_run_dir(title: str) -> str:
    """Create a unique run folder: output/generated/<title>_doc_analysis_<datetime>/"""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"{slug}_doc_analysis_{ts}"
    run_dir = os.path.join(GENERATED_DIR, run_name)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def main():
    parser = argparse.ArgumentParser(description="Analyze documentation into a structured document tree")
    parser.add_argument("document", help="Path to the document file (.txt or .md)")
    parser.add_argument("--title", "-t", default=None, help="Title for the document")
    parser.add_argument("--chunk-size", type=int, default=4000, help="Max words per chunk (default: 4000)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to use")
    parser.add_argument("--output-dir", "-o", default=None, help="Override output directory")
    args = parser.parse_args()

    if not os.path.exists(args.document):
        print(f"Error: File not found: {args.document}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: GEMINI_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    title = args.title or os.path.splitext(os.path.basename(args.document))[0].replace("_", " ").title()

    if args.output_dir:
        run_dir = args.output_dir
        os.makedirs(run_dir, exist_ok=True)
    else:
        run_dir = make_run_dir(title)

    out_path = os.path.join(run_dir, "doc_tree.json")

    print("=" * 60)
    print("  DOCUMENTATION ANALYZER")
    print("=" * 60)
    print(f"  Document   : {args.document}")
    print(f"  Title      : {title}")
    print(f"  Model      : {args.model}")
    print(f"  Chunk size : {args.chunk_size} words")
    print(f"  Run folder : {run_dir}")
    print("=" * 60)
    print()

    doc = load_document_as_content(
        doc_path=args.document,
        title=title,
        max_chunk_words=args.chunk_size,
    )
    print(f"Loaded document: {len(doc.chunks)} chunk(s)")

    backend = GeminiBackend(api_key=api_key, model_name=args.model)
    pipeline = DocAnalysisPipeline(llm=backend)
    doc_tree = pipeline.run(doc)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc_tree, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print("  DONE!")
    print(f"  Run folder: {run_dir}")
    print(f"  Output    : {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
