"""Pipeline orchestrator — runs all 6 stages in sequence.

Stage 1:     Input preparation (PDF upload / URL fetch / raw text)
Stage 2:     Raw extraction (Gemini — auto-detects metadata)    [Call 1]
Stage 2.5:   Verification + grounding                           [Call 2]
Stage 2.7:   Enrichment (prerequisites, complexity, splitting)  [Call 3]
Stage 3:     Script generation                                  [Call 4]
Stage 3.5:   Script review + polish                             [Call 5]
Stage 4:     Image generation (pluggable provider)
Stage 5:     Audio / TTS generation (pluggable provider)
Stage 6:     Video assembly (pluggable provider)
"""
import json
import os
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from google import genai

from stage1_ingestion.detector import detect_input_type
from stage1_ingestion.pdf_uploader import upload_pdf_to_gemini
from stage1_ingestion.url_fetcher import fetch_url_html
from stage2_extraction.extractor import extract_structure
from stage2_extraction.validator import validate_structure
from stage2_extraction.verifier import verify_extraction, apply_verification
from stage2_extraction.enricher import enrich_structure
from stage3_script.generator import generate_script
from stage3_script.reviewer import review_script
from providers import get_registry
from providers.tts_xtts import XTTSProvider
from providers.image_imagen import ImagenProvider
from providers.image_fallback import FallbackSlideProvider
from providers.video_remotion import RemotionProvider

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ProgressCallback = Callable[[str, str], None] | None


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found. Add it to .env")
    return genai.Client(api_key=api_key)


