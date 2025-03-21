"""Prompts for scene script generation."""

SCRIPT_PROMPT = """You are a video script writer. Given structured manual data, produce a scene-by-scene script as a JSON array.

Each scene object:
{
  "scene_id": 0,
  "type": "intro|step|warning|outro",
  "narration": "What the narrator says (conversational, clear)",
  "visual_hint": "Detailed description for image generation",
  "estimated_duration_sec": 8
}

Rules:
- Start with an intro scene (greet viewer, state product name)
- One scene per step (combine very short steps if needed)
- Add a dedicated warning scene for any safety warnings
- End with an outro scene
- Narration should be conversational, 2nd person ("you")
- visual_hint must be specific enough for image generation
- estimated_duration_sec = word_count / 2.2 (rounded up)
- Return valid JSON array only
"""
