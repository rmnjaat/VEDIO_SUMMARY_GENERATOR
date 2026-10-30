"""FastAPI backend — serves the pipeline with SSE progress and provider selection."""

import json
import os
import tempfile
import asyncio
from pathlib import Path
from queue import Queue

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv

from pipeline import run_pipeline
from providers import get_registry

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Manual → Video Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/providers")
async def list_providers():
    """List all available providers for TTS, Image, and Video."""
    # Force provider setup by importing pipeline setup
    from google import genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        client = genai.Client(api_key=api_key)
        from pipeline import _setup_providers
        _setup_providers(client)

    registry = get_registry()
    return {
        "tts": registry.list_tts(),
        "image": registry.list_image(),
        "video": registry.list_video(),
    }


@app.post("/api/generate")
async def generate_video_endpoint(
    pdf: UploadFile | None = File(None),
    url: str = Form(""),
    raw_text: str = Form(""),
    tts_provider: str = Form(""),
    image_provider: str = Form(""),
    video_provider: str = Form(""),
):
    """Run the full pipeline with SSE progress streaming.

    Accepts: PDF upload, URL, or raw text + optional provider overrides.
    Returns: Server-Sent Events with per-stage progress, then final result.
    """
    source = None
    temp_path = None

    if pdf and pdf.filename:
        suffix = Path(pdf.filename).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await pdf.read()
            tmp.write(content)
            temp_path = tmp.name
        source = temp_path
    elif url.strip():
        source = url.strip()
    elif raw_text.strip():
        source = raw_text.strip()
    else:
        raise HTTPException(400, "Provide a PDF file, URL, or raw text.")

    # Build provider config from form
    provider_config = {}
    if tts_provider.strip():
        provider_config["tts"] = tts_provider.strip()
    if image_provider.strip():
        provider_config["image"] = image_provider.strip()
    if video_provider.strip():
        provider_config["video"] = video_provider.strip()

    progress_queue: Queue = Queue()

    def on_progress(stage: str, detail: str = ""):
        progress_queue.put({"stage": stage, "detail": detail})

    async def event_stream():
        loop = asyncio.get_event_loop()

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = loop.run_in_executor(
                pool, lambda: run_pipeline(
                    source,
                    output_dir="outputs",
                    on_progress=on_progress,
                    provider_config=provider_config or None,
                )
            )

            # Stream progress while pipeline runs
            while not future.done():
                await asyncio.sleep(0.3)
                while not progress_queue.empty():
                    msg = progress_queue.get()
                    yield f"data: {json.dumps(msg)}\n\n"

            # Drain remaining
            while not progress_queue.empty():
                msg = progress_queue.get()
                yield f"data: {json.dumps(msg)}\n\n"

            try:
                result = future.result()
                done_msg = {
                    "stage": "done",
                    "result": {
                        "video_path": result.get("video_path", ""),
                        "scenes": result.get("scenes", []),
                        "changelog": result.get("changelog", []),
                        "metadata": result.get("metadata", {}),
                    }
                }
                yield f"data: {json.dumps(done_msg)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'stage': 'error', 'detail': str(e)})}\n\n"
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/download-video")
async def download_video():
    """Download the final generated video."""
    video_path = Path(__file__).resolve().parent / "outputs" / "final_video.mp4"
    if not video_path.exists():
        raise HTTPException(404, "No video generated yet.")
    return FileResponse(video_path, media_type="video/mp4", filename="instruction_video.mp4")


@app.get("/api/outputs/{filename}")
async def get_output_file(filename: str):
    """Serve a saved output JSON file."""
    out_dir = Path(__file__).resolve().parent / "outputs"
    file_path = out_dir / filename

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename}")

    if filename.endswith(".mp4"):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)

    with open(file_path) as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
