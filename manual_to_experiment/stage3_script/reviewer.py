"""Stage 3.5 — Call 5: Review and polish the generated script."""

import json
from google import genai
from google.genai import types

from stage2_extraction.validator import parse_gemini_json
from .prompts import REVIEW_SYSTEM, REVIEW_USER


def review_script(
    client: genai.Client,
    script: list[dict],
    enriched_data: dict,
    model_name: str = "gemini-2.0-flash",
) -> dict:
    """
    Review the generated script for quality issues and fix them.

    Args:
        client: A google.genai.Client instance.
        script: The draft scene list from Stage 3.
        enriched_data: The enriched data from Stage 2.7 (for warning cross-check).
        model_name: Gemini model to use.

    Returns:
        Dict with 'scenes' (corrected list) and 'changelog' (list of fixes made).
    """
    user_prompt = REVIEW_USER.format(
        script_json=json.dumps(script, indent=2),
        structured_data_json=json.dumps(enriched_data, indent=2),
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[types.Part.from_text(text=user_prompt)],
        config=types.GenerateContentConfig(
            system_instruction=REVIEW_SYSTEM,
        ),
    )

    result = parse_gemini_json(response.text)

    if isinstance(result, list):
        return {"scenes": result, "changelog": []}

    if "scenes" not in result:
        raise ValueError("Review response missing 'scenes' key")

    return result
