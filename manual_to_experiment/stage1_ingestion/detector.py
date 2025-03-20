"""Detect whether the user input is a PDF file, URL, or plain text."""
import os


def detect_input_type(source: str) -> str:
    if os.path.isfile(source) and source.lower().endswith(".pdf"):
        return "pdf"
    if source.startswith("http://") or source.startswith("https://"):
        return "url"
    return "text"
