#!/bin/bash

# Generate commit history for manual_to_experiment between March 20-25, 2025
# Usage: bash generate_commit_history.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# ── Helper: create a commit with a specific date ──
make_commit() {
    local date="$1"
    local msg="$2"
    shift 2
    # Stage all passed files
    for f in "$@"; do
        git add "$f"
    done
    GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -m "$msg"
}

echo "=== Generating commit history (March 20-25) ==="

# ─────────────────── March 20 ───────────────────

# 1. Project scaffold
mkdir -p manual_to_experiment/stage1_ingestion
mkdir -p manual_to_experiment/stage2_extraction
mkdir -p manual_to_experiment/stage3_script

cat > manual_to_experiment/requirements.txt << 'EOF'
google-generativeai>=0.8.0
google-cloud-texttospeech
httpx>=0.27.0
moviepy>=1.0.3
Pillow>=10.0.0
python-dotenv>=1.0.0
streamlit>=1.35.0
EOF

cat > manual_to_experiment/PLAN.md << 'EOF'
# Plan: Manual to Instruction Video

## Stage 1 — Ingestion
- Accept PDF upload or URL
- Upload PDF to Gemini via File API
- Fetch URL content with httpx

## Stage 2 — Extraction
- Send content + extraction prompt to Gemini
- Parse structured JSON response
- Validate sections/steps schema

## Stage 3 — Script Generation
- Send structured data + script prompt to Gemini
- Get scene-by-scene script with narration + visual hints
EOF

cat > manual_to_experiment/__init__.py << 'EOF'
EOF

cat > manual_to_experiment/stage1_ingestion/__init__.py << 'EOF'
EOF

cat > manual_to_experiment/stage2_extraction/__init__.py << 'EOF'
EOF

cat > manual_to_experiment/stage3_script/__init__.py << 'EOF'
EOF

make_commit "2025-03-20 11:15:00 +0530" "scaffold manual_to_experiment project with stage directories and plan" \
    manual_to_experiment/requirements.txt \
    manual_to_experiment/PLAN.md \
    manual_to_experiment/__init__.py \
    manual_to_experiment/stage1_ingestion/__init__.py \
    manual_to_experiment/stage2_extraction/__init__.py \
    manual_to_experiment/stage3_script/__init__.py

# 2. Stage 1 ingestion modules
cat > manual_to_experiment/stage1_ingestion/detector.py << 'PYEOF'
"""Detect whether the user input is a PDF file, URL, or plain text."""
import os


def detect_input_type(source: str) -> str:
    if os.path.isfile(source) and source.lower().endswith(".pdf"):
        return "pdf"
    if source.startswith("http://") or source.startswith("https://"):
        return "url"
    return "text"
PYEOF

cat > manual_to_experiment/stage1_ingestion/pdf_uploader.py << 'PYEOF'
"""Upload a PDF to Google Gemini via the File API."""
import google.generativeai as genai


def upload_pdf_to_gemini(pdf_path: str):
    """Upload PDF and return a Gemini file object for use in prompts."""
    gemini_file = genai.upload_file(pdf_path, mime_type="application/pdf")
    return gemini_file
PYEOF

cat > manual_to_experiment/stage1_ingestion/url_fetcher.py << 'PYEOF'
"""Fetch the HTML content of a URL."""
import httpx


def fetch_url_html(url: str, timeout: int = 30) -> str:
    """GET request and return the HTML body as a string."""
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text
PYEOF

make_commit "2025-03-20 14:30:00 +0530" "add stage 1 ingestion: input detector, pdf uploader, url fetcher" \
    manual_to_experiment/stage1_ingestion/detector.py \
    manual_to_experiment/stage1_ingestion/pdf_uploader.py \
    manual_to_experiment/stage1_ingestion/url_fetcher.py

# ─────────────────── March 21 ───────────────────

# 3. Stage 2 extraction
cat > manual_to_experiment/stage2_extraction/prompts.py << 'PYEOF'
"""Prompts for the extraction stage."""

