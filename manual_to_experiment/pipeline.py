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
