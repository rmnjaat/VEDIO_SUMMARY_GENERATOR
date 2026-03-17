from .groq_provider import GroqProvider
from .assemblyai_provider import AssemblyAIProvider
from .gemini_provider import GeminiProvider

PROVIDERS = {
    "groq": GroqProvider,
    "assemblyai": AssemblyAIProvider,
    "gemini": GeminiProvider,
}
