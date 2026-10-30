"""Upload a PDF to Google Gemini via the File API."""
from google import genai


def upload_pdf_to_gemini(client: genai.Client, pdf_path: str):
    """Upload PDF and return a Gemini file object for use in prompts.

    Args:
        client: A google.genai.Client instance.
        pdf_path: Path to the local PDF file.

    Returns:
        A Gemini file object that can be passed directly to generate_content.
    """
    gemini_file = client.files.upload(file=pdf_path)
    return gemini_file
