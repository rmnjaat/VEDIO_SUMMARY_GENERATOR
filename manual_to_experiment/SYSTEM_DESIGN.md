# System Design: Manual → Instruction Video

---

## Full System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI                             │
│                                                                 │
│   [Upload PDF]  or  [Paste URL]                                 │
│   Product Name: ________  Brand: ________  Model: ________     │
│                  [ Generate Video ]                             │
│                                                                 │
│   Progress:                                                     │
│   ✓ Stage 1: Input prepared                                     │
│   ✓ Stage 2: Content extracted (12 steps found)                 │
│   ✓ Stage 3: Script generated (14 scenes)                       │
│   ⟳ Stage 4: Generating images... (6/14)                        │
│   ○ Stage 5: Generating audio                                   │
│   ○ Stage 6: Assembling video                                   │
│                                                                 │
│   [ Download Video ]                                            │
└─────────────────────────────────────────────────────────────────┘
         │
         │ user submits form
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1 — Input Preparation                                    │
│                                                                 │
│  PDF path ──► genai.upload_file() ──► gemini_file_object        │
│  URL       ──► httpx.get()        ──► raw HTML string           │
│  Text      ──────────────────────► plain string                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2 — Extraction  [1 Gemini call]                          │
│                                                                 │
│  Input:  gemini_file / html / text  +  EXTRACTION_PROMPT        │
│  Model:  gemini-2.0-flash                                       │
│                                                                 │
│  Output: structured_data.json                                   │
│  {                                                              │
│    sections: [                                                  │
│      { title, type, steps: [                                    │
│          { step_number, title, description,                     │
│            warning, image_hint }                                │
│      ]}                                                         │
│    ]                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 3 — Script Generation  [1 Gemini call]                   │
│                                                                 │
│  Input:  structured_data.json  +  SCRIPT_PROMPT                 │
│  Model:  gemini-2.0-flash                                       │
│                                                                 │
│  Output: scene_script.json                                      │
│  [                                                              │
│    { scene_id, type, narration,                                 │
│      visual_hint, estimated_duration_sec },                     │
│    ...                                                          │
│  ]                                                              │
└─────────────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────┐
         ▼                         ▼
┌─────────────────┐     ┌─────────────────────────┐
│   STAGE 4       │     │   STAGE 5               │
│   Images        │     │   Audio (TTS)           │
│                 │     │                         │
│  visual_hint    │     │  narration text         │
│      │          │     │      │                  │
│      ▼          │     │      ▼                  │
│  Imagen 3       │     │  Google TTS             │
│  (via Gemini)   │     │  (or ElevenLabs)        │
│      │          │     │      │                  │
│      ▼          │     │      ▼                  │
│  scene_N.png    │     │  scene_N.mp3            │
│  1920x1080      │     │  + actual duration      │
└────────┬────────┘     └───────────┬─────────────┘
         │                          │
         └──────────┬───────────────┘
                    ▼
         ┌─────────────────────────┐
         │   STAGE 6               │
         │   Video Assembly        │
         │                         │
         │  for each scene:        │
         │    image + audio        │
         │    → video clip         │
         │                         │
         │  all clips → concat     │
         │  add subtitles          │
         │  → final.mp4            │
         └───────────┬─────────────┘
                     │
                     ▼
              outputs/final.mp4
              (user downloads)
```

---

## How Gemini Reads Images from the PDF

When a PDF is uploaded via the File API, Gemini processes every page visually — not just the text layer.

```
PDF Page (as Gemini sees it)
┌────────────────────────────────┐
│  STEP 3: Connect the hose      │  ← text (read normally)
│                                │
│  [diagram: hose connecting     │  ← Gemini SEES this diagram
│   to back of machine]          │     reads labels, arrows
│                                │     understands what it shows
│  ⚠ Do not overtighten          │  ← warning box (read + flagged)
└────────────────────────────────┘
```

**What Gemini extracts from images in the PDF:**
- Text labels on diagrams ("inlet valve", "drain hose")
- Arrows showing direction or connection
- Warning symbols and their associated text
- Product part numbers shown in exploded diagrams
- Colour coding (red = danger, yellow = caution)

**How this feeds into image_hint:**
Gemini generates `image_hint` based on what it actually saw:
```
"image_hint": "diagram showing blue cold water hose connecting to
               back-left inlet of washing machine, arrow pointing
               to connection point"
```

This is far more specific than if we had just passed text — because Gemini saw the original diagram.

---

## How Images Are Generated (Stage 4)

Each scene's `visual_hint` is sent to **Imagen 3** (Google's image model — uses your Gemini credits).

### Flow per scene

```
scene.visual_hint
       │
       ▼
  build image prompt
  (add style instructions)
       │
       ▼
  Imagen 3 API call
       │
       ▼
  1920x1080 PNG
  saved to temp/images/scene_N.png
```

### Image prompt construction

The raw `visual_hint` is wrapped with style instructions:

```
visual_hint: "hands removing red bolts from back of washing machine"

full image prompt sent to Imagen 3:
"Instructional product photography style. Clean white background.
 Professional, clear, well-lit. No text overlays.
 Hands removing red transport bolts from the back panel of a white washing machine.
 Realistic, educational, suitable for a how-to video."
```

### Image resolution
- **1920 x 1080** (Full HD, 16:9) — standard video frame size
- All images same size → no resizing needed in video assembly

### Fallback if image generation fails
- Create a simple slide: white background + step title text (using Pillow)
- Always have something to show — never a blank frame

### PDF images as an alternative source
For steps where Gemini found a relevant diagram in the PDF:
- The `image_hint` will reference it specifically
- Imagen 3 will recreate it as a clean illustration
- OR: extract the actual page image from PDF and use it directly (PyMuPDF fallback)

---

## How the Script Frames the Video

### Scene-to-frame mapping

```
scene_script.json          audio file         image file         video clip
─────────────────          ──────────         ──────────         ──────────
scene 0  (intro)    →   scene_0.mp3  +  scene_0.png   →  clip_0.mp4  (6s)
scene 1  (step 1)   →   scene_1.mp3  +  scene_1.png   →  clip_1.mp4  (12s)
scene 2  (step 2)   →   scene_2.mp3  +  scene_2.png   →  clip_2.mp4  (9s)
...
scene 14 (outro)    →   scene_14.mp3 +  scene_14.png  →  clip_14.mp4 (5s)

all clips concatenated
+ fade transitions between clips
+ subtitle track (from narration text)
─────────────────────────────────────
→  outputs/final.mp4
```

### How clip duration is determined

1. Stage 3 gives `estimated_duration_sec` (word count / 2.2 words per sec)
2. Stage 5 generates the actual `.mp3` audio
3. Stage 6 reads the actual audio duration — **this overrides the estimate**
4. Image is held for exactly as long as the audio plays

```python
# Stage 6 logic
audio_clip = AudioFileClip("scene_1.mp3")
actual_duration = audio_clip.duration        # e.g. 11.4 seconds
image_clip = ImageClip("scene_1.png").set_duration(actual_duration)
video_clip = image_clip.set_audio(audio_clip)
```

### Subtitle generation

Narration text from each scene → burned into the video as subtitles:
- White text, black outline, bottom-center position
- Font size 36px, max 2 lines visible at once
- Synced to audio start/end of each scene

---

## Minimal UI Design (Streamlit)

### Why Streamlit
- Pure Python — no HTML/CSS/JS needed
- Built-in file uploader, progress indicators, download button
- Runs locally, no server setup

### UI Layout

```
┌──────────────────────────────────────────────────────┐
│  🎬  Manual → Instruction Video Generator            │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Input source                                        │
│  ( ) Upload PDF file   ( ) Paste a URL               │
│                                                      │
│  [  Choose PDF file  ]                               │
│   — or —                                             │
│  URL: [ https://...                              ]   │
│                                                      │
│  ──────────────────────────────────────              │
│  Product Name:  [                          ]         │
│  Brand:         [                          ]         │
│  Model Number:  [                          ]         │
│                                                      │
│  [       Generate Instruction Video        ]         │
│                                                      │
├──────────────────────────────────────────────────────┤
│  Progress                                            │
│  ✓  Stage 1: Input prepared                          │
│  ✓  Stage 2: Extracted 3 sections, 11 steps          │
│  ✓  Stage 3: Script ready — 13 scenes                │
│  ⟳  Stage 4: Generating images (5 / 13)...           │
│  ○  Stage 5: Audio generation                        │
│  ○  Stage 6: Video assembly                          │
├──────────────────────────────────────────────────────┤
│  [ ⬇ Download final_video.mp4 ]                      │
└──────────────────────────────────────────────────────┘
```

### Streamlit file: `app.py`

```
app.py
  ├── sidebar: API key input (GEMINI_API_KEY)
  ├── main panel: input form
  ├── on submit:
  │     run stage1() → show ✓
  │     run stage2() → show ✓ + step count
  │     run stage3() → show ✓ + scene count
  │     run stage4() → show progress bar (image N of total)
  │     run stage5() → show ✓
  │     run stage6() → show ✓
  └── show download button
```

---

## Complete File & Folder Structure

```
manual_to_experiment/
│
├── PLAN.md                      # stages 1-3 detailed plan
├── SYSTEM_DESIGN.md             # this file
├── requirements.txt
├── .env                         # GEMINI_API_KEY=...
│
├── app.py                       # Streamlit UI entry point
├── pipeline.py                  # orchestrates all 6 stages
│
├── stage1_ingestion/
│   ├── __init__.py
│   ├── detector.py              # detect_input_type(source)
│   ├── pdf_uploader.py          # upload_pdf_to_gemini(path)
│   └── url_fetcher.py           # fetch_url_html(url)
│
├── stage2_extraction/
│   ├── __init__.py
│   ├── extractor.py             # extract_structure(content, metadata)
│   ├── prompts.py               # EXTRACTION_PROMPT
│   └── validator.py             # validate_structure(json)
│
├── stage3_script/
│   ├── __init__.py
│   ├── generator.py             # generate_script(structure, metadata)
│   └── prompts.py               # SCRIPT_PROMPT
│
├── stage4_images/
│   ├── __init__.py
│   ├── imagen.py                # generate_image(visual_hint) → path
│   └── fallback_slide.py        # text slide if Imagen fails
│
├── stage5_audio/
│   ├── __init__.py
│   └── tts.py                   # generate_audio(narration) → path, duration
│
├── stage6_video/
│   ├── __init__.py
│   ├── assembler.py             # assemble clips → final.mp4
│   └── subtitles.py             # burn subtitles onto clips
│
├── outputs/
│   ├── structured_data.json     # Stage 2 output
│   ├── scene_script.json        # Stage 3 output
│   └── final_video.mp4          # final output
│
└── temp/
    ├── images/
    │   ├── scene_0.png
    │   ├── scene_1.png
    │   └── ...
    └── audio/
        ├── scene_0.mp3
        ├── scene_1.mp3
        └── ...
```

---

## APIs & Models Used

| Purpose | API / Service | Model |
|---|---|---|
| PDF reading + content extraction | Google Gemini | `gemini-2.0-flash` |
| Script generation | Google Gemini | `gemini-2.0-flash` |
| Image generation | Google Imagen | `imagen-3.0-generate-001` |
| Text-to-speech | Google Cloud TTS | `en-US-Neural2-F` (female) |
| Video assembly | moviepy (local) | — |
| URL fetching | httpx (local) | — |

**All Google — one API key, one billing account (your Gemini credits).**

---

## End-to-End Example Run

```
Input:
  source   = "bosch_wm_manual.pdf"
  name     = "Series 6 Washing Machine"
  brand    = "Bosch"
  model    = "WAU28PH0GB"

Stage 1:  PDF uploaded to Gemini → gemini_file_object
Stage 2:  Gemini reads 87-page PDF → 3 sections, 11 steps (8 sec)
Stage 3:  Gemini writes script → 13 scenes including intro/outro (3 sec)
Stage 4:  Imagen 3 generates 13 images @ 1920x1080 (45 sec)
Stage 5:  Google TTS generates 13 audio clips (15 sec)
Stage 6:  moviepy assembles → final_video.mp4, 1:52 total length (10 sec)

Total time: ~80 seconds
Output: outputs/final_video.mp4
```

---

## requirements.txt (all 6 stages)

```
google-generativeai>=0.8.0      # Gemini + Imagen
google-cloud-texttospeech        # Google TTS
httpx>=0.27.0                    # URL fetching
playwright>=1.44.0               # JS-rendered URLs (optional)
moviepy>=1.0.3                   # video assembly
Pillow>=10.0.0                   # fallback image slides
python-dotenv>=1.0.0             # .env for API key
streamlit>=1.35.0                # UI
```
