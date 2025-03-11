from .groq_provider import GroqProvider
from .assemblyai_provider import AssemblyAIProvider
from .gemini_provider import GeminiProvider
from .mlx_provider import MLXProvider

PROVIDERS = {
    "groq": GroqProvider,
    "assemblyai": AssemblyAIProvider,
    "gemini": GeminiProvider,
    "mlx": MLXProvider,
}
