"""Streamlit UI for Manual to Instruction Video Generator."""
import streamlit as st
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

from stage1_ingestion.detector import detect_input_type
from stage1_ingestion.pdf_uploader import upload_pdf_to_gemini
from stage1_ingestion.url_fetcher import fetch_url_html
from stage2_extraction.extractor import extract_structure
from stage2_extraction.validator import validate_structure
from stage3_script.generator import generate_script
from stage4_images.imagen import generate_image
from stage4_images.fallback_slide import create_fallback_slide
from stage5_audio.tts import generate_audio
from stage6_video.assembler import assemble_video

load_dotenv()

st.set_page_config(page_title="Manual to Video", layout="wide")
st.title("Manual to Instruction Video Generator")

# Sidebar
with st.sidebar:
    api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    if api_key:
        genai.configure(api_key=api_key)

# Input form
input_type = st.radio("Input source", ["Upload PDF", "Paste URL"])

uploaded_file = None
url = ""
if input_type == "Upload PDF":
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
else:
    url = st.text_input("URL")

col1, col2, col3 = st.columns(3)
with col1:
    product_name = st.text_input("Product Name")
with col2:
    brand = st.text_input("Brand")
with col3:
    model = st.text_input("Model Number")

metadata = {"product_name": product_name, "brand": brand, "model": model}

if st.button("Generate Instruction Video", type="primary"):
    if not api_key:
        st.error("Please enter your Gemini API key in the sidebar.")
        st.stop()

    progress = st.empty()
    status_container = st.container()

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("temp/images", exist_ok=True)
    os.makedirs("temp/audio", exist_ok=True)

    # Stage 1
    with status_container:
        st.write("Stage 1: Preparing input...")
    if uploaded_file:
        tmp_path = os.path.join("temp", uploaded_file.name)
        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        content = upload_pdf_to_gemini(tmp_path)
    elif url:
        content = fetch_url_html(url)
    else:
        st.error("Please upload a PDF or enter a URL.")
        st.stop()
    with status_container:
        st.write("Stage 1: Input prepared")

    # Stage 2
    with status_container:
        st.write("Stage 2: Extracting content...")
    structure = extract_structure(content, metadata)
    errors = validate_structure(structure)
    section_count = len(structure.get("sections", []))
    step_count = sum(len(s.get("steps", [])) for s in structure.get("sections", []))
    with status_container:
        st.write(f"Stage 2: Extracted {section_count} sections, {step_count} steps")

    # Stage 3
    with status_container:
        st.write("Stage 3: Generating script...")
    scenes = generate_script(structure, metadata)
    with status_container:
        st.write(f"Stage 3: Script ready — {len(scenes)} scenes")

    # Stage 4
    img_progress = st.progress(0, text="Stage 4: Generating images...")
    for i, scene in enumerate(scenes):
        img_path = os.path.join("temp/images", f"scene_{scene['scene_id']}.png")
        try:
            generate_image(scene["visual_hint"], img_path)
        except Exception:
            create_fallback_slide(scene.get("narration", "")[:80], img_path)
        img_progress.progress((i + 1) / len(scenes), text=f"Stage 4: Image {i+1}/{len(scenes)}")

    # Stage 5
    with status_container:
        st.write("Stage 5: Generating audio...")
    for scene in scenes:
        audio_path = os.path.join("temp/audio", f"scene_{scene['scene_id']}.mp3")
        generate_audio(scene["narration"], audio_path)
    with status_container:
        st.write("Stage 5: Audio done")

    # Stage 6
    with status_container:
        st.write("Stage 6: Assembling video...")
    video_path = "outputs/final_video.mp4"
    assemble_video(scenes, "temp/images", "temp/audio", video_path)
    with status_container:
        st.write("Stage 6: Video ready!")

    # Download button
    with open(video_path, "rb") as f:
        st.download_button("Download Video", f.read(), file_name="final_video.mp4", mime="video/mp4")
