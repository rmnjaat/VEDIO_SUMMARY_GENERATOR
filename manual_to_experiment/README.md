# Manual → Instruction Video Generator

Takes a product manual (PDF, URL, or text) as input and produces a narrated instruction video (MP4) as output. Fully automated — no human editing needed.

---

## System Design

### Architecture Overview

```
                           ┌──────────────┐
                           │   React UI   │
                           │  (frontend)  │
                           └──────┬───────┘
                                  │ POST /api/generate
                                  ▼
                           ┌──────────────┐
                           │  FastAPI      │
                           │  (server.py)  │
                           └──────┬───────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PIPELINE ORCHESTRATOR                       │
│                        (pipeline.py)                            │
│                                                                 │
│  ┌─────────┐  ┌─────────────────────────────────────────────┐  │
│  │ Stage 1 │  │ Stage 2: 3 Gemini calls                     │  │
│  │ Ingest  │→ │ 2.0: Extract → 2.5: Verify → 2.7: Enrich  │  │
│  └─────────┘  └───────────────────┬─────────────────────────┘  │
│                                   ▼                             │
│               ┌─────────────────────────────────────────────┐  │
│               │ Stage 3: 2 Gemini calls                     │  │
│               │ 3.0: Script → 3.5: Review                   │  │
│               └───────────────────┬─────────────────────────┘  │
│                                   ▼                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            PLUGGABLE PROVIDER LAYER                       │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │  Stage 4     │  │  Stage 5     │  │  Stage 6         │  │  │
│  │  │  ImageProv.  │  │  TTSProv.    │  │  VideoProv.      │  │  │
│  │  │  ─────────── │  │  ─────────── │  │  ─────────────── │  │  │
│  │  │  • Imagen 3  │  │  • XTTS v2   │  │  • Remotion      │  │  │
│  │  │  • Fallback  │  │  • (add more)│  │  • (add more)    │  │  │
│  │  │  • (add more)│  │              │  │                   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                   │                             │
│                                   ▼                             │
│                          outputs/final_video.mp4                │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
INPUT (PDF / URL / Text)
  │
  ├─► Stage 1:   Prepare input (upload PDF or fetch URL)
  │
  ├─► Stage 2:   Gemini reads document → structured JSON         [Call 1]
  │                 auto-detects: product name, brand, model
  │
  ├─► Stage 2.5: Gemini re-reads doc, verifies extraction        [Call 2]
  │                 catches: hallucinated, missing, inaccurate steps
  │
  ├─► Stage 2.7: Gemini enriches with prerequisites + complexity  [Call 3]
  │                 splits complex steps (score 4-5) into sub-steps
  │
  ├─► Stage 3:   Gemini converts steps → spoken narration scenes  [Call 4]
  │                 adds: intro, prerequisites, transitions, outro
  │
  ├─► Stage 3.5: Gemini reviews script for quality                [Call 5]
  │                 fixes: tone, pacing, duration, missing warnings
  │
  ├─► Stage 4:   Image generation (1 per scene)
  │                 provider: Imagen 3 (default) or Pillow fallback
  │
  ├─► Stage 5:   Audio / TTS generation (1 per scene)
  │                 provider: Coqui XTTS v2 (default, local, free)
  │
  └─► Stage 6:   Video assembly (all scenes → MP4)
                    provider: Remotion (default, local, free)

OUTPUT: outputs/final_video.mp4
```

### Why 5 Gemini Calls (Not 2)

| Call | What it does | What it catches |
|------|-------------|-----------------|
| 1. Extract | Reads manual → structured JSON | — |
| 2. Verify | Re-reads document, checks extraction | Hallucinated steps, missing steps, wrong descriptions |
| 3. Enrich | Adds prerequisites, complexity scores | Missing tools/parts, complex steps that need splitting |
| 4. Script | Writes spoken narration per scene | — |
| 5. Review | Polishes script for quality | Tone drift, bad pacing, lost warnings, visual mismatches |

Cost: ~$0.03 total per manual (Gemini 2.0 Flash). Quality jump is significant.

