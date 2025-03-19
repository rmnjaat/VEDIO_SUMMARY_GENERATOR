"""
Backend server for Video Summary Generator UI.

Provides REST APIs for:
  GET /api/videos       — list videos in VEID/
  GET /api/transcripts  — list transcript files
  GET /api/outputs      — list all generated output files
  GET /api/file?path=   — serve a file's content for preview

Also serves the frontend at http://localhost:8899/

Usage:
    python backend/server.py
    # or
    python backend/server.py --port 8899
"""

import json
import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file, abort

# Project root = parent of backend/
ROOT = Path(__file__).resolve().parent.parent
VEID_DIR = ROOT / "VEID"
OUTPUT_DIR = ROOT / "output"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
GENERATED_DIR = OUTPUT_DIR / "generated"
FRONTEND_DIR = ROOT / "frontend"

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


# ── Helpers ──────────────────────────────────────────────────

def human_size(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} B"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def safe_relative(path: Path) -> str:
    """Return path relative to ROOT, or abort if outside ROOT."""
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        abort(403)


def read_first_line(fpath: Path) -> str:
    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            return f.readline().strip()[:100]
    except Exception:
        return ""


# ── API: Videos ──────────────────────────────────────────────

@app.route("/api/videos")
def api_videos():
    """Scan VEID/ folder and return list of video files."""
    videos = []
    if VEID_DIR.is_dir():
        for f in sorted(VEID_DIR.iterdir()):
            if f.suffix.lower() in VIDEO_EXTS and f.is_file():
                videos.append({
                    "name": f.name,
                    "size": human_size(f.stat().st_size),
                    "path": f"VEID/{f.name}",
                })
    return jsonify(videos)


# ── API: Transcripts ─────────────────────────────────────────

@app.route("/api/transcripts")
def api_transcripts():
    """Scan output/ and output/transcripts/ for transcript files."""
    transcripts = []
    seen = set()

    for folder, rel_prefix in [(OUTPUT_DIR, "output"), (TRANSCRIPTS_DIR, "output/transcripts")]:
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file() or not f.name.endswith(".txt"):
                continue
            name_lower = f.name.lower()
            if "transcript" not in name_lower and "timestamps" not in name_lower:
                continue
            if "_doc" in name_lower or "_content_tree" in name_lower:
                continue
            key = f.name
            if key in seen:
                continue
            seen.add(key)
            transcripts.append({
                "name": f.name,
                "size": human_size(f.stat().st_size),
                "path": f"{rel_prefix}/{f.name}",
                "subtype": "timestamps" if "timestamps" in name_lower else "plain",
            })

    return jsonify(transcripts)


# ── API: Outputs ─────────────────────────────────────────────

@app.route("/api/outputs")
def api_outputs():
    """Scan all output locations and return categorized file list."""
    files = []

    # output/ root (legacy files)
    if OUTPUT_DIR.is_dir():
        for f in sorted(OUTPUT_DIR.iterdir()):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            size = human_size(f.stat().st_size)
            rel = f"output/{f.name}"
            name_lower = f.name.lower()

            if ext == ".json":
                files.append({"name": f.name, "size": size, "type": "json",
                              "category": "analysis", "desc": f"Analysis: {f.name}", "path": rel})
            elif ext in (".litcoffee", ".md"):
                files.append({"name": f.name, "size": size, "type": "litcoffee",
                              "category": "doc", "desc": f"Doc: {f.name}", "path": rel})
            elif ext == ".txt":
                if "transcript" in name_lower or "timestamps" in name_lower:
                    sub = "timestamps" if "timestamps" in name_lower else "plain"
                    if "_doc" not in name_lower:
                        files.append({"name": f.name, "size": size, "type": "txt",
                                      "category": "transcript", "desc": f"Transcript: {f.name}",
                                      "path": rel, "subtype": sub})
                        continue
                if "_doc" in name_lower:
                    files.append({"name": f.name, "size": size, "type": "txt",
                                  "category": "doc", "desc": f"Documentation: {f.name}", "path": rel})
                else:
                    first = read_first_line(f)
                    files.append({"name": f.name, "size": size, "type": "txt",
                                  "category": "blog", "desc": f"Blog: {first or f.name}", "path": rel})

    # output/generated/ run folders
    if GENERATED_DIR.is_dir():
        for run_dir in sorted(GENERATED_DIR.iterdir()):
            if not run_dir.is_dir():
                continue
            run_name = run_dir.name
            for f in sorted(run_dir.iterdir()):
                if not f.is_file():
                    continue
                ext = f.suffix.lower()
                size = human_size(f.stat().st_size)
                rel = f"output/generated/{run_name}/{f.name}"

                if ext == ".json":
                    files.append({"name": f"{run_name}/{f.name}", "size": size, "type": "json",
                                  "category": "analysis", "desc": f"Analysis: {f.name}", "path": rel})
                elif ext == ".txt":
                    first = read_first_line(f)
                    cat = "blog" if "blog" in run_name else "doc"
                    files.append({"name": f"{run_name}/{f.name}", "size": size, "type": "txt",
                                  "category": cat, "desc": f"{cat.title()}: {first or f.name}", "path": rel})

    # Audio files
    audio_dir = OUTPUT_DIR / ".temp_audio"
    if audio_dir.is_dir():
        for f in sorted(audio_dir.iterdir()):
            if f.suffix.lower() in AUDIO_EXTS and f.is_file():
                files.append({"name": f.name, "size": human_size(f.stat().st_size), "type": "audio",
                              "category": "audio", "desc": f"Audio: {f.name}",
                              "path": f"output/.temp_audio/{f.name}"})

    return jsonify(files)


# ── API: File content ────────────────────────────────────────

@app.route("/api/file")
def api_file():
    """Serve a file for preview. ?path=output/foo.txt"""
    rel_path = request.args.get("path", "")
    if not rel_path:
        abort(400, "Missing ?path= parameter")

    # Security: resolve and ensure it's inside ROOT
    target = (ROOT / rel_path).resolve()
    if not str(target).startswith(str(ROOT.resolve())):
        abort(403, "Access denied")
    if not target.is_file():
        abort(404, "File not found")

    return send_file(target)


# ── Frontend serving ─────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


# Also serve files from project root (for backward compat with output/ paths)
@app.route("/output/<path:subpath>")
def serve_output(subpath):
    return send_from_directory(str(OUTPUT_DIR), subpath)


@app.route("/VEID/<path:subpath>")
def serve_veid(subpath):
    return send_from_directory(str(VEID_DIR), subpath)


# ── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Video Summary Generator UI Server")
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"Serving UI at http://{args.host}:{args.port}")
    print(f"Project root: {ROOT}")
    app.run(host=args.host, port=args.port, debug=False)
