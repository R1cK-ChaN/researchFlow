"""OpenRouter client — thin wrapper around the OpenAI SDK."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def openrouter_client(api_key: str | None = None) -> OpenAI:
    """Return an OpenAI-SDK client configured for OpenRouter.

    API key resolution order: explicit argument > OPENROUTER_API_KEY env var.
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OpenRouter API key not set. Pass api_key=... or set OPENROUTER_API_KEY."
        )
    return OpenAI(api_key=key, base_url=OPENROUTER_BASE_URL)


def openrouter_headers(http_referer: str | None, app_title: str | None) -> dict[str, Any]:
    """OpenRouter optional attribution headers (leaderboard / routing hints)."""
    headers: dict[str, Any] = {}
    if http_referer:
        headers["HTTP-Referer"] = http_referer
    if app_title:
        headers["X-Title"] = app_title
    return headers
