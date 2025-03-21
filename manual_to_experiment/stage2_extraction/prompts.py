"""Prompts for the extraction stage."""

EXTRACTION_PROMPT = """You are analyzing a product manual. Extract the following structured data as JSON:

{
  "product_name": "...",
  "sections": [
    {
      "title": "Section title",
      "type": "setup|usage|maintenance|safety",
      "steps": [
        {
          "step_number": 1,
          "title": "Short step title",
          "description": "Detailed description of what to do",
          "warning": "Any safety warning or null",
          "image_hint": "Description of any diagram/image shown for this step"
        }
      ]
    }
  ]
}

Rules:
- Extract EVERY actionable step from the manual
- Include image_hint only if there is a relevant diagram on the page
- Preserve the order as it appears in the manual
- Mark warnings from caution/warning boxes
- Return valid JSON only, no markdown
"""
