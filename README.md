# Video Summary Generator

End-to-end pipeline that converts long video lectures (3-4+ hours) into clean transcripts, structured content trees, documentation pages, and comprehensive blog posts.

Two-tier architecture:
1. **Transcription** — Extract audio from video, transcribe via pluggable providers (Groq, AssemblyAI, Gemini, MLX local)
2. **Analysis** — Process transcripts through AI-driven pipelines that extract, structure, and generate various output formats

## Architecture

```
Video File (.mp4, .mkv, .avi, .mov, .webm)
    |
    v
[main.py] ── VideoSource ── Audio Extraction (ffmpeg) ── Chunking
    |
    v
[Provider Selection]
    |── GroqProvider      (Whisper large-v3, 24MB chunks, fast, free tier)
    |── AssemblyAIProvider (Universal-3-pro, 2.2GB, no chunking needed)
    |── GeminiProvider    (Gemini 1.5 Pro, file upload API)
    |__ MLXProvider       (Whisper large-v3, local on Apple Silicon, no API key)
    |
    v
output/transcripts/
    |── 12_transcript.txt       (plain text)
    |__ 12_timestamps.txt       ([HH:MM:SS] timestamped lines)
    |
    v
[analyze.py] ── Load transcript ── Chunk (4000 words, 200 overlap) ── ContentDocument
    |
    v
[Pipeline Selection]
    |
    |── --mode tree   AnalysisPipeline (2-stage)
    |     Scanner (per chunk) --> Architect --> JSON content tree
    |
    |── --mode doc    DocWriterPipeline (3-stage)
    |     Scanner --> Outliner --> Section Writer --> plain-text doc page
    |
    |__ --mode blog   BlogWriterPipeline (4-stage)
          Scanner --> Topic Splitter --> Section Writer --> Finalizer
                                                          |
                                                          v
                                                  N blog files (one per major topic)
    |
    v
output/generated/<title>_<mode>_<YYYYMMDD_HHMMSS>/
    |── content_tree.json    (tree mode)
    |── doc.txt              (doc mode)
    |── lsm_trees.txt        (blog mode — file per topic)
    |__ youtube_arch.txt     (blog mode — file per topic)
```

## Pipelines in Detail

### AnalysisPipeline (`--mode tree`)

| Stage | Agent | What it does | Output |
|-------|-------|-------------|--------|
| 1 | Scanner | Extracts topics, concepts, Q&A, problems, transitions per chunk | JSON per chunk |
| 2 | Architect | Merges, deduplicates, builds hierarchical content tree | Single JSON file |

### DocWriterPipeline (`--mode doc`)

| Stage | Agent | What it does | Output |
|-------|-------|-------------|--------|
| 1 | Scanner | Same extraction as above | JSON per chunk |
| 2 | Outliner | Plans document skeleton — headings, section mapping | JSON outline |
| 3 | Section Writer | Writes one section at a time (avoids quality degradation) | Plain text per section |

Produces Kafka-style documentation: title, tags, clean headings, no markdown.

### BlogWriterPipeline (`--mode blog`)

| Stage | Agent | What it does | Output |
|-------|-------|-------------|--------|
| 1 | Scanner | Same extraction as above | JSON per chunk |
| 2 | Topic Splitter | Identifies N major topics, plans separate outlines per topic | JSON with N topic outlines |
| 3 | Section Writer | Writes each section using scanner data + raw transcript | Plain text per section |
| 4 | Finalizer | Compares written text against source, fills gaps, adds examples | Final polished text |

Key features:
- Splits into separate files when transcript covers multiple unrelated topics
- Section Writer receives raw transcript text (not just scanner data) so nothing is lost
- Finalizer catches anything the writer missed
- Adds clarifying examples and supplementary context
- Blog-style: short paragraphs, clear headings, no wall-of-text

## Prerequisites

- Python 3.10+
- ffmpeg (audio extraction)

```bash
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
```

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv VEDIO_SUMMARY_GENERATOR_env
source VEDIO_SUMMARY_GENERATOR_env/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env with your keys
```

API keys needed:
| Key | Get it from | Used by |
|-----|------------|---------|
| `GROQ_API_KEY` | https://console.groq.com | Groq Whisper transcription |
| `ASSEMBLYAI_API_KEY` | https://www.assemblyai.com/dashboard | AssemblyAI transcription |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey | Gemini transcription + all analysis pipelines |

## Usage

### Step 1: Transcribe a video

```bash
python main.py "./VEID/12.mp4" --provider groq
```

Output lands in `output/transcripts/`:
```
output/transcripts/
  12_transcript.txt       # Plain text
  12_timestamps.txt       # [HH:MM:SS] timestamped
```

### Step 2: Analyze the transcript

```bash
# JSON content tree (topics, concepts, Q&A, glossary)
python analyze.py output/transcripts/12_timestamps.txt --mode tree --title "LSM Trees" --duration "04:00:00"

# Kafka-style documentation page
python analyze.py output/transcripts/12_timestamps.txt --mode doc --title "LSM Trees" --duration "04:00:00"

