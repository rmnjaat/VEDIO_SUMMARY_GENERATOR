"""Stage 2.5 — Call 2: Verify extraction against the original document."""

import json
from google import genai
from google.genai import types

from .prompts import VERIFICATION_SYSTEM, VERIFICATION_USER
from .validator import parse_gemini_json, validate_verification


def verify_extraction(
    client: genai.Client,
    content,
    structured_data: dict,
    model_name: str = "gemini-2.0-flash",
) -> dict:
    """
    Re-read the original document and verify the extraction is correct and complete.

    Args:
        client: A google.genai.Client instance.
        content: Original Gemini file object / HTML / text.
        structured_data: The raw extraction from Call 1.
        model_name: Gemini model to use.

    Returns:
        Verification result dict with verified_steps, missing_steps, order_issues.
    """
    user_prompt = VERIFICATION_USER.format(
        structured_data_json=json.dumps(structured_data, indent=2),
    )

    if isinstance(content, str):
        parts = [types.Part.from_text(text=user_prompt + "\n\n---ORIGINAL DOCUMENT---\n" + content)]
    else:
        parts = [content, types.Part.from_text(text=user_prompt)]

    response = client.models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=VERIFICATION_SYSTEM,
        ),
    )

    return validate_verification(parse_gemini_json(response.text))


def apply_verification(structured_data: dict, verification: dict) -> dict:
    """
    Apply verification results to the structured data:
    - Remove hallucinated steps
    - Fix inaccurate steps
    - Add missing steps
    - Fix ordering issues

    Args:
        structured_data: The raw extraction.
        verification: The verification result from verify_extraction().

    Returns:
        Corrected structured data dict.
    """
    # Build a lookup of verification results by (section, step_number)
    step_status = {}
    for v in verification.get("verified_steps", []):
        key = (v["section"], v["step_number"])
        step_status[key] = v

    # Filter and correct sections
    for section in structured_data.get("sections", []):
        corrected_steps = []
        for step in section.get("steps", []):
            key = (section["title"], step["step_number"])
            status = step_status.get(key, {})

            if status.get("status") == "hallucinated":
                continue

            if status.get("status") == "inaccurate" and status.get("correction"):
                step["description"] = status["correction"]

            corrected_steps.append(step)

        section["steps"] = corrected_steps

    # Add missing steps
    for missing in verification.get("missing_steps", []):
        target_section = missing.get("suggested_section")
        new_step = missing.get("suggested_step", {})

        for section in structured_data["sections"]:
            if section["title"] == target_section:
                max_num = max((s["step_number"] for s in section["steps"]), default=0)
                new_step["step_number"] = max_num + 1
                section["steps"].append(new_step)
                break

    # Re-number steps in each section
    for section in structured_data["sections"]:
        for i, step in enumerate(section["steps"], 1):
            step["step_number"] = i

    # Remove empty sections
    structured_data["sections"] = [
        s for s in structured_data["sections"] if s.get("steps")
    ]

    return structured_data
