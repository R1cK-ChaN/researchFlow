"""Stage runners. Each returns (stage_output, artifacts) for audit writing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from researchflow.context import (
    BlockInputs,
    Brief,
    Context,
    ContextParams,
    DataPack,
    HouseView,
    MaterialPack,
    build,
)
from researchflow.context.contracts import RenderedBlock
from researchflow.eval.contracts import Fixture
from researchflow.generation import GeneratorParams, Report, generate
from researchflow.validation import ValidationReport, post_process, validate


def run_context(fixture: Fixture) -> tuple[Context, dict[str, str]]:
    inputs = _build_block_inputs(fixture.inputs)
    params = ContextParams(**fixture.params)
    ctx = build(fixture.recipe, params, inputs)
    artifacts = {
        "inputs.json": json.dumps(_serializable(fixture.inputs), indent=2, ensure_ascii=False),
        "params.json": params.model_dump_json(indent=2),
        "output.xml": ctx.rendered_text,
        "trace.json": ctx.trace.model_dump_json(indent=2),
        "blocks.json": json.dumps(
            [_rendered_block_dump(b) for b in ctx.blocks], indent=2, ensure_ascii=False
        ),
    }
    return ctx, artifacts


def run_generation(
    context: Context,
    *,
    client: Any,
    params: GeneratorParams | None = None,
) -> tuple[Report, dict[str, str]]:
    params = params or GeneratorParams(model="mock/replay")
    report = generate(context, params, client=client)
    artifacts = {
        "prompt_user.xml": context.rendered_text,
        "output.md": report.raw_text,
        "trace.json": report.trace.model_dump_json(indent=2),
        "fact_citations.json": json.dumps(report.fact_citations, indent=2),
    }
    return report, artifacts


def run_postprocess(
    report: Report, *, disclaimer: str | None = None
) -> tuple[Report, dict[str, str]]:
    finalized = post_process(report, disclaimer=disclaimer)
    artifacts = {
        "input.md": report.raw_text,
        "output.md": finalized.raw_text,
    }
    return finalized, artifacts


def run_validation(
    report: Report,
    context: Context,
    *,
    judge_client: Any | None = None,
    configs: dict[str, dict] | None = None,
) -> tuple[ValidationReport, dict[str, str]]:
    vr = validate(report, context, judge_client=judge_client, configs=configs)
    artifacts = {
        "input.md": report.raw_text,
        "report.json": vr.model_dump_json(indent=2),
    }
    return vr, artifacts


def _build_block_inputs(raw: dict[str, Any]) -> BlockInputs:
    brief = Brief(**raw["brief"])
    data_pack = DataPack(**raw["data_pack"]) if "data_pack" in raw else None
    if data_pack is not None and "event_id" not in raw["data_pack"]:
        data_pack = DataPack(event_id=brief.event_id, payload=raw["data_pack"].get("payload", raw["data_pack"]))
    material_pack = None
    if "material_pack" in raw:
        mp_raw = raw["material_pack"]
        material_pack = MaterialPack(event_id=mp_raw.get("event_id", brief.event_id), payload=mp_raw.get("payload", {}))
    house_view = HouseView(**raw["house_view"]) if "house_view" in raw else None
    extras = raw.get("extras", {})
    return BlockInputs(
        brief=brief,
        data_pack=data_pack,
        material_pack=material_pack,
        house_view=house_view,
        extras=extras,
    )


def _rendered_block_dump(b: RenderedBlock) -> dict:
    return {"name": b.name, "token_estimate": b.token_estimate, "trace": b.trace}


def _serializable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serializable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    return obj
