"""Single-call generator: Context -> Report via OpenRouter."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Protocol

from researchflow.context.contracts import Context
from researchflow.generation.contracts import GenerationTrace, GeneratorParams, Report
from researchflow.generation.prompts import SYSTEM_PROMPT
from researchflow.generation.provider import openrouter_client, openrouter_headers

_CITATION_RE = re.compile(r"\[(F-[A-Z0-9][A-Z0-9\-_]*)\]")


class _ChatClient(Protocol):
    """Minimal interface the generator needs. Enables test doubles."""

    def chat_completions_create(self, **kwargs): ...  # pragma: no cover


def generate(
    context: Context,
    params: GeneratorParams | None = None,
    *,
    client=None,
) -> Report:
    """Generate a report from a built Context.

    `client` is injectable for tests; production path builds one from env.
    """
    params = params or GeneratorParams()
    started = datetime.now(timezone.utc)

    if client is None:
        client = openrouter_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": context.rendered_text},
    ]
    extra_headers = openrouter_headers(params.http_referer, params.app_title)

    kwargs = {
        "model": params.model,
        "messages": messages,
        "temperature": params.temperature,
        "max_tokens": params.max_tokens,
    }
    if params.top_p is not None:
        kwargs["top_p"] = params.top_p
    if extra_headers:
        kwargs["extra_headers"] = extra_headers

    response = client.chat.completions.create(**kwargs)
    finished = datetime.now(timezone.utc)

    choice = response.choices[0]
    raw_text = choice.message.content or ""
    citations = _extract_citations(raw_text)

    usage = {}
    if getattr(response, "usage", None) is not None:
        usage = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
            "total_tokens": getattr(response.usage, "total_tokens", 0) or 0,
        }

    trace = GenerationTrace(
        model=params.model,
        started_at=started,
        finished_at=finished,
        usage=usage,
        request_id=getattr(response, "id", None),
    )
    return Report(
        recipe_name=context.recipe_name,
        raw_text=raw_text,
        fact_citations=citations,
        trace=trace,
    )


def _extract_citations(text: str) -> list[str]:
    """Extract unique fact ids from a generated report, preserving order."""
    seen: dict[str, None] = {}
    for m in _CITATION_RE.finditer(text):
        seen.setdefault(m.group(1), None)
    return list(seen)
