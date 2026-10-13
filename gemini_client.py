"""Small Gemini client used by DataChat Copilot.

The application uses Google's Gemini Developer API. A free-tier Gemini model
can be used without adding billing, subject to Google's current quota limits.
"""
import os

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-3.5-flash-lite"


def get_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def is_configured() -> bool:
    return bool(get_api_key())


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
    max_output_tokens: int = 1024,
) -> str:
    """Generate text using Gemini and return only the response text."""
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. Add GEMINI_API_KEY to your "
            ".env file or enter it in the DataChat sidebar."
        )

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
    temperature=temperature,
    max_output_tokens=max_output_tokens,
    system_instruction=system_instruction,
)

    try:
        response = client.models.generate_content(
            model=model or DEFAULT_MODEL,
            contents=prompt,
            config=config,
        )
    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        if "429" in message or "quota" in lowered or "rate limit" in lowered:
            raise RuntimeError(
                "Gemini free-tier quota/rate limit was reached. Wait a little "
                "and try again, or check your Gemini API quota."
            ) from exc
        if "api key" in lowered or "authentication" in lowered or "unauthenticated" in lowered:
            raise RuntimeError(
                "Gemini API key was rejected. Check the key in your .env file "
                "or the sidebar."
            ) from exc
        raise RuntimeError(f"Gemini request failed: {message}") from exc

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return text.strip()
