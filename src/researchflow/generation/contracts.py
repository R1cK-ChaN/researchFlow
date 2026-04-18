"""Contracts for the generator."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class GeneratorParams(BaseModel):
    """Knobs for a single LLM call via OpenRouter."""

    model: str = "anthropic/claude-sonnet-4.5"
    temperature: float = 0.3
    max_tokens: int = 4000
    top_p: float | None = None
    # Optional OpenRouter routing/attribution headers.
    http_referer: str | None = None
    app_title: str | None = "researchFlow"


class GenerationTrace(BaseModel):
    model: str
    started_at: datetime
    finished_at: datetime
    usage: dict[str, int] = Field(default_factory=dict)
    request_id: str | None = None
    notes: list[str] = Field(default_factory=list)

    @classmethod
    def start(cls, model: str) -> "GenerationTrace":
        now = datetime.now(timezone.utc)
        return cls(model=model, started_at=now, finished_at=now)


class Report(BaseModel):
    """Raw LLM output plus extracted metadata. Validation is downstream."""

    recipe_name: str
    raw_text: str
    fact_citations: list[str] = Field(default_factory=list)
    trace: GenerationTrace
    extras: dict[str, Any] = Field(default_factory=dict)
