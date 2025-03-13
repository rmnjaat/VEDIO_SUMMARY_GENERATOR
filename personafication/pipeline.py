"""
Analysis pipeline: Transcript → Scanner (per chunk) → Architect → Content Tree.

This module wires the prompts to actual LLM calls.
Designed to be provider-agnostic — swap in OpenAI, Anthropic, Gemini, local, etc.
"""

import json
import os
import re
import textwrap
from abc import ABC, abstractmethod


def _save_step(save_dir: str | None, filename: str, data) -> None:
    """Save intermediate pipeline output to the run folder."""
    if not save_dir:
        return
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, (dict, list)):
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            f.write(str(data))
    print(f"  [Saved] {filename}")

from .source_schema import ContentChunk, ContentDocument, SourceType
from .prompts import (
    SCANNER_SYSTEM_PROMPT, ARCHITECT_SYSTEM_PROMPT,
    DOC_SCANNER_SYSTEM_PROMPT, DOC_ARCHITECT_SYSTEM_PROMPT,
    DOC_WRITER_SYSTEM_PROMPT,
    DOC_OUTLINER_SYSTEM_PROMPT, DOC_SECTION_WRITER_SYSTEM_PROMPT,
    BLOG_TOPIC_SPLITTER_SYSTEM_PROMPT,
    BLOG_SECTION_WRITER_SYSTEM_PROMPT,
    BLOG_FINALIZER_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Abstract LLM backend (swap in any provider)
# ---------------------------------------------------------------------------

class LLMBackend(ABC):
    """Minimal interface for an LLM call."""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str:
        """Send a system + user message and return the assistant response."""
        ...


# ---------------------------------------------------------------------------
# Chunker: splits a ContentDocument into manageable pieces
# ---------------------------------------------------------------------------

def chunk_transcript(
    full_text: str,
    max_words: int = 4000,
    overlap_words: int = 200,
) -> list[str]:
    """Split transcript text into overlapping chunks at paragraph boundaries."""
    paragraphs = full_text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_word_count = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_word_count + para_words > max_words and current:
            chunks.append("\n\n".join(current))
            # Keep last few paragraphs for overlap
            overlap: list[str] = []
            overlap_count = 0
            for p in reversed(current):
                pw = len(p.split())
                if overlap_count + pw > overlap_words:
                    break
                overlap.insert(0, p)
                overlap_count += pw
            current = overlap
            current_word_count = overlap_count

        current.append(para)
        current_word_count += para_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class AnalysisPipeline:
    """Runs the full Scanner → Architect pipeline."""

    def __init__(self, llm: LLMBackend):
        self.llm = llm

    def _build_scanner_user_message(self, chunk: ContentChunk) -> str:
        """Build the user message for a single Scanner call."""
        meta = {
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "source_type": chunk.source_metadata.get("source_type", "video_transcript"),
        }
        if chunk.start_timestamp:
            meta["start_timestamp"] = chunk.start_timestamp
        if chunk.end_timestamp:
            meta["end_timestamp"] = chunk.end_timestamp

        return (
            f"## Chunk Metadata\n```json\n{json.dumps(meta)}\n```\n\n"
            f"## Transcript Chunk\n\n{chunk.text}"
        )

    def _parse_json_response(self, response: str) -> dict:
        """Extract JSON from an LLM response, handling markdown fences."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        # Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse JSON from response:\n{response[:500]}...")

    def scan_chunk(self, chunk: ContentChunk) -> dict:
        """Run the Scanner on a single chunk. Returns parsed JSON."""
        user_msg = self._build_scanner_user_message(chunk)
        response = self.llm.chat(SCANNER_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    def scan_all(self, doc: ContentDocument) -> list[dict]:
        """Run the Scanner on every chunk. Returns list of extraction dicts."""
        results = []
        for chunk in doc.chunks:
            result = self.scan_chunk(chunk)
            results.append(result)
        return results

    def architect(self, scanner_outputs: list[dict], doc: ContentDocument) -> dict:
        """Run the Architect to merge scanner outputs into a content tree."""
        user_msg = (
            f"## Source Info\n"
            f"- Title: {doc.title}\n"
            f"- Source type: {doc.source_type.value}\n"
            f"- Total duration: {doc.total_duration or 'unknown'}\n"
            f"- Total chunks scanned: {len(scanner_outputs)}\n\n"
            f"## Scanner Outputs\n\n"
            f"```json\n{json.dumps(scanner_outputs, indent=2)}\n```"
        )
        response = self.llm.chat(ARCHITECT_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    def run(self, doc: ContentDocument, save_dir: str | None = None) -> dict:
        """Full pipeline: scan all chunks → architect → content tree."""
        print(f"[Pipeline] Scanning {len(doc.chunks)} chunks...")
        scanner_outputs = self.scan_all(doc)
        _save_step(save_dir, "1_scanner_outputs.json", scanner_outputs)

        print(f"[Pipeline] Scanning complete. Building content tree...")
        tree = self.architect(scanner_outputs, doc)
        _save_step(save_dir, "2_content_tree.json", tree)

        print(f"[Pipeline] Content tree built.")
        return tree


# ---------------------------------------------------------------------------
# Doc Writer Pipeline (Transcript → Scanner → Doc Writer → plain-text doc)
# ---------------------------------------------------------------------------

class DocWriterPipeline:
    """
    3-stage doc generation pipeline:

      Stage 1 — Scanner  (per chunk)  : Extract topics/concepts/Q&A as JSON
      Stage 2 — Outliner (all chunks) : Plan the doc skeleton (headings + mapping)
      Stage 3 — Section Writer (per section) : Write each section in full detail

    This avoids the "quality degrades in the second half" problem because the
    LLM only writes one focused section at a time, never the whole document.

    Output is a STRING (plain text), not JSON.
    """

    def __init__(self, llm: LLMBackend, text_llm: LLMBackend | None = None):
        """
        Args:
            llm: Backend for Scanner + Outliner calls (needs JSON output mode).
            text_llm: Backend for Section Writer calls (needs plain-text output).
                      If None, uses `llm` for both.
        """
        self.llm = llm
        self.text_llm = text_llm or llm

    # -- helpers --

    def _build_scanner_user_message(self, chunk: ContentChunk) -> str:
        meta = {
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "source_type": chunk.source_metadata.get("source_type", "video_transcript"),
        }
        if chunk.start_timestamp:
            meta["start_timestamp"] = chunk.start_timestamp
        if chunk.end_timestamp:
            meta["end_timestamp"] = chunk.end_timestamp
        return (
            f"## Chunk Metadata\n```json\n{json.dumps(meta)}\n```\n\n"
            f"## Transcript Chunk\n\n{chunk.text}"
        )

    def _parse_json_response(self, response: str) -> dict:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse JSON from response:\n{response[:500]}...")

    # -- Stage 1: Scanner --

    def scan_chunk(self, chunk: ContentChunk) -> dict:
        user_msg = self._build_scanner_user_message(chunk)
        response = self.llm.chat(SCANNER_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    def scan_all(self, doc: ContentDocument) -> list[dict]:
        results = []
        for i, chunk in enumerate(doc.chunks):
            print(f"  [Scanner] Chunk {i+1}/{len(doc.chunks)}...")
            result = self.scan_chunk(chunk)
            results.append(result)
        return results

    # -- Stage 2: Outliner --

    def build_outline(self, scanner_outputs: list[dict], doc: ContentDocument) -> dict:
        """Produce a JSON outline: title, tags, and section plan."""
        user_msg = (
            f"## Source Info\n"
            f"- Title: {doc.title}\n"
            f"- Source type: {doc.source_type.value}\n"
            f"- Total duration: {doc.total_duration or 'unknown'}\n"
            f"- Total chunks scanned: {len(scanner_outputs)}\n\n"
            f"## Scanner Outputs\n\n"
            f"```json\n{json.dumps(scanner_outputs, indent=2)}\n```"
        )
        response = self.llm.chat(DOC_OUTLINER_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    # -- Stage 3: Section Writer --

    def write_section(
        self,
        section_outline: dict,
        scanner_outputs: list[dict],
        previous_headings: list[str],
    ) -> str:
        """Write one section using only the relevant scanner chunks."""
        # Gather only the scanner chunks this section needs
        chunk_indices = section_outline.get("scanner_chunks", [])
        relevant_data = [scanner_outputs[i] for i in chunk_indices if i < len(scanner_outputs)]
        # If no specific chunks mapped, give all (fallback)
        if not relevant_data:
            relevant_data = scanner_outputs

        context_str = ""
        if previous_headings:
            context_str = (
                f"## Sections Already Written (do NOT repeat this content)\n"
                + "\n".join(f"- {h}" for h in previous_headings)
                + "\n\n"
            )

        user_msg = (
            f"{context_str}"
            f"## Section Outline\n"
            f"```json\n{json.dumps(section_outline, indent=2)}\n```\n\n"
            f"## Relevant Scanner Data\n\n"
            f"```json\n{json.dumps(relevant_data, indent=2)}\n```"
        )
        response = self.text_llm.chat(DOC_SECTION_WRITER_SYSTEM_PROMPT, user_msg)
        return response.strip()

    # -- Full pipeline --

    def run(self, doc: ContentDocument, save_dir: str | None = None) -> str:
        """Full pipeline: scan → outline → write sections → stitch."""

        # Stage 1: Scan
        print(f"[DocWriter] Stage 1: Scanning {len(doc.chunks)} chunks...")
        scanner_outputs = self.scan_all(doc)
        _save_step(save_dir, "1_scanner_outputs.json", scanner_outputs)

        # Stage 2: Outline
        print(f"[DocWriter] Stage 2: Building outline...")
        outline = self.build_outline(scanner_outputs, doc)
        _save_step(save_dir, "2_outline.json", outline)
        sections = outline.get("sections", [])
        title = outline.get("title", doc.title)
        tags = outline.get("tags", [])
        print(f"  [Outliner] Planned {len(sections)} sections")

        # Stage 3: Write each section
        print(f"[DocWriter] Stage 3: Writing {len(sections)} sections...")
        written_parts = []
        previous_headings = []

        for i, section in enumerate(sections):
            heading = section.get("heading", f"Section {i+1}")
            weight = section.get("estimated_weight", "medium")
            print(f"  [Writer] Section {i+1}/{len(sections)}: {heading} ({weight})")

            section_text = self.write_section(section, scanner_outputs, previous_headings)
            written_parts.append(section_text)
            previous_headings.append(heading)

        _save_step(save_dir, "3_sections_written.json", [
            {"heading": s.get("heading", f"Section {i+1}"), "text": t}
            for i, (s, t) in enumerate(zip(sections, written_parts))
        ])

        # Stitch: title + tags + all sections
        tags_line = f"Tags:{','.join(tags)}" if tags else "Tags:General"
        final_doc = f"{title}\n{tags_line}\n"
        for part in written_parts:
            final_doc += f"\n{part}\n"

        print(f"[DocWriter] Done. Document has {len(sections)} sections.")
        return final_doc


# ---------------------------------------------------------------------------
# Doc Analysis Pipeline (for documentation / articles)
# ---------------------------------------------------------------------------

class DocAnalysisPipeline:
    """Runs the Doc Scanner → Doc Architect pipeline for documentation."""

    def __init__(self, llm: LLMBackend):
        self.llm = llm

    def _build_doc_scanner_user_message(self, chunk: ContentChunk) -> str:
        meta = {
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "source_type": chunk.source_metadata.get("source_type", "documentation"),
        }
        return (
            f"## Chunk Metadata\n```json\n{json.dumps(meta)}\n```\n\n"
            f"## Document Chunk\n\n{chunk.text}"
        )

    def _parse_json_response(self, response: str) -> dict:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse JSON from response:\n{response[:500]}...")

    def scan_chunk(self, chunk: ContentChunk) -> dict:
        user_msg = self._build_doc_scanner_user_message(chunk)
        response = self.llm.chat(DOC_SCANNER_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    def scan_all(self, doc: ContentDocument) -> list[dict]:
        results = []
        for chunk in doc.chunks:
            result = self.scan_chunk(chunk)
            results.append(result)
        return results

    def architect(self, scanner_outputs: list[dict], doc: ContentDocument) -> dict:
        user_msg = (
            f"## Source Info\n"
            f"- Title: {doc.title}\n"
            f"- Source type: {doc.source_type.value}\n"
            f"- Total chunks scanned: {len(scanner_outputs)}\n\n"
            f"## Doc Scanner Outputs\n\n"
            f"```json\n{json.dumps(scanner_outputs, indent=2)}\n```"
        )
        response = self.llm.chat(DOC_ARCHITECT_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    def run(self, doc: ContentDocument) -> dict:
        print(f"[DocPipeline] Scanning {len(doc.chunks)} chunks...")
        scanner_outputs = self.scan_all(doc)
        print(f"[DocPipeline] Scanning complete. Building document tree...")
        tree = self.architect(scanner_outputs, doc)
        print(f"[DocPipeline] Document tree built.")
        return tree


# ---------------------------------------------------------------------------
# Blog Writer Pipeline (multi-topic, 4-stage, exhaustive blog generation)
# ---------------------------------------------------------------------------

class BlogWriterPipeline:
    """
    4-stage blog generation pipeline:

      Stage 1 — Scanner        (per chunk)   : Extract topics/concepts/Q&A as JSON
      Stage 2 — Topic Splitter (all chunks)   : Identify major topics, plan outlines
      Stage 3 — Section Writer (per section)  : Write each section thoroughly
      Stage 4 — Finalizer      (per section)  : Catch missed details, polish

    Key differences from DocWriterPipeline:
      - Produces N output files (one per major topic) when topics are distinct
      - Section Writer receives RAW TRANSCRIPT alongside scanner data
      - Finalizer pass compares written text against source to fill gaps
      - Writer adds clarifying examples and supplementary context
      - Blog-style: short paragraphs, clear structure, no walls of text

    Output is a list of (filename_slug, content_string) tuples.
    """

    def __init__(self, llm: LLMBackend, text_llm: LLMBackend | None = None):
        """
        Args:
            llm: Backend for Scanner + Topic Splitter (needs JSON output).
            text_llm: Backend for Section Writer + Finalizer (plain text).
                      If None, uses `llm` for both.
        """
        self.llm = llm
        self.text_llm = text_llm or llm

    # -- helpers (same as other pipelines) --

    def _build_scanner_user_message(self, chunk: ContentChunk) -> str:
        meta = {
            "chunk_index": chunk.chunk_index,
            "total_chunks": chunk.total_chunks,
            "source_type": chunk.source_metadata.get("source_type", "video_transcript"),
        }
        if chunk.start_timestamp:
            meta["start_timestamp"] = chunk.start_timestamp
        if chunk.end_timestamp:
            meta["end_timestamp"] = chunk.end_timestamp
        return (
            f"## Chunk Metadata\n```json\n{json.dumps(meta)}\n```\n\n"
            f"## Transcript Chunk\n\n{chunk.text}"
        )

    def _parse_json_response(self, response: str) -> dict:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse JSON from response:\n{response[:500]}...")

    def _gather_raw_text(self, chunk_indices: list[int], chunks: list[ContentChunk]) -> str:
        """Gather raw transcript text for the given chunk indices."""
        parts = []
        for i in chunk_indices:
            if i < len(chunks):
                parts.append(chunks[i].text)
        return "\n\n".join(parts)

    # -- Stage 1: Scanner (reuses existing SCANNER_SYSTEM_PROMPT) --

    def scan_chunk(self, chunk: ContentChunk) -> dict:
        user_msg = self._build_scanner_user_message(chunk)
        response = self.llm.chat(SCANNER_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    def scan_all(self, doc: ContentDocument) -> list[dict]:
        results = []
        for i, chunk in enumerate(doc.chunks):
            print(f"  [Scanner] Chunk {i+1}/{len(doc.chunks)}...")
            result = self.scan_chunk(chunk)
            results.append(result)
        return results

    # -- Stage 2: Topic Splitter --

    def split_topics(self, scanner_outputs: list[dict], doc: ContentDocument) -> dict:
        """Identify major topics and plan a separate outline for each."""
        user_msg = (
            f"## Source Info\n"
            f"- Title: {doc.title}\n"
            f"- Source type: {doc.source_type.value}\n"
            f"- Total duration: {doc.total_duration or 'unknown'}\n"
            f"- Total chunks scanned: {len(scanner_outputs)}\n\n"
            f"## Scanner Outputs\n\n"
            f"```json\n{json.dumps(scanner_outputs, indent=2)}\n```"
        )
        response = self.llm.chat(BLOG_TOPIC_SPLITTER_SYSTEM_PROMPT, user_msg)
        return self._parse_json_response(response)

    # -- Stage 3: Blog Section Writer --

    def write_section(
        self,
        section_outline: dict,
        scanner_outputs: list[dict],
        chunks: list[ContentChunk],
        previous_headings: list[str],
    ) -> str:
        """Write one section with full detail using scanner data + raw transcript."""
        # Gather relevant scanner data
        chunk_indices = section_outline.get("scanner_chunks", [])
        relevant_data = [scanner_outputs[i] for i in chunk_indices if i < len(scanner_outputs)]
        if not relevant_data:
            relevant_data = scanner_outputs

        # Gather raw transcript text for those chunks
        raw_text = self._gather_raw_text(chunk_indices, chunks)
        if not raw_text:
            raw_text = self._gather_raw_text(list(range(len(chunks))), chunks)

        # Build context about previous sections
        context_str = ""
        if previous_headings:
            context_str = (
                f"## Sections Already Written (do NOT repeat this content)\n"
                + "\n".join(f"- {h}" for h in previous_headings)
                + "\n\n"
            )

        user_msg = (
            f"{context_str}"
            f"## Section Outline\n"
            f"```json\n{json.dumps(section_outline, indent=2)}\n```\n\n"
            f"## Relevant Scanner Data\n\n"
            f"```json\n{json.dumps(relevant_data, indent=2)}\n```\n\n"
            f"## Raw Transcript Text\n\n{raw_text}"
        )
        response = self.text_llm.chat(BLOG_SECTION_WRITER_SYSTEM_PROMPT, user_msg)
        return response.strip()

    # -- Stage 4: Blog Finalizer --

    def finalize_section(
        self,
        section_outline: dict,
        written_text: str,
        scanner_outputs: list[dict],
        chunks: list[ContentChunk],
    ) -> str:
        """Compare written section against source material, fill gaps."""
        chunk_indices = section_outline.get("scanner_chunks", [])
        relevant_data = [scanner_outputs[i] for i in chunk_indices if i < len(scanner_outputs)]
        if not relevant_data:
            relevant_data = scanner_outputs

        raw_text = self._gather_raw_text(chunk_indices, chunks)
        if not raw_text:
            raw_text = self._gather_raw_text(list(range(len(chunks))), chunks)

        user_msg = (
            f"## Written Section (to review and enhance)\n\n{written_text}\n\n"
            f"## Section Outline\n"
            f"```json\n{json.dumps(section_outline, indent=2)}\n```\n\n"
            f"## Scanner Data\n\n"
            f"```json\n{json.dumps(relevant_data, indent=2)}\n```\n\n"
            f"## Raw Transcript Text\n\n{raw_text}"
        )
        response = self.text_llm.chat(BLOG_FINALIZER_SYSTEM_PROMPT, user_msg)
        return response.strip()

    # -- Full pipeline --

    def run(self, doc: ContentDocument, save_dir: str | None = None) -> list[tuple[str, str]]:
        """
        Full pipeline: scan → split topics → write sections → finalize.

        Returns a list of (filename_slug, content) tuples — one per topic.
        If save_dir is provided, saves every intermediate step.
        """
        # Stage 1: Scan
        print(f"[Blog] Stage 1: Scanning {len(doc.chunks)} chunks...")
        scanner_outputs = self.scan_all(doc)
        _save_step(save_dir, "1_scanner_outputs.json", scanner_outputs)

        # Stage 2: Topic Splitter
        print(f"[Blog] Stage 2: Splitting into topics...")
        topic_plan = self.split_topics(scanner_outputs, doc)
        _save_step(save_dir, "2_topic_plan.json", topic_plan)
        topics = topic_plan.get("topics", [])
        print(f"  [Splitter] Found {len(topics)} topic(s): "
              + ", ".join(t.get('title', '?') for t in topics))
        if topic_plan.get("split_rationale"):
            print(f"  [Splitter] Rationale: {topic_plan['split_rationale']}")

        results: list[tuple[str, str]] = []

        for t_idx, topic in enumerate(topics):
            title = topic.get("title", f"Topic {t_idx + 1}")
            tags = topic.get("tags", [])
            sections = topic.get("sections", [])
            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:60]

            print(f"\n[Blog] === Topic {t_idx + 1}/{len(topics)}: {title} ===")

            # Stage 3: Write each section
            print(f"[Blog] Stage 3: Writing {len(sections)} sections...")
            written_parts: list[str] = []
            previous_headings: list[str] = []

            for s_idx, section in enumerate(sections):
                heading = section.get("heading", f"Section {s_idx + 1}")
                weight = section.get("estimated_weight", "medium")
                print(f"  [Writer] Section {s_idx + 1}/{len(sections)}: {heading} ({weight})")

                section_text = self.write_section(
                    section, scanner_outputs, doc.chunks, previous_headings,
                )
                written_parts.append(section_text)
                previous_headings.append(heading)

            _save_step(save_dir, f"3_sections_draft_{slug}.json", [
                {"heading": s.get("heading", f"Section {i+1}"), "text": t}
                for i, (s, t) in enumerate(zip(sections, written_parts))
            ])

            # Stage 4: Finalize each section
            print(f"[Blog] Stage 4: Finalizing {len(sections)} sections...")
            final_parts: list[str] = []

            for s_idx, (section, written_text) in enumerate(zip(sections, written_parts)):
                heading = section.get("heading", f"Section {s_idx + 1}")
                print(f"  [Finalizer] Section {s_idx + 1}/{len(sections)}: {heading}")

                final_text = self.finalize_section(
                    section, written_text, scanner_outputs, doc.chunks,
                )
                final_parts.append(final_text)

            _save_step(save_dir, f"4_sections_final_{slug}.json", [
                {"heading": s.get("heading", f"Section {i+1}"), "draft": d, "final": f}
                for i, (s, d, f) in enumerate(zip(sections, written_parts, final_parts))
            ])

            # Stitch: title + tags + all finalized sections
            tags_line = f"Tags:{','.join(tags)}" if tags else "Tags:General"
            final_doc = f"{title}\n{tags_line}\n"
            for part in final_parts:
                final_doc += f"\n{part}\n"

            results.append((slug, final_doc))

            print(f"[Blog] Topic '{title}' done — {len(sections)} sections.")

        print(f"\n[Blog] Pipeline complete. Generated {len(results)} document(s).")
        return results


# ---------------------------------------------------------------------------
# Helper: build ContentDocument from a plain-text doc file
# ---------------------------------------------------------------------------

def load_document_as_content(
    doc_path: str,
    title: str = "Untitled",
    max_chunk_words: int = 4000,
) -> ContentDocument:
    """Load a documentation/article .txt/.md file as a ContentDocument."""
    with open(doc_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    raw_chunks = chunk_transcript(full_text, max_words=max_chunk_words)

    chunks = [
        ContentChunk(
            text=text,
            chunk_index=i,
            total_chunks=len(raw_chunks),
            source_metadata={"source_type": "documentation"},
        )
        for i, text in enumerate(raw_chunks)
    ]

    return ContentDocument(
        title=title,
        source_type=SourceType.DOCUMENTATION,
        chunks=chunks,
    )


# ---------------------------------------------------------------------------
# Helper: build ContentDocument from a transcript file
# ---------------------------------------------------------------------------

def load_transcript_as_document(
    transcript_path: str,
    title: str = "Untitled",
    total_duration: str | None = None,
    max_chunk_words: int = 4000,
) -> ContentDocument:
    """Load a transcript .txt file and prepare it as a ContentDocument."""
    with open(transcript_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    raw_chunks = chunk_transcript(full_text, max_words=max_chunk_words)

    chunks = [
        ContentChunk(
            text=text,
            chunk_index=i,
            total_chunks=len(raw_chunks),
            source_metadata={"source_type": "video_transcript"},
        )
        for i, text in enumerate(raw_chunks)
    ]

    return ContentDocument(
        title=title,
        source_type=SourceType.VIDEO_TRANSCRIPT,
        chunks=chunks,
        total_duration=total_duration,
    )
