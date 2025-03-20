"""Upload a PDF to Google Gemini via the File API."""
import google.generativeai as genai


def upload_pdf_to_gemini(pdf_path: str):
    """Upload PDF and return a Gemini file object for use in prompts."""
    gemini_file = genai.upload_file(pdf_path, mime_type="application/pdf")
    return gemini_file
