"""End-to-end orchestrator: context → generate → post-process → validate.

A pure function intentionally decoupled from HTTP / sibling services.
The server wires sibling-service calls and topic resolution; this module
only cares about prepared inputs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from researchflow.context import BlockInputs, Context, ContextParams
from researchflow.eval.harness import _write_artifacts
from researchflow.eval.runners import (
    run_context,
    run_generation,
    run_postprocess,
    run_validation,
)
from researchflow.generation.contracts import GeneratorParams, Report
from researchflow.validation.contracts import ValidationReport


class StageSummary(BaseModel):
    stage: str
    ok: bool
    metrics: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class FlowResult(BaseModel):
    run_id: str
    context: Context
    report: Report
    validation: ValidationReport
    stage_summary: list[StageSummary]
    run_dir: str | None = None


def run_research_flow(
    block_inputs: BlockInputs,
    params: ContextParams,
    recipe: str,
    *,
    generator_client: Any,
    judge_client: Any | None = None,
    generator_params: GeneratorParams | None = None,
    disclaimer: str | None = None,
    runs_dir: Path | None = None,
    run_id: str | None = None,
) -> FlowResult:
    """Run all four pipeline stages over prepared `BlockInputs`.

    When `runs_dir` is given, every stage's inputs/outputs/trace are
    written under `runs_dir/<run_id>/` for audit — same artifact tree as
    the eval harness. Otherwise the flow runs purely in-memory.
    """
    run_id = run_id or _default_run_id()
    run_dir = runs_dir / run_id if runs_dir is not None else None

    # The eval runners read inputs from a Fixture-like object. Build a thin
    # shim: `run_context` accepts anything with `.recipe`, `.params`, `.inputs`.
    fixture_shim = _FixtureShim(
        recipe=recipe,
        params=params.model_dump(mode="json"),
        inputs=_dump_block_inputs(block_inputs),
    )

    context, ctx_artifacts = run_context(fixture_shim)
    _maybe_write(run_dir, "01_context", ctx_artifacts)

    report, gen_artifacts = run_generation(
        context, client=generator_client, params=generator_params
    )
    _maybe_write(run_dir, "02_generation", gen_artifacts)

    finalized, pp_artifacts = run_postprocess(report, disclaimer=disclaimer)
    _maybe_write(run_dir, "03_postprocess", pp_artifacts)

    vr, val_artifacts = run_validation(
        finalized, context, judge_client=judge_client
    )
    _maybe_write(run_dir, "04_validation", val_artifacts)

    stage_summary = [
        StageSummary(
            stage="context",
            ok=not context.trace.notes,
            metrics={
                "blocks_rendered": context.trace.blocks_rendered,
                "token_estimate": context.trace.total_token_estimate,
            },
        ),
        StageSummary(
            stage="generation",
            ok=bool(report.raw_text),
            metrics={
                "usage": report.trace.usage,
                "fact_citations": report.fact_citations,
            },
        ),
        StageSummary(stage="postprocess", ok=True, metrics={}),
        StageSummary(
            stage="validation",
            ok=vr.passed,
            metrics={
                "error_count": len(vr.errors()),
                "warning_count": len(vr.warnings()),
                "validators_run": vr.validators_run,
                "validators_skipped": vr.validators_skipped,
            },
        ),
    ]

    result = FlowResult(
        run_id=run_id,
        context=context,
        report=finalized,
        validation=vr,
        stage_summary=stage_summary,
        run_dir=str(run_dir) if run_dir else None,
    )
    if run_dir is not None:
        (run_dir / "flow_summary.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "recipe": recipe,
                    "stage_summary": [s.model_dump() for s in stage_summary],
                    "validation_passed": vr.passed,
                    "fact_citations": finalized.fact_citations,
                },
                indent=2,
            )
        )
    return result


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S_") + uuid4().hex[:6]


def _maybe_write(run_dir: Path | None, stage: str, artifacts: dict[str, str]) -> None:
    if run_dir is None:
        return
    _write_artifacts(run_dir / stage, artifacts)


def _dump_block_inputs(bi: BlockInputs) -> dict:
    return {
        "brief": bi.brief.model_dump(mode="json"),
        "data_pack": bi.data_pack.model_dump(mode="json") if bi.data_pack else None,
        "material_pack": bi.material_pack.model_dump(mode="json") if bi.material_pack else None,
        "house_view": bi.house_view.model_dump(mode="json") if bi.house_view else None,
        "extras": bi.extras,
    }


class _FixtureShim:
    """Mini adapter that satisfies the surface eval.runners.run_context uses."""

    def __init__(self, *, recipe: str, params: dict, inputs: dict):
        self.recipe = recipe
        self.params = params
        # run_context passes `fixture.inputs` directly into _build_block_inputs,
        # which accepts a raw dict keyed on brief / data_pack / …
        self.inputs = {k: v for k, v in inputs.items() if v is not None}
