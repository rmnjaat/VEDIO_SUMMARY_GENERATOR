"""Stage 2.7 — Call 3: Enrich with prerequisites, complexity scores, and step splitting."""

import json
from google import genai
from google.genai import types

from .prompts import ENRICHMENT_SYSTEM, ENRICHMENT_USER
from .validator import parse_gemini_json, validate_enrichment


def enrich_structure(
    client: genai.Client,
    structured_data: dict,
    model_name: str = "gemini-2.0-flash",
) -> dict:
    """
    Enrich the verified extraction with prerequisites, complexity scores, sub-steps.

    Args:
        client: A google.genai.Client instance.
        structured_data: Verified structured data from Stage 2.5.
        model_name: Gemini model to use.

    Returns:
        Enriched structured data with prerequisites, complexity, and sub_steps.
    """
    user_prompt = ENRICHMENT_USER.format(
        structured_data_json=json.dumps(structured_data, indent=2),
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[types.Part.from_text(text=user_prompt)],
        config=types.GenerateContentConfig(
            system_instruction=ENRICHMENT_SYSTEM,
        ),
    )

    return validate_enrichment(parse_gemini_json(response.text))