EXTRACTION_PROMPT = """You are analyzing a product manual. Extract the following structured data as JSON:

{
  "product_name": "...",
  "sections": [
    {
      "title": "Section title",
      "type": "setup|usage|maintenance|safety",
      "steps": [
        {
          "step_number": 1,
          "title": "Short step title",
          "description": "Detailed description of what to do",
          "warning": "Any safety warning or null",
          "image_hint": "Description of any diagram/image shown for this step"
        }
      ]
    }
  ]
}

Rules:
- Extract EVERY actionable step from the manual
- Include image_hint only if there is a relevant diagram on the page
- Preserve the order as it appears in the manual
- Mark warnings from caution/warning boxes
- Return valid JSON only, no markdown
"""
PYEOF

cat > manual_to_experiment/stage2_extraction/extractor.py << 'PYEOF'
"""Extract structured data from manual content using Gemini."""
import json
import google.generativeai as genai
from .prompts import EXTRACTION_PROMPT


def extract_structure(content, metadata: dict) -> dict:
    """Send content to Gemini and parse the structured extraction.

    Args:
        content: Either a Gemini file object (PDF), HTML string, or plain text.
        metadata: Dict with product_name, brand, model fields.

    Returns:
        Parsed JSON dict with sections and steps.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")

    context = f"Product: {metadata.get('product_name', 'Unknown')}"
    context += f"\nBrand: {metadata.get('brand', '')}"
    context += f"\nModel: {metadata.get('model', '')}"

    response = model.generate_content([
        content,
        f"{context}\n\n{EXTRACTION_PROMPT}"
    ])

    raw = response.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
PYEOF

cat > manual_to_experiment/stage2_extraction/validator.py << 'PYEOF'
"""Validate the extracted structure against expected schema."""


def validate_structure(data: dict) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors = []

    if "sections" not in data:
        errors.append("Missing 'sections' key")
        return errors

    for i, section in enumerate(data["sections"]):
        if "title" not in section:
            errors.append(f"Section {i}: missing title")
        if "steps" not in section:
            errors.append(f"Section {i}: missing steps")
            continue
        for j, step in enumerate(section["steps"]):
            if "description" not in step:
                errors.append(f"Section {i}, Step {j}: missing description")

    return errors
PYEOF

make_commit "2025-03-21 10:00:00 +0530" "add stage 2 extraction: prompt, extractor, and json validator" \
    manual_to_experiment/stage2_extraction/prompts.py \
    manual_to_experiment/stage2_extraction/extractor.py \
    manual_to_experiment/stage2_extraction/validator.py

# 4. Stage 3 script generation
cat > manual_to_experiment/stage3_script/prompts.py << 'PYEOF'
"""Prompts for scene script generation."""

SCRIPT_PROMPT = """You are a video script writer. Given structured manual data, produce a scene-by-scene script as a JSON array.

Each scene object:
{
  "scene_id": 0,
  "type": "intro|step|warning|outro",
  "narration": "What the narrator says (conversational, clear)",
  "visual_hint": "Detailed description for image generation",
  "estimated_duration_sec": 8
}

