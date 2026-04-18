"""Shared helper for LLM-based validators.

Calls an OpenAI-compatible chat client, expects the model to return a JSON
object of shape `{"violations": [...]}` and returns the list. On parse
failure the list contains a single sentinel violation so the calling
validator can emit an INFO issue rather than crash the pipeline.
"""

from __future__ import annotations

import json
from typing import Any

DEFAULT_JUDGE_MODEL = "anthropic/claude-haiku-4.5"
PARSE_ERROR_SENTINEL = "_judge_parse_error"


def run_judge(
    client: Any,
    *,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: float = 0.0,
    max_tokens: int = 2000,
) -> list[dict]:
    """Call the LLM and return the parsed list of violation dicts."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    raw = response.choices[0].message.content or ""
    return _parse(raw)


def _parse(raw: str) -> list[dict]:
    # Strip common fence artifacts before parsing.
    trimmed = raw.strip()
    if trimmed.startswith("```"):
        trimmed = trimmed.strip("`").lstrip()
        if trimmed.lower().startswith("json"):
            trimmed = trimmed[4:].lstrip()
    try:
        payload = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        return [{PARSE_ERROR_SENTINEL: True, "detail": str(exc), "raw": raw[:500]}]
    if not isinstance(payload, dict):
        return [{PARSE_ERROR_SENTINEL: True, "detail": "top-level not object", "raw": raw[:500]}]
    violations = payload.get("violations", [])
    if not isinstance(violations, list):
        return [{PARSE_ERROR_SENTINEL: True, "detail": "violations not list", "raw": raw[:500]}]
    return [v for v in violations if isinstance(v, dict)]
