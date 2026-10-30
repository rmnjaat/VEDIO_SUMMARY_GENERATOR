"""All prompts for Stage 3: Script Generation and Review."""

# ---------------------------------------------------------------------------
# Call 4 — Script Generation
# ---------------------------------------------------------------------------
SCRIPT_SYSTEM = """You are a scriptwriter for instructional product videos on YouTube.
You write in a friendly, clear, conversational tone — like explaining to a friend.
Never use passive voice. Never use jargon without explaining it.
Always return valid JSON only. No markdown fences. No explanation."""

SCRIPT_PROMPT = """Convert the structured steps below into a spoken video script.
Use the product metadata from the input to name the product in the intro/outro.
One step = one scene. Sub-steps each become their own scene.

RULES:
- Tone: friendly, clear, spoken English — NOT written/formal English
- Each scene narration: 2-3 short sentences only (target 5-15 seconds when spoken)
- Use active voice ("remove the bolts" not "the bolts should be removed")
- Warnings MUST be included naturally in the narration — never skip them
- Do NOT add steps that are not in the input
- Do NOT narrate image descriptions — narrate the action

REQUIRED SPECIAL SCENES:
- scene_id 0: Intro — greet viewer, state product name, what video covers
- scene_id 1: "What you'll need" — list all prerequisites naturally
- scene_id 999: Outro — congratulate, brief recap, sign off

SECTION TRANSITIONS:
- Between sections add a transition scene.
  Example: "Great, setup is done! Now let's look at how to actually use it."

Return a JSON array:
[
  {{
    "scene_id": 0,
    "type": "intro",
    "section": null,
    "narration": "...",
    "visual_hint": "...",
    "estimated_duration_sec": 6
  }},
  {{
    "scene_id": 1,
    "type": "prerequisites",
    "section": null,
    "narration": "Before we start, here's what you'll need: ...",
    "visual_hint": "flat lay of all tools and parts needed",
    "estimated_duration_sec": 8
  }},
  {{
    "scene_id": 2,
    "type": "step",
    "section": "Initial Setup",
    "step_number": 1,
    "narration": "...",
    "visual_hint": "...",
    "estimated_duration_sec": 10
  }},
  {{
    "scene_id": 999,
    "type": "outro",
    "section": null,
    "narration": "...",
    "visual_hint": "...",
    "estimated_duration_sec": 5
  }}
]

estimated_duration_sec = word count of narration / 2.2

Return ONLY valid JSON array. No extra text."""


# ---------------------------------------------------------------------------
# Call 5 — Script Review + Polish
# ---------------------------------------------------------------------------
REVIEW_SYSTEM = """You are a senior video script editor.
Your job is to review and polish a video script for production quality.
Fix problems. Improve what needs improving. Leave what works alone.
Always return valid JSON only. No markdown fences. No explanation."""

REVIEW_USER = """Review this instruction video script and fix any quality issues.

CHECK AND FIX:

1. TONE CONSISTENCY
   - Every scene should sound like the same friendly person talking
   - Fix any that sound robotic, overly formal, or like reading a manual

2. DURATION BALANCE
   - Split any scene > 20 seconds into two scenes
   - Merge any scene < 3 seconds with its neighbor
   - Recalculate estimated_duration_sec (word count / 2.2)

3. VISUAL-NARRATION ALIGNMENT
   - Does each visual_hint actually match what the narration says?
   - visual_hint must be specific enough to generate an image from

4. WARNING PRESERVATION
   - Cross-check: every warning from the input data MUST appear in the script
   - List any warnings that were lost and add them back

5. TRANSITIONS
   - Is there a smooth transition between each section?
   - Does the intro properly set expectations?

6. PACING
   - 3+ very short scenes in a row → consider merging
   - A scene covering multiple distinct actions → split

Return:
{{
  "scenes": [ ... full corrected scene array ... ],
  "changelog": [
    "Scene 3: split into 3a and 3b — was 25 seconds",
    "Scene 7: rewrote narration — was too formal",
    "Added transition between Setup and Operation"
  ]
}}

Script to review:
{script_json}

Original enriched data (for warning cross-check):
{structured_data_json}"""