Rules:
- Start with an intro scene (greet viewer, state product name)
- One scene per step (combine very short steps if needed)
- Add a dedicated warning scene for any safety warnings
- End with an outro scene
- Narration should be conversational, 2nd person ("you")
- visual_hint must be specific enough for image generation
- estimated_duration_sec = word_count / 2.2 (rounded up)
- Return valid JSON array only
"""
PYEOF

cat > manual_to_experiment/stage3_script/generator.py << 'PYEOF'
"""Generate a video scene script from structured data."""
import json
import google.generativeai as genai
from .prompts import SCRIPT_PROMPT


def generate_script(structure: dict, metadata: dict) -> list[dict]:
    """Generate scene-by-scene video script.

    Args:
        structure: Output from stage 2 extraction.
        metadata: Product name, brand, model.

    Returns:
        List of scene dicts.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")

    context = f"Product: {metadata.get('product_name', 'Unknown')}"
    context += f"\nBrand: {metadata.get('brand', '')}"
    context += f"\nModel: {metadata.get('model', '')}"

    input_json = json.dumps(structure, indent=2)

    response = model.generate_content(
        f"{context}\n\nStructured data:\n{input_json}\n\n{SCRIPT_PROMPT}"
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
PYEOF

make_commit "2025-03-21 15:45:00 +0530" "add stage 3 script generation with scene prompts and generator" \
    manual_to_experiment/stage3_script/prompts.py \
    manual_to_experiment/stage3_script/generator.py

# ─────────────────── March 22 ───────────────────

# 5. Pipeline orchestrator
cat > manual_to_experiment/pipeline.py << 'PYEOF'
"""Pipeline orchestrator — runs stages 1 through 3 in sequence."""
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

from stage1_ingestion.detector import detect_input_type
from stage1_ingestion.pdf_uploader import upload_pdf_to_gemini
from stage1_ingestion.url_fetcher import fetch_url_html
from stage2_extraction.extractor import extract_structure
from stage2_extraction.validator import validate_structure
from stage3_script.generator import generate_script

load_dotenv()


def run_pipeline(source: str, metadata: dict, output_dir: str = "outputs"):
    """Run the full extraction-to-script pipeline.

    Args:
        source: Path to PDF, URL, or plain text.
        metadata: Dict with product_name, brand, model.
        output_dir: Where to save intermediate JSON files.
    """
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    os.makedirs(output_dir, exist_ok=True)

    # ── Stage 1: Ingestion ──
    input_type = detect_input_type(source)
    print(f"[Stage 1] Input type: {input_type}")

    if input_type == "pdf":
        content = upload_pdf_to_gemini(source)
    elif input_type == "url":
        content = fetch_url_html(source)
    else:
        content = source

    print("[Stage 1] Done")

    # ── Stage 2: Extraction ──
    print("[Stage 2] Extracting structure...")
    structure = extract_structure(content, metadata)

    errors = validate_structure(structure)
    if errors:
        print(f"[Stage 2] Validation warnings: {errors}")

    struct_path = os.path.join(output_dir, "structured_data.json")
    with open(struct_path, "w") as f:
        json.dump(structure, f, indent=2)

    section_count = len(structure.get("sections", []))
    step_count = sum(len(s.get("steps", [])) for s in structure.get("sections", []))
    print(f"[Stage 2] Done — {section_count} sections, {step_count} steps")

    # ── Stage 3: Script generation ──
    print("[Stage 3] Generating scene script...")
    scenes = generate_script(structure, metadata)

    script_path = os.path.join(output_dir, "scene_script.json")
    with open(script_path, "w") as f:
        json.dump(scenes, f, indent=2)

    print(f"[Stage 3] Done — {len(scenes)} scenes")

    return {
        "structure": structure,
        "scenes": scenes,
        "structure_path": struct_path,
        "script_path": script_path,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <pdf_or_url> [product_name] [brand] [model]")
        sys.exit(1)

    src = sys.argv[1]
    meta = {
        "product_name": sys.argv[2] if len(sys.argv) > 2 else "Unknown Product",
        "brand": sys.argv[3] if len(sys.argv) > 3 else "",
        "model": sys.argv[4] if len(sys.argv) > 4 else "",
    }
    result = run_pipeline(src, meta)
    print(f"\nOutputs saved to: {result['structure_path']}, {result['script_path']}")
PYEOF

make_commit "2025-03-22 10:30:00 +0530" "add pipeline orchestrator for stages 1-3 with CLI entry point" \
    manual_to_experiment/pipeline.py

# 6. Stage 4 image generation
mkdir -p manual_to_experiment/stage4_images

cat > manual_to_experiment/stage4_images/__init__.py << 'EOF'
EOF

cat > manual_to_experiment/stage4_images/imagen.py << 'PYEOF'
"""Generate images using Imagen 3 via Gemini API."""
import os
import google.generativeai as genai
from PIL import Image
import io


STYLE_PREFIX = (
    "Instructional product photography style. Clean white background. "
    "Professional, clear, well-lit. No text overlays. "
)
STYLE_SUFFIX = " Realistic, educational, suitable for a how-to video."


def generate_image(visual_hint: str, output_path: str) -> str:
    """Generate a 1920x1080 image from a visual hint.

    Args:
        visual_hint: Description of what the image should show.
        output_path: Where to save the PNG file.

    Returns:
        The output_path on success.
    """
    full_prompt = STYLE_PREFIX + visual_hint + STYLE_SUFFIX

    imagen = genai.ImageGenerationModel("imagen-3.0-generate-001")
    result = imagen.generate_images(
        prompt=full_prompt,
        number_of_images=1,
        aspect_ratio="16:9",
    )

    image = result.images[0]
    img = Image.open(io.BytesIO(image._image_bytes))
    img = img.resize((1920, 1080), Image.LANCZOS)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
PYEOF

cat > manual_to_experiment/stage4_images/fallback_slide.py << 'PYEOF'
"""Create a simple text slide as fallback when image generation fails."""
from PIL import Image, ImageDraw, ImageFont


def create_fallback_slide(title: str, output_path: str) -> str:
    """Create a white 1920x1080 slide with centered title text.

    Args:
        title: Text to display on the slide.
        output_path: Where to save the PNG.

    Returns:
        The output_path.
    """
    img = Image.new("RGB", (1920, 1080), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), title, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (1920 - text_w) // 2
    y = (1080 - text_h) // 2

    draw.text((x, y), title, fill="black", font=font)
    img.save(output_path, "PNG")
    return output_path
PYEOF

make_commit "2025-03-22 16:20:00 +0530" "add stage 4 image generation with imagen 3 and fallback slides" \
    manual_to_experiment/stage4_images/__init__.py \
    manual_to_experiment/stage4_images/imagen.py \
    manual_to_experiment/stage4_images/fallback_slide.py

# ─────────────────── March 23 ───────────────────

# 7. Stage 5 audio (TTS)
mkdir -p manual_to_experiment/stage5_audio

cat > manual_to_experiment/stage5_audio/__init__.py << 'EOF'
EOF

cat > manual_to_experiment/stage5_audio/tts.py << 'PYEOF'
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
PYEOF

make_commit "2025-03-23 11:00:00 +0530" "add stage 5 text-to-speech audio generation with google cloud tts" \
    manual_to_experiment/stage5_audio/__init__.py \
    manual_to_experiment/stage5_audio/tts.py

# 8. Stage 6 video assembly
mkdir -p manual_to_experiment/stage6_video

cat > manual_to_experiment/stage6_video/__init__.py << 'EOF'
EOF

cat > manual_to_experiment/stage6_video/assembler.py << 'PYEOF'
"""Assemble scene images and audio into a final video."""
import os
from moviepy.editor import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
)
from .subtitles import create_subtitle_clip


def assemble_video(scenes: list[dict], images_dir: str, audio_dir: str, output_path: str) -> str:
    """Combine per-scene images and audio into a single MP4.

    Args:
        scenes: List of scene dicts (need scene_id, narration).
        images_dir: Directory containing scene_N.png files.
        audio_dir: Directory containing scene_N.mp3 files.
        output_path: Where to write the final MP4.

    Returns:
        The output_path.
    """
    clips = []

    for scene in scenes:
        sid = scene["scene_id"]
        img_path = os.path.join(images_dir, f"scene_{sid}.png")
        audio_path = os.path.join(audio_dir, f"scene_{sid}.mp3")

        if not os.path.exists(img_path) or not os.path.exists(audio_path):
            print(f"Skipping scene {sid}: missing files")
            continue

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        image_clip = ImageClip(img_path).set_duration(duration)

        # Add subtitles
        subtitle = create_subtitle_clip(
            scene.get("narration", ""), duration, (1920, 1080)
        )

        video_clip = CompositeVideoClip([image_clip, subtitle])
        video_clip = video_clip.set_audio(audio_clip)
        clips.append(video_clip)

    if not clips:
        raise ValueError("No clips were generated")

    final = concatenate_videoclips(clips, method="compose")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
    )

    # Cleanup
    for clip in clips:
        clip.close()
    final.close()

    return output_path