---

## Tech Stack

| Component | Tool | Cost | Runs on |
|-----------|------|------|---------|
| Extraction (Stages 1-3.5) | Gemini 2.0 Flash | Gemini credits | Cloud (Google API) |
| Image generation (Stage 4) | Gemini Imagen 3 | Gemini credits | Cloud (Google API) |
| Voice / TTS (Stage 5) | Coqui XTTS v2 | Free | Local (GPU recommended) |
| Video assembly (Stage 6) | Remotion | Free | Local (Node.js) |
| Backend | FastAPI | Free | Local |
| Frontend | React + Vite | Free | Local |

---

## Pluggable Provider Architecture

Stages 4, 5, and 6 use a **provider pattern** — each stage has an abstract interface, and concrete implementations can be swapped at runtime.

### How it works

```
providers/
├── base.py              # Abstract interfaces: TTSProvider, ImageProvider, VideoProvider
├── registry.py          # ProviderRegistry — register + select providers at runtime
├── tts_xtts.py          # Coqui XTTS v2 implementation
├── image_imagen.py      # Google Imagen 3 implementation
├── image_fallback.py    # Pillow text slides (always works)
└── video_remotion.py    # Remotion implementation
```

### Adding a new provider

Example: adding ElevenLabs TTS

```python
# providers/tts_elevenlabs.py
from providers.base import TTSProvider

class ElevenLabsProvider(TTSProvider):
    def __init__(self, api_key: str, voice_id: str = "default"):
        self.api_key = api_key
        self.voice_id = voice_id

    def generate(self, text: str, output_path: str, **kwargs) -> tuple[str, float]:
        # Your ElevenLabs implementation here
        ...
        return output_path, duration
```

Then register it:

```python
from providers import get_registry
from providers.tts_elevenlabs import ElevenLabsProvider

registry = get_registry()
registry.register_tts("elevenlabs", ElevenLabsProvider(api_key="..."))
registry.set_active_tts("elevenlabs")  # switch to it
```

### Available provider interfaces

| Interface | Method | Input | Output |
|-----------|--------|-------|--------|
| `TTSProvider` | `generate(text, output_path)` | narration text | `(path, duration_sec)` |
| `ImageProvider` | `generate(prompt, output_path)` | visual_hint text | `path` |
| `VideoProvider` | `render(scenes, images_dir, audio_dir, output_path)` | all assets | `path` |

### Current implementations

| Provider | Type | Local? | Free? |
|----------|------|--------|-------|
| `XTTSProvider` | TTS | Yes | Yes |
| `ImagenProvider` | Image | No (API) | Credits |
| `FallbackSlideProvider` | Image | Yes | Yes |
| `RemotionProvider` | Video | Yes | Yes |

### Possible future providers

| Provider | Type | Notes |
|----------|------|-------|
| ElevenLabs | TTS | Better voice quality, paid |
| Edge TTS | TTS | Microsoft, free, cloud |
| Piper TTS | TTS | Very fast, local |
| Stable Diffusion | Image | Local, needs GPU |
| DALL-E 3 | Image | OpenAI, paid |
| MoviePy | Video | Python-only, simpler |
| FFmpeg | Video | CLI-based, minimal |

---

## Folder Structure

