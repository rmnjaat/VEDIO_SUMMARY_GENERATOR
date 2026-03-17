from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptResult:
    text: str
    timestamped_text: str


class TranscriptionProvider(ABC):

    @abstractmethod
    def transcribe(self, audio_paths: list[str]) -> TranscriptResult:
        """Transcribe a list of audio chunk paths and return merged result."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def max_chunk_size_mb(self) -> int:
        """Max file size this provider accepts per request, in MB."""
        ...
