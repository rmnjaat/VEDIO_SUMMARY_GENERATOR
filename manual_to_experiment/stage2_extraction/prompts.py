"""All prompts for Stage 2: Extraction, Verification, and Enrichment."""

# ---------------------------------------------------------------------------
# Call 1 — Raw Extraction (auto-detects product metadata)
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are a technical documentation expert.
Your only job is to extract instructional content from product manuals.
Be faithful — do not invent, summarize, or rephrase steps.

Read the document and:
1. IDENTIFY the product — extract its name, brand, and model number.
   If any are not found, use "Unknown".
2. EXTRACT ONLY actionable instructional content.

IGNORE completely:
- Legal disclaimers, warranty pages
- Regulatory/compliance sections (CE, FCC)
- Specification tables (dimensions, voltage, weight)
- Table of contents
- Contact/support information

Return this exact JSON structure:
{
  "metadata": {
    "product_name": "extracted product name",
    "brand": "extracted brand name",
    "model": "extracted model number"
  },
  "product_summary": "one sentence — what this product does",
  "sections": [
    {
      "title": "section name",
      "type": "setup | operation | maintenance | safety | troubleshooting",
      "steps": [
        {
          "step_number": 1,
          "title": "short step title",
          "description": "full description — exactly as manual intends",
          "warning": "safety warning text, or null",
          "image_hint": "specific visual — what should be shown for this step"
        }
      ]
    }
  ]
}

image_hint must be specific and visual:
  BAD:  "setup diagram"
  GOOD: "hands connecting blue water inlet hose to back-left port of washing machine"

Return ONLY valid JSON. No extra text. No markdown fences."""


# ---------------------------------------------------------------------------
# Call 2 — Verification + Grounding
# ---------------------------------------------------------------------------
VERIFICATION_SYSTEM = """You are a quality auditor for technical documentation extraction.
Your job is to verify that an extraction is correct and complete.
You must be thorough — missing a step could cause real harm to someone.
Always return valid JSON only. No markdown fences. No explanation."""

VERIFICATION_USER = """I extracted the following structured data from a product manual.
Your job: re-read the original manual and verify the extraction.

For EACH extracted step, do one of:
  VERIFIED    — the step exists in the manual (quote the source sentence)
  HALLUCINATED — this step is NOT in the manual (flag for removal)
  INACCURATE  — the step exists but description is wrong (provide correction)

Then check: are there steps IN THE MANUAL that were NOT extracted?
If yes, list them as missing_steps.

Return this JSON:
{{
  "verified_steps": [
    {{
      "section": "section title",
      "step_number": 1,
      "status": "verified | hallucinated | inaccurate",
      "source_quote": "exact quote from manual, or null if hallucinated",
      "correction": "corrected description, or null if verified"
    }}
  ],
  "missing_steps": [
    {{
      "found_in": "page or section where this step appears in manual",
      "source_quote": "exact text from manual",
      "suggested_section": "which existing section it belongs to",
      "suggested_step": {{
        "title": "short step title",
        "description": "full description",
        "warning": "warning or null",
        "image_hint": "specific visual description"
      }}
    }}
  ],
  "order_issues": [
    "step X should come before step Y because..."
  ]
}}

Return ONLY valid JSON. No extra text.

Extracted data:
{structured_data_json}"""


# ---------------------------------------------------------------------------
# Call 3 — Enrichment (prerequisites + complexity + splitting)
# ---------------------------------------------------------------------------
ENRICHMENT_SYSTEM = """You are a technical content analyst.
Your job is to enrich extraction data to make it production-ready for video.
Always return valid JSON only. No markdown fences. No explanation."""

ENRICHMENT_USER = """Here is the verified extraction from a product manual.

Do three things:

1. PREREQUISITES — list every tool, part, material, or condition
   the user needs BEFORE starting. Look across ALL sections.

2. COMPLEXITY SCORING — score each step 1-5:
   1 = trivial (open a door, press a button)
   2 = simple (plug in a cable, flip a switch)
   3 = moderate (adjust feet until level, measure a distance)
   4 = complex (connect multiple hoses in specific order)
   5 = critical (electrical work, safety-sensitive, irreversible)

3. STEP SPLITTING — any step scored 4 or 5 MUST be split
   into 2-3 simpler sub-steps. Each sub-step should be one
   clear action a person can do without pausing.

Return:
{{
  "prerequisites": [
    {{
      "item": "17mm spanner",
      "needed_for": "removing transport bolts",
      "category": "tool | part | material | condition"
    }}
  ],
  "sections": [
    {{
      "title": "...",
      "type": "...",
      "steps": [
        {{
          "step_number": 1,
          "title": "...",
          "description": "...",
          "warning": "...",
          "image_hint": "...",
          "complexity": 2,
          "sub_steps": null
        }}
      ]
    }}
  ]
}}

Return ONLY valid JSON. No extra text.

Verified data:
{structured_data_json}"""