PYEOF

cat > manual_to_experiment/stage6_video/subtitles.py << 'PYEOF'
"""Generate subtitle overlays for video clips."""
from moviepy.editor import TextClip


def create_subtitle_clip(text: str, duration: float, size: tuple[int, int]):
    """Create a subtitle text clip positioned at the bottom center.

    Args:
        text: The subtitle text.
        duration: How long to show the subtitle.
        size: Video dimensions (width, height).

    Returns:
        A TextClip positioned at bottom-center.
    """
    if not text.strip():
        return TextClip("", fontsize=1, color="white").set_duration(duration)

    # Wrap long text to ~60 chars per line
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 60:
            lines.append(" ".join(current_line))
            current_line = []
    if current_line:
        lines.append(" ".join(current_line))

    # Keep only last 2 lines to avoid cluttering
    display_text = "\n".join(lines[-2:])

    txt_clip = TextClip(
        display_text,
        fontsize=36,
        color="white",
        stroke_color="black",
        stroke_width=2,
        font="DejaVu-Sans-Bold",
        method="caption",
        size=(size[0] - 100, None),
    ).set_position(("center", size[1] - 120)).set_duration(duration)

    return txt_clip
PYEOF

make_commit "2025-03-23 17:30:00 +0530" "add stage 6 video assembly with clip concatenation and subtitles" \
    manual_to_experiment/stage6_video/__init__.py \
    manual_to_experiment/stage6_video/assembler.py \
    manual_to_experiment/stage6_video/subtitles.py

