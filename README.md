# Video Summary Generator

Convert long video lectures (3-4 hours) into clean transcripts and structured notes.

## Prerequisites

- Python 3.10+
- ffmpeg (required for audio extraction)

Install ffmpeg:
```bash
brew install ffmpeg
```

## Setup

### 1. Clone the repo and navigate to the project

```bash
cd /Users/ramanjangu/Desktop/VEDIO_SUMMARY_GENERATOR
```

### 2. Create a virtual environment

```bash
python -m venv VEDIO_SUMMARY_GENERATOR_env
```

### 3. Activate the virtual environment

```bash
source VEDIO_SUMMARY_GENERATOR_env/bin/activate
```

To deactivate later:
```bash
deactivate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure API keys

Copy the example env file and add your keys:
```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:
```
GROQ_API_KEY=your_groq_api_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API keys from:
- Groq: https://console.groq.com
- AssemblyAI: https://www.assemblyai.com/dashboard
- Gemini: https://aistudio.google.com/app/apikey

## Usage

```bash
python main.py <video_path> --provider <groq|assemblyai|gemini>
```

### Examples

**Using Groq (free, fast):**
```bash
python main.py "./VEID/12.mp4" --provider groq
```

**Using AssemblyAI (best for large files):**
```bash
python main.py "./VEID/12.mp4" --provider assemblyai
```

**Using Gemini:**
```bash
python main.py "./VEID/12.mp4" --provider gemini
```

## Output

Transcripts are saved in the `output/` folder:

```
output/
  12_transcript.txt        # Plain text transcript
  12_timestamps.txt        # Transcript with [HH:MM:SS] timestamps
```

## Available Providers

| Provider | Max File Size | Speed | Notes |
|----------|--------------|-------|-------|
| Groq | 25MB per chunk (auto-split) | Fast | Free tier available |
| AssemblyAI | No practical limit | Medium | Handles large files natively |
| Gemini | Varies | Medium | Requires Google AI Studio key |

## Project Structure

```
VEDIO_SUMMARY_GENERATOR/
├── main.py                          # Entry point
├── .env                             # API keys (do not commit)
├── .env.example                     # Example env file
├── requirements.txt                 # Python dependencies
├── output/                          # Generated transcripts
└── src/
    ├── video_source.py              # Video loading, audio extraction, chunking
    ├── transcript_generator.py      # Main orchestrator
    └── providers/
        ├── base.py                  # Abstract base class
        ├── groq_provider.py         # Groq Whisper provider
        ├── assemblyai_provider.py   # AssemblyAI provider
        └── gemini_provider.py       # Gemini provider
```