```
manual_to_experiment/
│
├── pipeline.py                  # Orchestrator — runs all 6 stages
├── server.py                    # FastAPI backend (REST + SSE)
├── requirements.txt             # Python dependencies
│
├── providers/                   # Pluggable AI provider layer
│   ├── base.py                  #   Abstract: TTSProvider, ImageProvider, VideoProvider
│   ├── registry.py              #   Register + select providers at runtime
│   ├── tts_xtts.py              #   Coqui XTTS v2 (local, free)
│   ├── image_imagen.py          #   Google Imagen 3 (cloud)
│   ├── image_fallback.py        #   Pillow text slides (always works)
│   └── video_remotion.py        #   Remotion (local, free)
│
├── stage1_ingestion/            # Input preparation
│   ├── detector.py              #   Auto-detect: PDF vs URL vs text
│   ├── pdf_uploader.py          #   Upload PDF to Gemini File API
│   └── url_fetcher.py           #   Fetch URL via httpx
│
├── stage2_extraction/           # Content extraction + verification
│   ├── extractor.py             #   Call 1: raw extraction
│   ├── verifier.py              #   Call 2: verification + grounding
│   ├── enricher.py              #   Call 3: prerequisites + complexity
│   ├── prompts.py               #   All Stage 2 prompts
│   └── validator.py             #   JSON parsing + schema validation
│
├── stage3_script/               # Script generation + review
│   ├── generator.py             #   Call 4: scene script generation
│   ├── reviewer.py              #   Call 5: script review + polish
│   └── prompts.py               #   All Stage 3 prompts
│
├── stage4_images/               # Image generation implementations
│   ├── imagen.py                #   Gemini Imagen 3
│   └── fallback_slide.py        #   Pillow text slides
│
├── stage5_audio/                # TTS implementations
│   └── tts.py                   #   Coqui XTTS v2
│
├── stage6_video/                # Video rendering implementations
│   └── renderer.py              #   Remotion CLI wrapper
│
├── remotion-video/              # Remotion React project
│   ├── src/
│   │   ├── ManualVideo.tsx      #   Main video composition
│   │   ├── scenes/              #   IntroScene, StepScene, TransitionScene, OutroScene
│   │   └── components/          #   KenBurnsImage, AnimatedSubtitle, ProgressBar
│   └── public/                  #   Images + audio copied here at render time
│
├── frontend/                    # React UI (Vite)
│   └── src/
│       ├── App.jsx
│       └── components/          #   InputForm, ProgressTracker, ScriptResults
│
├── assets/                      # Reference voice for XTTS v2
│   └── reference_voice.wav      #   3-10 sec voice sample (you provide)
│
├── outputs/                     # All intermediate + final outputs (gitignored)
│   ├── structured_data_raw.json
│   ├── verification_result.json
│   ├── structured_data_verified.json
│   ├── structured_data_final.json
│   ├── scene_script_draft.json
│   ├── scene_script_final.json
│   ├── scene_script_with_durations.json
│   └── final_video.mp4
│
└── temp/                        # Intermediate files (gitignored)
    ├── images/                  #   scene_N.png
    └── audio/                   #   scene_N.wav
```

---

## How Each Stage Works

### Stage 1: Input Preparation

No AI. Just gets the input ready for Gemini.

- **PDF** → uploaded to Gemini File API (Gemini reads text + images + scanned pages natively)
- **URL** → fetched via `httpx.get()`, raw HTML passed to Gemini (Gemini ignores nav/footer/ads)
- **Text** → passed directly

No pdfplumber, no BeautifulSoup. Gemini handles all parsing.

### Stage 2: Raw Extraction [Gemini Call 1]

Gemini reads the entire document and returns structured JSON:
- Auto-detects product name, brand, model number
- Extracts sections (setup, operation, maintenance, troubleshooting)
- Extracts ordered steps with descriptions, warnings, visual hints
- Ignores legal, warranty, specs, ToC

### Stage 2.5: Verification [Gemini Call 2]

Gemini re-reads the original document alongside the extraction and checks:
- Is each step real (verified) or invented (hallucinated)?
- Are descriptions accurate or distorted?
- Are there steps in the manual that were missed?
- For each verified step, quotes the source text as proof

Then `apply_verification()` removes hallucinated steps, fixes inaccurate ones, and adds missing ones.

### Stage 2.7: Enrichment [Gemini Call 3]

Gemini enriches the verified data:
- Extracts all **prerequisites** (tools, parts, conditions needed before starting)
- Scores each step **1-5 for complexity**
- **Splits** steps scoring 4-5 into 2-3 simpler sub-steps

### Stage 3: Script Generation [Gemini Call 4]

Converts structured data into a spoken narration script:
- Each step becomes one scene
- Adds: intro scene, "what you'll need" scene, section transitions, outro
- Tone: friendly, conversational, spoken English
- Each scene: 2-3 sentences, 5-15 seconds