# ─────────────────── March 24 ───────────────────

# 9. Full pipeline update (stages 4-6 integrated)
cat > manual_to_experiment/pipeline.py << 'PYEOF'
"""Pipeline orchestrator — runs all 6 stages in sequence."""
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

from stage1_ingestion.detector import detect_input_type
from stage1_ingestion.pdf_uploader import upload_pdf_to_gemini
from stage1_ingestion.url_fetcher import fetch_url_html
from stage2_extraction.extractor import extract_structure
from stage2_extraction.validator import validate_structure
from stage3_script.generator import generate_script
from stage4_images.imagen import generate_image
from stage4_images.fallback_slide import create_fallback_slide
from stage5_audio.tts import generate_audio
from stage6_video.assembler import assemble_video

load_dotenv()


def run_pipeline(source: str, metadata: dict, output_dir: str = "outputs"):
    """Run the full manual-to-video pipeline.

    Args:
        source: Path to PDF, URL, or plain text.
        metadata: Dict with product_name, brand, model.
        output_dir: Where to save outputs.
    """
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    os.makedirs(output_dir, exist_ok=True)

    images_dir = os.path.join("temp", "images")
    audio_dir = os.path.join("temp", "audio")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # ── Stage 1: Ingestion ──
    input_type = detect_input_type(source)
    print(f"[Stage 1] Input type: {input_type}")

    if input_type == "pdf":
        content = upload_pdf_to_gemini(source)
    elif input_type == "url":
        content = fetch_url_html(source)
    else:
        content = source

    print("[Stage 1] Done")

    # ── Stage 2: Extraction ──
    print("[Stage 2] Extracting structure...")
    structure = extract_structure(content, metadata)

    errors = validate_structure(structure)
    if errors:
        print(f"[Stage 2] Validation warnings: {errors}")

    struct_path = os.path.join(output_dir, "structured_data.json")
    with open(struct_path, "w") as f:
        json.dump(structure, f, indent=2)

    section_count = len(structure.get("sections", []))
    step_count = sum(len(s.get("steps", [])) for s in structure.get("sections", []))
    print(f"[Stage 2] Done — {section_count} sections, {step_count} steps")

    # ── Stage 3: Script generation ──
    print("[Stage 3] Generating scene script...")
    scenes = generate_script(structure, metadata)

    script_path = os.path.join(output_dir, "scene_script.json")
    with open(script_path, "w") as f:
        json.dump(scenes, f, indent=2)

    print(f"[Stage 3] Done — {len(scenes)} scenes")

    # ── Stage 4: Image generation ──
    print(f"[Stage 4] Generating {len(scenes)} images...")
    for i, scene in enumerate(scenes):
        img_path = os.path.join(images_dir, f"scene_{scene['scene_id']}.png")
        try:
            generate_image(scene["visual_hint"], img_path)
            print(f"  Image {i+1}/{len(scenes)} done")
        except Exception as e:
            print(f"  Image {i+1} failed ({e}), using fallback slide")
            title = scene.get("narration", "")[:80]
            create_fallback_slide(title, img_path)

    print("[Stage 4] Done")

    # ── Stage 5: Audio generation ──
    print(f"[Stage 5] Generating {len(scenes)} audio clips...")
    durations = {}
    for i, scene in enumerate(scenes):
        audio_path = os.path.join(audio_dir, f"scene_{scene['scene_id']}.mp3")
        _, dur = generate_audio(scene["narration"], audio_path)
        durations[scene["scene_id"]] = dur
        print(f"  Audio {i+1}/{len(scenes)} done ({dur:.1f}s)")

    print("[Stage 5] Done")

    # ── Stage 6: Video assembly ──
    print("[Stage 6] Assembling final video...")
    video_path = os.path.join(output_dir, "final_video.mp4")
    assemble_video(scenes, images_dir, audio_dir, video_path)

    total_dur = sum(durations.values())
    print(f"[Stage 6] Done — {total_dur:.0f}s total duration")
    print(f"\nFinal video: {video_path}")

    return {
        "structure": structure,
        "scenes": scenes,
        "video_path": video_path,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <pdf_or_url> [product_name] [brand] [model]")
        sys.exit(1)

    src = sys.argv[1]
    meta = {
        "product_name": sys.argv[2] if len(sys.argv) > 2 else "Unknown Product",
        "brand": sys.argv[3] if len(sys.argv) > 3 else "",
        "model": sys.argv[4] if len(sys.argv) > 4 else "",
    }
    run_pipeline(src, meta)
PYEOF

make_commit "2025-03-24 10:15:00 +0530" "integrate stages 4-6 into pipeline orchestrator for end-to-end run" \
    manual_to_experiment/pipeline.py

# 10. Streamlit app
cat > manual_to_experiment/app.py << 'PYEOF'
"""Streamlit UI for Manual to Instruction Video Generator."""
import streamlit as st
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

from stage1_ingestion.detector import detect_input_type
from stage1_ingestion.pdf_uploader import upload_pdf_to_gemini
from stage1_ingestion.url_fetcher import fetch_url_html
from stage2_extraction.extractor import extract_structure
from stage2_extraction.validator import validate_structure
from stage3_script.generator import generate_script
from stage4_images.imagen import generate_image
from stage4_images.fallback_slide import create_fallback_slide
from stage5_audio.tts import generate_audio
from stage6_video.assembler import assemble_video

load_dotenv()

st.set_page_config(page_title="Manual to Video", layout="wide")
st.title("Manual to Instruction Video Generator")

# Sidebar
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    if api_key:
        genai.configure(api_key=api_key)

# Input form
input_type = st.radio("Input source", ["Upload PDF", "Paste URL"])

uploaded_file = None
url = ""
if input_type == "Upload PDF":
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
else:
    url = st.text_input("URL")

col1, col2, col3 = st.columns(3)
with col1:
    product_name = st.text_input("Product Name")
with col2:
    brand = st.text_input("Brand")
with col3:
    model = st.text_input("Model Number")

metadata = {"product_name": product_name, "brand": brand, "model": model}

if st.button("Generate Instruction Video", type="primary"):
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
        st.stop()

    progress = st.empty()
    status_container = st.container()

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("temp/images", exist_ok=True)
    os.makedirs("temp/audio", exist_ok=True)

    # Stage 1
    with status_container:
        st.write("Stage 1: Preparing input...")
    if uploaded_file:
        tmp_path = os.path.join("temp", uploaded_file.name)
        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        content = upload_pdf_to_gemini(tmp_path)
    elif url:
        content = fetch_url_html(url)
    else:
        st.error("Please upload a PDF or enter a URL.")
        st.stop()
    with status_container:
        st.write("Stage 1: Input prepared")

    # Stage 2
    with status_container:
        st.write("Stage 2: Extracting content...")
    structure = extract_structure(content, metadata)
    errors = validate_structure(structure)
    section_count = len(structure.get("sections", []))
    step_count = sum(len(s.get("steps", [])) for s in structure.get("sections", []))
    with status_container:
        st.write(f"Stage 2: Extracted {section_count} sections, {step_count} steps")

    # Stage 3
    with status_container:
        st.write("Stage 3: Generating script...")
    scenes = generate_script(structure, metadata)
    with status_container:
        st.write(f"Stage 3: Script ready — {len(scenes)} scenes")

    # Stage 4
    img_progress = st.progress(0, text="Stage 4: Generating images...")
    for i, scene in enumerate(scenes):
        img_path = os.path.join("temp/images", f"scene_{scene['scene_id']}.png")
        try:
            generate_image(scene["visual_hint"], img_path)
        except Exception:
            create_fallback_slide(scene.get("narration", "")[:80], img_path)
        img_progress.progress((i + 1) / len(scenes), text=f"Stage 4: Image {i+1}/{len(scenes)}")

    # Stage 5
    with status_container:
        st.write("Stage 5: Generating audio...")
    for scene in scenes:
        audio_path = os.path.join("temp/audio", f"scene_{scene['scene_id']}.mp3")
        generate_audio(scene["narration"], audio_path)
    with status_container:
        st.write("Stage 5: Audio done")

    # Stage 6
    with status_container:
        st.write("Stage 6: Assembling video...")
    video_path = "outputs/final_video.mp4"
    assemble_video(scenes, "temp/images", "temp/audio", video_path)
    with status_container:
        st.write("Stage 6: Video ready!")

    # Download button
    with open(video_path, "rb") as f:
        st.download_button("Download Video", f.read(), file_name="final_video.mp4", mime="video/mp4")
PYEOF

make_commit "2025-03-24 15:00:00 +0530" "add streamlit app UI with progress tracking and download button" \
    manual_to_experiment/app.py

# ─────────────────── March 25 ───────────────────

# 11. System design doc
make_commit "2025-03-25 10:00:00 +0530" "add system design document with full architecture and stage diagrams" \
    manual_to_experiment/SYSTEM_DESIGN.md

# 12. .env template and gitignore update
cat > manual_to_experiment/.env.example << 'EOF'
GEMINI_API_KEY=your_api_key_here
EOF

cat > manual_to_experiment/.gitignore << 'EOF'
.env
temp/
outputs/
__pycache__/
*.pyc
EOF

make_commit "2025-03-25 12:30:00 +0530" "add env template and gitignore for manual_to_experiment" \
    manual_to_experiment/.env.example \
    manual_to_experiment/.gitignore

# 13. Update requirements with playwright
cat > manual_to_experiment/requirements.txt << 'EOF'
google-generativeai>=0.8.0
google-cloud-texttospeech
httpx>=0.27.0
playwright>=1.44.0
moviepy>=1.0.3
Pillow>=10.0.0
python-dotenv>=1.0.0
streamlit>=1.35.0
EOF

make_commit "2025-03-25 14:45:00 +0530" "add playwright dependency for js-rendered url support" \
    manual_to_experiment/requirements.txt

echo ""
echo "=== Done! Generated 13 commits between March 20-25 ==="
echo ""
git log --oneline --since="2025-03-20" --until="2025-03-26"
