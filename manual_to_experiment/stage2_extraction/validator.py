"""Validate and parse Gemini JSON responses for all Stage 2 calls."""
import json
import re


def parse_gemini_json(text: str) -> dict | list:
    """Strip markdown fences and parse JSON from Gemini response.

    Gemini sometimes wraps JSON in ```json ... ``` — this handles it.
    """
    raw = text.strip()
    # Strip markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def validate_structure(data: dict) -> list[str]:
    """Validate the raw extraction structure. Returns list of errors (empty = valid)."""
    errors = []

    if "sections" not in data:
        errors.append("Missing 'sections' key")
        return errors

    for i, section in enumerate(data["sections"]):
        if "title" not in section:
            errors.append(f"Section {i}: missing title")
        if "steps" not in section:
            errors.append(f"Section {i}: missing steps")
            continue
        for j, step in enumerate(section["steps"]):
            if "description" not in step:
                errors.append(f"Section {i}, Step {j}: missing description")

    return errors


def validate_extraction(data: dict) -> dict:
    """Validate and return the extraction result."""
    errors = validate_structure(data)
    if errors:
        raise ValueError(f"Extraction validation failed: {errors}")
    return data


def validate_verification(data: dict) -> dict:
    """Validate the verification response structure."""
    if "verified_steps" not in data:
        raise ValueError("Verification response missing 'verified_steps' key")
    return data


def validate_enrichment(data: dict) -> dict:
    """Validate the enrichment response structure."""
    if "sections" not in data:
        raise ValueError("Enrichment response missing 'sections' key")
    return data
