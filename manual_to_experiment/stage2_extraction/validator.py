"""Validate the extracted structure against expected schema."""


def validate_structure(data: dict) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
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
