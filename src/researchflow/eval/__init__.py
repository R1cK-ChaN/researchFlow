"""Evaluation harness — runs the full flow over fixtures and scores each stage.

The harness lives outside the production flow: it exercises
context/generation/postprocess/validation stages on recorded inputs,
writes per-stage artifacts for audit, and computes per-stage scores
against fixture-declared expectations.
"""

from researchflow.eval.contracts import (
    Expected,
    Fixture,
    FixtureScorecard,
    RunSummary,
    StageScore,
)
from researchflow.eval.harness import run_all, run_fixture

__all__ = [
    "Expected",
    "Fixture",
    "FixtureScorecard",
    "RunSummary",
    "StageScore",
    "run_all",
    "run_fixture",
]
