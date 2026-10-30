"""Fetch the HTML content of a URL."""
import httpx


def fetch_url_html(url: str, timeout: int = 30) -> str:
    """GET request and return the HTML body as a string."""
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    return response.text
