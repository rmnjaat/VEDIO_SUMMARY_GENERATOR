"""Extract structured data from manual content using Gemini."""
import json
from google import genai
from google.genai import types
from .prompts import EXTRACTION_PROMPT


def extract_structure(client: genai.Client, content, model_name: str = "gemini-2.0-flash") -> dict:
    """Send content to Gemini and parse the structured extraction.

    Gemini auto-detects product name, brand, and model from the document.

    Args:
        client: A google.genai.Client instance.
        content: Either a Gemini file object (PDF), HTML string, or plain text.
        model_name: Gemini model to use.

    Returns:
        Parsed JSON dict with metadata, sections, and steps.
    """
    if isinstance(content, str):
        parts = [types.Part.from_text(text=EXTRACTION_PROMPT + "\n\n---DOCUMENT---\n" + content)]
    else:
        parts = [content, types.Part.from_text(text=EXTRACTION_PROMPT)]

    response = client.models.generate_content(
        model=model_name,
        contents=parts,
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    return json.loads(raw)