### Stage 3.5: Script Review [Gemini Call 5]

Reviews the script for production quality:
- Tone consistency (no drift between casual and formal)
- Duration balance (no scene > 20s or < 3s)
- Visual-narration alignment (visual_hint matches narration)
- Warning preservation (cross-checks all warnings are present)
- Smooth transitions between sections

### Stage 4: Image Generation

Uses the active `ImageProvider` to generate one image per scene from `visual_hint`.

Default: **Gemini Imagen 3** (1920x1080 instructional photography style).
Fallback: **Pillow text slides** (styled dark background with step title).

### Stage 5: Audio / TTS

Uses the active `TTSProvider` to generate speech for each scene's narration.

Default: **Coqui XTTS v2** (voice cloning from a reference .wav file).
- Splits long narrations into sentences for better quality
- Concatenates sentence audio into one clip per scene
- Returns actual duration (overrides the estimated duration)

### Stage 6: Video Assembly

Uses the active `VideoProvider` to combine images + audio → final MP4.

Default: **Remotion** (React-based programmatic video):
- Ken Burns effect (slow zoom/pan on images)
- Animated subtitles (fade-in text at bottom)
- Progress bar (step N of total)
- Section labels (top-left)
- Fade transitions between scenes

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Conda (for virtual environment)
- `GEMINI_API_KEY` in `.env`
- A `reference_voice.wav` in `assets/` (3-10 seconds of clear speech)

### Install

```bash
# Create and activate conda environment
conda create -n video_summary_generator python=3.11 -y
conda activate video_summary_generator

# Install Python dependencies
cd manual_to_experiment
pip install -r requirements.txt
pip install google-genai

# Install Remotion dependencies
cd remotion-video && npm install && cd ..

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Run

```bash
# Terminal 1: Backend
conda activate video_summary_generator
cd manual_to_experiment
python server.py

# Terminal 2: Frontend
cd manual_to_experiment/frontend
npm run dev

# Or run directly via CLI:
conda activate video_summary_generator
cd manual_to_experiment
python pipeline.py "/path/to/manual.pdf"
```

---

## Intermediate Output Files

Every stage saves its output to `outputs/`. You can re-run any stage independently.

| File | Stage | Description |
|------|-------|-------------|
| `structured_data_raw.json` | 2 | First extraction (may have errors) |
| `verification_result.json` | 2.5 | Verification report (hallucinated/missing/inaccurate) |
| `structured_data_verified.json` | 2.5 | Extraction after fixes applied |
| `structured_data_final.json` | 2.7 | Enriched (prerequisites, complexity, sub-steps) |
| `scene_script_draft.json` | 3 | First script draft |
| `scene_script_final.json` | 3.5 | Polished script after review |
| `scene_script_with_durations.json` | 5 | Script with actual audio durations |
| `final_video.mp4` | 6 | Final output video |

---

## Scalability

### Horizontal scaling

The provider pattern enables horizontal scaling:

1. **Multiple AI backends** — swap providers without changing pipeline logic
2. **Parallel image generation** — Stage 4 can generate images concurrently (each scene is independent)
3. **Parallel audio generation** — Stage 5 scenes are independent, can be parallelized
4. **Queue-based processing** — server.py can be placed behind a task queue (Celery, Redis) for handling multiple concurrent requests

### Adding new providers

Each provider is a single file implementing one method. To add support for a new TTS engine, image generator, or video renderer:

1. Create a class extending the base interface (`TTSProvider`, `ImageProvider`, or `VideoProvider`)
2. Register it in the `ProviderRegistry`
3. Set it as active via `registry.set_active_*(name)`

No changes needed to `pipeline.py` or any other stage.

### Configuration

Provider selection can be driven by:
- Environment variables (`IMAGE_PROVIDER=imagen3`)
- CLI flags (`python pipeline.py --tts=elevenlabs source.pdf`)
- API request parameters (`{ "tts_provider": "xtts_v2" }`)
- Frontend dropdown (select provider in the UI)
