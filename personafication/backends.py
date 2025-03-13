"""
LLM backend implementations for the analysis pipeline.
"""

from google import genai
from google.genai import types

from .pipeline import LLMBackend


class GeminiBackend(LLMBackend):
    """Gemini-powered backend using the new google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.1,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                response_mime_type="application/json",
            ),
        )
        return response.text


class GeminiTextBackend(LLMBackend):
    """Gemini backend that returns plain text (no JSON mime type constraint).
    Used for the Doc Writer stage which outputs documentation, not JSON."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.2,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=self.temperature,
                response_mime_type="text/plain",
            ),
        )
        return response.text
