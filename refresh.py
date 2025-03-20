"""
Scan project folders and write manifests so viewer.html stays up to date.

Run this before opening the viewer, or after adding new videos/running pipelines:
    python refresh.py

It writes:
  VEID/manifest.json           — list of videos
  output/transcripts.json      — list of transcript files
  output/outputs.json          — list of all output files (blogs, docs, json, audio)
"""

import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
VEID_DIR = os.path.join(ROOT, "VEID")
OUTPUT_DIR = os.path.join(ROOT, "output")
TRANSCRIPTS_DIR = os.path.join(OUTPUT_DIR, "transcripts")
GENERATED_DIR = os.path.join(OUTPUT_DIR, "generated")

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def human_size(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}" if unit != "B" else f"{nbytes} B"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def scan_videos():
    """Scan VEID/ for video files."""
    videos = []
    if not os.path.isdir(VEID_DIR):
        return videos
    for fname in sorted(os.listdir(VEID_DIR)):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in VIDEO_EXTS:
            continue
        fpath = os.path.join(VEID_DIR, fname)
        size = os.path.getsize(fpath)
        videos.append({
            "name": fname,
            "size": human_size(size),
            "path": f"VEID/{fname}",
        })
    return videos


def scan_transcripts():
    """Scan output/ and output/transcripts/ for transcript .txt files."""
    transcripts = []
    # Check both old (output/) and new (output/transcripts/) locations
    # Only include files that are actual transcripts (contain "transcript" or "timestamps" in name)
    for folder, rel_prefix in [(OUTPUT_DIR, "output"), (TRANSCRIPTS_DIR, "output/transcripts")]:
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.endswith(".txt"):
                continue
            # Only pick up transcript/timestamps files, not blogs/docs/analysis
            name_lower = fname.lower()
            if "transcript" not in name_lower and "timestamps" not in name_lower:
                continue
            # Exclude generated docs/trees that happen to have "timestamps" in the name
            if "_doc" in name_lower or "_content_tree" in name_lower:
                continue
            fpath = os.path.join(folder, fname)
            if not os.path.isfile(fpath):
                continue
            size = os.path.getsize(fpath)
            is_timestamps = "timestamps" in name_lower
            transcripts.append({
                "name": fname,
                "size": human_size(size),
                "path": f"{rel_prefix}/{fname}",
                "subtype": "timestamps" if is_timestamps else "plain",
            })
    return transcripts


def scan_outputs():
    """Scan output/ for all generated files (blogs, docs, json, audio)."""
    files = []

    # Scan output/ root for legacy files
    if os.path.isdir(OUTPUT_DIR):
        for fname in sorted(os.listdir(OUTPUT_DIR)):
            fpath = os.path.join(OUTPUT_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            size = os.path.getsize(fpath)

            if ext == ".json":
                files.append({"name": fname, "size": human_size(size), "type": "json", "category": "analysis", "desc": f"Analysis: {fname}", "path": f"output/{fname}"})
            elif ext == ".txt" and "doc" in fname:
                files.append({"name": fname, "size": human_size(size), "type": "txt", "category": "doc", "desc": f"Documentation: {fname}", "path": f"output/{fname}"})
            elif ext == ".txt" and ("transcript" not in fname and "timestamps" not in fname):
                # Blog or other generated text
                first_line = ""
                try:
                    with open(fpath, "r") as f:
                        first_line = f.readline().strip()[:80]
                except Exception:
                    pass
                files.append({"name": fname, "size": human_size(size), "type": "txt", "category": "blog", "desc": f"Blog: {first_line or fname}", "path": f"output/{fname}"})
            elif ext in (".litcoffee", ".md"):
                files.append({"name": fname, "size": human_size(size), "type": "litcoffee", "category": "doc", "desc": f"Doc: {fname}", "path": f"output/{fname}"})

    # Scan output/generated/ run folders
    if os.path.isdir(GENERATED_DIR):
        for run_name in sorted(os.listdir(GENERATED_DIR)):
            run_dir = os.path.join(GENERATED_DIR, run_name)
            if not os.path.isdir(run_dir):
                continue
            for fname in sorted(os.listdir(run_dir)):
                fpath = os.path.join(run_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                ext = os.path.splitext(fname)[1].lower()
                size = os.path.getsize(fpath)
                rel_path = f"output/generated/{run_name}/{fname}"

                if ext == ".json":
                    files.append({"name": f"{run_name}/{fname}", "size": human_size(size), "type": "json", "category": "analysis", "desc": f"Analysis: {fname}", "path": rel_path})
                elif ext == ".txt":
                    first_line = ""
                    try:
                        with open(fpath, "r") as f:
                            first_line = f.readline().strip()[:80]
                    except Exception:
                        pass
                    cat = "blog" if "blog" in run_name else "doc"
                    files.append({"name": f"{run_name}/{fname}", "size": human_size(size), "type": "txt", "category": cat, "desc": f"{cat.title()}: {first_line or fname}", "path": rel_path})

    # Scan audio files
    audio_dir = os.path.join(OUTPUT_DIR, ".temp_audio")
    if os.path.isdir(audio_dir):
        for fname in sorted(os.listdir(audio_dir)):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in AUDIO_EXTS:
                continue
            fpath = os.path.join(audio_dir, fname)
            size = os.path.getsize(fpath)
            files.append({"name": fname, "size": human_size(size), "type": "audio", "category": "audio", "desc": f"Audio: {fname}", "path": f"output/.temp_audio/{fname}"})

    return files


def main():
    # Videos
    videos = scan_videos()
    veid_manifest = os.path.join(VEID_DIR, "manifest.json")
    os.makedirs(VEID_DIR, exist_ok=True)
    with open(veid_manifest, "w") as f:
        json.dump(videos, f, indent=2)
    print(f"Videos: {len(videos)} found -> VEID/manifest.json")

    # Transcripts
    transcripts = scan_transcripts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "transcripts.json"), "w") as f:
        json.dump(transcripts, f, indent=2)
    print(f"Transcripts: {len(transcripts)} found -> output/transcripts.json")

    # All outputs
    outputs = scan_outputs()
    with open(os.path.join(OUTPUT_DIR, "outputs.json"), "w") as f:
        json.dump(outputs, f, indent=2)
    print(f"Outputs: {len(outputs)} found -> output/outputs.json")

    print("Done. Refresh viewer.html in your browser.")


if __name__ == "__main__":
    main()
