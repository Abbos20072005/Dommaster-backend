"""Gemini calls through the official `google-genai` SDK. Tests mock `generate` / `generate_stream`."""
import logging

from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

TIMEOUT_MS = 30_000

_client = None


class AssistantError(Exception):
    """Gemini gave no answer (not configured, timeout, API error)."""


def client():
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise AssistantError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    return _client


def generate(contents, config):
    """One whole response (`GenerateContentResponse`)."""
    try:
        return client().models.generate_content(model=settings.GEMINI_MODEL, contents=contents, config=config)
    except AssistantError:
        raise
    except Exception as error:  # the SDK raises its APIError, httpx timeouts, pydantic errors
        logger.exception("gemini generate_content failed")
        raise AssistantError(str(error)[:500]) from error


def generate_stream(contents, config):
    """The response in chunks (each a `GenerateContentResponse`)."""
    try:
        yield from client().models.generate_content_stream(
            model=settings.GEMINI_MODEL, contents=contents, config=config)
    except AssistantError:
        raise
    except Exception as error:
        logger.exception("gemini generate_content_stream failed")
        raise AssistantError(str(error)[:500]) from error
