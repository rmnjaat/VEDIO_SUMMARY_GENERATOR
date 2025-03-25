"""FastAPI backend — serves the pipeline as a REST API with SSE progress updates."""

import json
import os
import tempfile
import asyncio
from pathlib import Path
from queue import Queue

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from pipeline import run_pipeline

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Manual → Script Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/generate")
async def generate_script_endpoint(
    pdf: UploadFile | None = File(None),
    url: str = Form(""),
    raw_text: str = Form(""),
):
    """
    Run the full pipeline (Stages 1-3.5) and stream progress via SSE.

    Accepts one of: PDF file upload, URL, or raw text.
    Gemini auto-detects product name, brand, and model from the document.
    Returns Server-Sent Events with progress updates, then the final result.
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

    progress_queue = Queue()

    def on_progress(stage, detail=""):
        progress_queue.put({"stage": stage, "detail": detail})

    async def event_stream():
        """Run pipeline in a thread and yield SSE events."""
        loop = asyncio.get_event_loop()

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = loop.run_in_executor(
                pool, run_pipeline, source, "gemini-2.0-flash", on_progress
            )

            # Poll for progress while pipeline runs
            while not future.done():
                await asyncio.sleep(0.3)
                while not progress_queue.empty():
                    msg = progress_queue.get()
                    yield f"data: {json.dumps(msg)}\n\n"

            # Drain remaining progress messages
            while not progress_queue.empty():
                msg = progress_queue.get()
                yield f"data: {json.dumps(msg)}\n\n"

            try:
                result = future.result()
                # Send final result
                yield f"data: {json.dumps({'stage': 'done', 'result': result})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'stage': 'error', 'detail': str(e)})}\n\n"
            finally:
                # Cleanup temp file
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/outputs/{filename}")
async def get_output_file(filename: str):
    """Serve a saved output JSON file."""
    out_dir = Path(__file__).resolve().parent / "outputs"
    file_path = out_dir / filename

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename}")

    with open(file_path) as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