# Comprehensive blog posts (splits by topic)
python analyze.py output/transcripts/12_timestamps.txt --mode blog --title "LSM Trees" --duration "04:00:00"
```

Each run creates its own folder:
```
output/generated/
  lsm_trees_blog_20260319_143022/
    lsm_trees_explained.txt
    youtube_architecture.txt
    senior_engineer_mindset.txt
  lsm_trees_tree_20260319_150500/
    content_tree.json
```

### CLI Options

```
python analyze.py <transcript> --mode <tree|doc|blog> [options]

Options:
  --title, -t        Title for the content (default: inferred from filename)
  --duration, -d     Total duration HH:MM:SS (default: unknown)
  --chunk-size       Max words per chunk (default: 4000)
  --model            Gemini model to use (default: gemini-2.5-flash)
  --output-dir, -o   Override output directory
```

### Viewing Results

Open `viewer.html` in a browser to browse all generated files with a styled preview UI:
- Blog posts and docs render with formatted headings, tag pills, example callouts
- JSON content trees render as expandable interactive trees
- Timestamps render with color-coded time codes
- Search and filter across all files

## Output Directory Structure

```
output/
  transcripts/                              # main.py stores transcripts here
    <video>_transcript.txt
    <video>_timestamps.txt
    .temp_audio/                            # Audio chunks (auto-generated)

  generated/                                # analyze.py stores results here
    manifest.json                           # Auto-updated index for viewer.html
    <title>_<mode>_<datetime>/              # One folder per run
      content_tree.json                     # (tree mode)
      doc.txt                               # (doc mode)
      <topic_slug>.txt                      # (blog mode, one per topic)
```

## Transcription Providers

| Provider | Max Size | Speed | API Key | Best For |
|----------|----------|-------|---------|----------|
| Groq | 24 MB/chunk (auto-split) | Fast | Required | Quick transcription, free tier |
| AssemblyAI | 2.2 GB (no split needed) | Medium | Required | Large files, high accuracy |
| Gemini | 2 GB (file upload API) | Medium | Required | Already using Gemini ecosystem |
| MLX | 500 MB/chunk | Variable | None | Offline/local on Apple Silicon |

## Project Structure

```
VEDIO_SUMMARY_GENERATOR/
|
|-- main.py                          # Entry: video -> transcript
|-- analyze.py                       # Entry: transcript -> tree/doc/blog
|-- generate_doc.py                  # Entry: transcript -> doc (standalone)
|-- analyze_doc.py                   # Entry: existing doc -> JSON tree
|-- viewer.html                      # Browser UI for viewing all outputs
|
|-- src/                             # Transcription layer
|   |-- video_source.py              # Video loading, ffmpeg audio extraction, chunking
|   |-- transcript_generator.py      # Orchestrator: extract -> transcribe -> save
|   |__ providers/
|       |-- base.py                  # Abstract TranscriptionProvider + TranscriptResult
|       |-- groq_provider.py         # Groq Whisper (rate-limited, cached)
|       |-- assemblyai_provider.py   # AssemblyAI (universal model)
|       |-- gemini_provider.py       # Gemini file upload API
|       |__ mlx_provider.py          # MLX Whisper (local, Apple Silicon)
|
|-- personafication/                 # Analysis layer
|   |-- source_schema.py            # ContentDocument, ContentChunk, SourceType
|   |-- backends.py                  # GeminiBackend (JSON), GeminiTextBackend (text)
|   |-- pipeline.py                  # All pipeline classes (Analysis, DocWriter, BlogWriter, DocAnalysis)
|   |__ prompts.py                   # All system prompts (Scanner, Architect, Outliner, etc.)
|
|-- output/                          # All generated artifacts
|   |-- transcripts/                 # Raw transcripts from main.py
|   |__ generated/                   # Analysis outputs, one folder per run
|
|-- .env.example                     # Template for API keys
|__ requirements.txt                 # Python dependencies
```

## How the Analysis Prompts Work

Each pipeline stage uses a persona-based system prompt:

| Prompt | Persona | Role |
|--------|---------|------|
| `SCANNER_SYSTEM_PROMPT` | "The Scanner" — meticulous academic indexer | Extract every signal from each transcript chunk |
| `ARCHITECT_SYSTEM_PROMPT` | "The Architect" — curriculum designer | Merge scanner outputs into hierarchical tree |
| `DOC_OUTLINER_SYSTEM_PROMPT` | "The Outliner" | Plan document skeleton with section mapping |
| `DOC_SECTION_WRITER_SYSTEM_PROMPT` | "The Section Writer" | Write one doc section at a time |
| `BLOG_TOPIC_SPLITTER_SYSTEM_PROMPT` | "The Topic Splitter" | Identify and separate major topics |
| `BLOG_SECTION_WRITER_SYSTEM_PROMPT` | "The Blog Section Writer" | Write blog sections with examples, using raw transcript |
| `BLOG_FINALIZER_SYSTEM_PROMPT` | "The Blog Finalizer" | Compare written text against source, fill gaps |

The LLM backend is provider-agnostic (`LLMBackend` abstract class). Currently uses Gemini, but can be swapped to OpenAI, Anthropic, or any other provider by implementing the `chat()` method.
