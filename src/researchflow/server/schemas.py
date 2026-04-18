"""Request/response schemas for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from researchflow.context.contracts import Brief


class ResearchParams(BaseModel):
    language: Literal["en", "zh_cn", "zh_hk"] = "en"
    reader_tier: Literal["trading_desk", "pm", "broad_client"] = "pm"
    extras: dict[str, Any] = Field(default_factory=dict)


class ResearchRequest(BaseModel):
    """Primary request. Callers send only what they naturally know."""

    topic: str = Field(..., description="Free-form topic, e.g. 'US CPI March 2026'")
    recipe: str = Field(..., description="Packaged recipe name")
    params: ResearchParams = Field(default_factory=ResearchParams)
    # Library-mode escape hatch; when set, resolver + sibling fetches are skipped.
    inputs_override: dict[str, Any] | None = None


class StageOutcome(BaseModel):
    stage: str
    ok: bool
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    run_id: str
    resolved_brief: Brief
    report: dict[str, Any]
    validation: dict[str, Any]
    stage_summary: list[StageOutcome]
    run_dir: str | None = None


class ResolveRequest(BaseModel):
    topic: str


class ResolveResponse(BaseModel):
    brief: Brief | None = None
    confidence: float = 0.0
    candidates: list[str] = Field(default_factory=list)
    source: str = "unknown"


class RecipesResponse(BaseModel):
    recipes: list[str]


class HealthResponse(BaseModel):
    status: str = "ok"
    dependencies: dict[str, bool] = Field(default_factory=dict)
