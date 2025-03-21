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
