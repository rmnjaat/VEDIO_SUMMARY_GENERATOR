"""
Source-agnostic content schema.

Every source type (video transcript, podcast, article, PDF, etc.)
gets normalized into a ContentDocument before being fed to the prompts.
This makes the entire prompt system source-independent.
"""

from dataclasses import dataclass, field
from enum import Enum


class SourceType(Enum):
    VIDEO_TRANSCRIPT = "video_transcript"
    PODCAST = "podcast"
    ARTICLE = "article"
    PDF = "pdf"
    LECTURE_NOTES = "lecture_notes"
    DOCUMENTATION = "documentation"


@dataclass
class ContentChunk:
    """A single chunk of content with positional metadata."""
    text: str
    chunk_index: int
    total_chunks: int
    start_timestamp: str | None = None   # e.g. "01:23:45"
    end_timestamp: str | None = None
    source_metadata: dict = field(default_factory=dict)


@dataclass
class ContentDocument:
    """Normalized wrapper around any content source."""
    title: str
    source_type: SourceType
    chunks: list[ContentChunk]
    total_duration: str | None = None     # for time-based sources
    language: str = "en"
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(c.text for c in self.chunks)
