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
