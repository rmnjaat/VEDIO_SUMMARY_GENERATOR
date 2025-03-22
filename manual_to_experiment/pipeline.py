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