def _save_json(data, output_dir: str, filename: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def _setup_providers(client: genai.Client, provider_config: dict | None = None):
    """Register default providers and apply overrides from config."""
    registry = get_registry()
    config = provider_config or {}

    # TTS providers
    if not registry.list_tts():
        registry.register_tts("xtts_v2", XTTSProvider())
    if "tts" in config:
        registry.set_active_tts(config["tts"])

    # Image providers
    if not registry.list_image():
        registry.register_image("imagen3", ImagenProvider(client))
        registry.register_image("fallback_slide", FallbackSlideProvider())
    if "image" in config:
        registry.set_active_image(config["image"])

    # Video providers
    if not registry.list_video():
        registry.register_video("remotion", RemotionProvider())
    if "video" in config:
        registry.set_active_video(config["video"])


def run_pipeline(
    source: str,
    output_dir: str = "outputs",
    on_progress: ProgressCallback = None,
    provider_config: dict | None = None,
):
    """Run the full manual-to-video pipeline (6 stages, 5 Gemini calls).

    Args:
        source: Path to PDF, URL, or plain text.
        output_dir: Where to save outputs.
        on_progress: Callback(stage_key, detail) for UI progress updates.
        provider_config: Optional dict to override active providers.
            e.g. {"tts": "xtts_v2", "image": "imagen3", "video": "remotion"}

    Returns:
        Dict with structure, scenes, video_path, and metadata.
    """
    def progress(stage: str, detail: str = ""):
        print(f"[{stage}] {detail}")
        if on_progress:
            on_progress(stage, detail)

    client = _get_client()
    _setup_providers(client, provider_config)
    registry = get_registry()

    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join("temp", "images")
    audio_dir = os.path.join("temp", "audio")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # ── Stage 1: Ingestion ──────────────────────────────────────────
    input_type = detect_input_type(source)
    progress("stage1", f"Detected input type: {input_type}")

    if input_type == "pdf":
        content = upload_pdf_to_gemini(client, source)
    elif input_type == "url":
        content = fetch_url_html(source)
    else:
        content = source

    progress("stage1_done", "Input ready")

    # ── Stage 2: Raw Extraction [Call 1] ────────────────────────────
    progress("stage2", "Extracting structure from document...")
    structure = extract_structure(client, content)

    errors = validate_structure(structure)
    if errors:
        progress("stage2", f"Validation warnings: {errors}")

    metadata = structure.get("metadata", {})
    product_label = f"{metadata.get('brand', '?')} {metadata.get('product_name', '?')}"
    _save_json(structure, output_dir, "structured_data_raw.json")

    section_count = len(structure.get("sections", []))
    step_count = sum(len(s.get("steps", [])) for s in structure.get("sections", []))
    progress("stage2_done", f"{product_label}: {section_count} sections, {step_count} steps")

    # ── Stage 2.5: Verification [Call 2] ────────────────────────────
    progress("stage2_5", "Verifying extraction against original document...")
    verification = verify_extraction(client, content, structure)
    _save_json(verification, output_dir, "verification_result.json")

    hallucinated = sum(1 for v in verification.get("verified_steps", []) if v.get("status") == "hallucinated")
    missing = len(verification.get("missing_steps", []))
    structure = apply_verification(structure, verification)
    _save_json(structure, output_dir, "structured_data_verified.json")
    progress("stage2_5_done", f"{hallucinated} hallucinated removed, {missing} missing added")

    # ── Stage 2.7: Enrichment [Call 3] ──────────────────────────────
    progress("stage2_7", "Enriching with prerequisites and complexity...")
    enriched = enrich_structure(client, structure)
    enriched["metadata"] = metadata
    _save_json(enriched, output_dir, "structured_data_final.json")

    prereq_count = len(enriched.get("prerequisites", []))
    progress("stage2_7_done", f"{prereq_count} prerequisites found")

    # ── Stage 3: Script Generation [Call 4] ─────────────────────────
    progress("stage3", "Generating video script...")
    scenes = generate_script(client, enriched, metadata)
    _save_json(scenes, output_dir, "scene_script_draft.json")
    progress("stage3_done", f"{len(scenes)} scenes generated")

    # ── Stage 3.5: Script Review [Call 5] ───────────────────────────
    progress("stage3_5", "Reviewing and polishing script...")
    review_result = review_script(client, scenes, enriched)
    scenes = review_result["scenes"]
    changelog = review_result.get("changelog", [])
    _save_json(review_result, output_dir, "scene_script_final.json")
    progress("stage3_5_done", f"{len(changelog)} fixes applied")

    # ── Stage 4: Image Generation (provider-based) ──────────────────
    image_provider = registry.get_image()
    progress("stage4", f"Generating {len(scenes)} images via {image_provider.get_name()}...")
    for i, scene in enumerate(scenes):
        img_path = os.path.join(images_dir, f"scene_{scene['scene_id']}.png")
        try:
            image_provider.generate(scene.get("visual_hint", ""), img_path)
        except Exception as e:
            FallbackSlideProvider().generate(
                scene.get("narration", "")[:80], img_path,
                section=scene.get("section", ""),
                step_number=f"Scene {scene['scene_id']}",
            )
        progress("stage4", f"Image {i+1}/{len(scenes)}")

    progress("stage4_done", f"{len(scenes)} images ready")

    # ── Stage 5: Audio / TTS (provider-based) ───────────────────────
    tts_provider = registry.get_tts()
    progress("stage5", f"Generating audio via {tts_provider.get_name()}...")
    for i, scene in enumerate(scenes):
        audio_path = os.path.join(audio_dir, f"scene_{scene['scene_id']}.wav")
        _, dur = tts_provider.generate(scene["narration"], audio_path)
        scene["real_duration_sec"] = dur
        progress("stage5", f"Audio {i+1}/{len(scenes)} ({dur:.1f}s)")

    _save_json(scenes, output_dir, "scene_script_with_durations.json")
    total_dur = sum(s.get("real_duration_sec", 0) for s in scenes)
    progress("stage5_done", f"Total audio: {total_dur:.0f}s")

    # ── Stage 6: Video Assembly (provider-based) ────────────────────
    video_provider = registry.get_video()
    progress("stage6", f"Rendering video via {video_provider.get_name()}...")
    video_path = os.path.join(output_dir, "final_video.mp4")
    video_provider.render(scenes, images_dir, audio_dir, video_path)

    progress("stage6_done", video_path)

    return {
        "metadata": metadata,
        "structure": enriched,
        "scenes": scenes,
        "changelog": changelog,
        "video_path": video_path,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <pdf_path_or_url_or_text>")
        sys.exit(1)

    run_pipeline(sys.argv[1])
