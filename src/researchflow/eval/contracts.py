"""Contracts for fixtures, stage scores, and run summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Expected(BaseModel):
    """Fixture-level expectations. Each sub-block is optional; the harness
    scores only the stages with expectations declared."""

    context: dict[str, Any] = Field(default_factory=dict)
    report: dict[str, Any] = Field(default_factory=dict)
    postprocess: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)


class Fixture(BaseModel):
    """A self-contained evaluation case.

    `inputs` is the kwargs bag fed into the context builder (brief,
    data_pack, house_view, extras). `mock_responses` are canned LLM outputs
    consumed in order by generator then judges; when running live, set
    `mock_responses=[]` and the harness uses a real client.
    """

    id: str
    tags: list[str] = Field(default_factory=list)
    recipe: str
    params: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any]
    expected: Expected = Field(default_factory=Expected)
    mock_responses: list[str] = Field(default_factory=list)
    # Optional inline gold text (or path relative to fixture dir).
    gold_report_inline: str | None = None
    gold_report_path: str | None = None


class StageScore(BaseModel):
    stage: str
    passed: bool
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class FixtureScorecard(BaseModel):
    fixture_id: str
    overall_passed: bool
    stages: list[StageScore]


class RunSummary(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime
    git_commit: str | None = None
    fixtures: list[FixtureScorecard]

    @property
    def pass_rate(self) -> float:
        if not self.fixtures:
            return 0.0
        return sum(1 for f in self.fixtures if f.overall_passed) / len(self.fixtures)
