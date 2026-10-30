"""Generate a video scene script from structured data."""
import json
from google import genai
from google.genai import types
from .prompts import SCRIPT_PROMPT


def generate_script(client: genai.Client, structure: dict, metadata: dict, model_name: str = "gemini-2.0-flash") -> list[dict]:
    """Generate scene-by-scene video script.

    Args:
        client: A google.genai.Client instance.
        structure: Output from stage 2 extraction.
        metadata: Auto-detected product metadata.
        model_name: Gemini model to use.

    Returns:
        List of scene dicts.
    """
    context = f"Product: {metadata.get('product_name', 'Unknown')}"
    context += f"\nBrand: {metadata.get('brand', '')}"
    context += f"\nModel: {metadata.get('model', '')}"

    input_json = json.dumps(structure, indent=2)

    response = client.models.generate_content(
        model=model_name,
        contents=[types.Part.from_text(
            text=f"{context}\n\nStructured data:\n{input_json}\n\n{SCRIPT_PROMPT}"
        )],
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
