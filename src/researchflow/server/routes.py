"""HTTP routes. Keeps wiring shallow: resolve → fetch → run_research_flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from researchflow.clients import HttpMacroDataClient, HttpRagClient
from researchflow.context import BlockInputs, ContextParams, DataPack, HouseView, MaterialPack
from researchflow.context.contracts import Brief
from researchflow.context.recipe_loader import load_recipe
from researchflow.flow import run_research_flow
from researchflow.generation.contracts import GeneratorParams
from researchflow.server.persistence import read_artifact, read_flow_summary
from researchflow.server.resources import load_exemplars, load_framework
from researchflow.server.schemas import (
    HealthResponse,
    RecipesResponse,
    ResearchRequest,
    ResearchResponse,
    ResolveRequest,
    ResolveResponse,
    StageOutcome,
)


def build_router(auth_dep) -> APIRouter:
    router = APIRouter()

    @router.post("/v1/research", response_model=ResearchResponse)
    def research(req: ResearchRequest, request: Request, _=Depends(auth_dep)):
        deps = request.app.state.deps
        block_inputs, resolved_brief = _resolve_and_fetch(req, deps)
        params = ContextParams(**req.params.model_dump())

        if deps.generator_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OPENROUTER_API_KEY not configured — cannot generate report",
            )

        result = run_research_flow(
            block_inputs,
            params,
            req.recipe,
            generator_client=deps.generator_client,
            judge_client=deps.judge_client,
            generator_params=GeneratorParams(model=deps.settings.generator_model),
            disclaimer=deps.disclaimer,
            runs_dir=deps.runs_dir,
        )
        return ResearchResponse(
            run_id=result.run_id,
            resolved_brief=resolved_brief,
            report=result.report.model_dump(mode="json"),
            validation=result.validation.model_dump(mode="json"),
            stage_summary=[StageOutcome(**s.model_dump()) for s in result.stage_summary],
            run_dir=result.run_dir,
        )

    @router.post("/v1/topics/resolve", response_model=ResolveResponse)
    def resolve(req: ResolveRequest, request: Request, _=Depends(auth_dep)):
        deps = request.app.state.deps
        result = deps.topic_resolver.resolve(req.topic)
        return ResolveResponse(
            brief=result.brief,
            confidence=result.confidence,
            candidates=result.candidates,
            source=result.source,
        )

    @router.get("/v1/recipes", response_model=RecipesResponse)
    def recipes(_=Depends(auth_dep)):
        from importlib import resources

        packaged = [
            r.name.removesuffix(".yaml")
            for r in resources.files("researchflow.context.recipes").iterdir()
            if r.name.endswith(".yaml")
        ]
        return RecipesResponse(recipes=sorted(packaged))

    @router.get("/v1/research/runs/{run_id}")
    def get_run(run_id: str, request: Request, _=Depends(auth_dep)):
        deps = request.app.state.deps
        summary = read_flow_summary(deps.runs_dir, run_id)
        if summary is None:
            raise HTTPException(status_code=404, detail=f"run {run_id} not found")
        return summary

    @router.get("/v1/research/runs/{run_id}/{stage}/{artifact}")
    def get_run_artifact(
        run_id: str,
        stage: str,
        artifact: str,
        request: Request,
        _=Depends(auth_dep),
    ):
        deps = request.app.state.deps
        content = read_artifact(deps.runs_dir, run_id, stage, artifact)
        if content is None:
            raise HTTPException(status_code=404, detail="artifact not found")
        media = "application/json" if artifact.endswith(".json") else (
            "application/xml" if artifact.endswith(".xml") else "text/markdown"
        )
        return Response(content=content, media_type=media)

    @router.get("/v1/health", response_model=HealthResponse)
    def health(request: Request):
        deps = request.app.state.deps
        return HealthResponse(
            status="ok",
            dependencies={
                "openrouter": deps.generator_client is not None,
                "macro_data": deps.data_client is not None,
                "rag": deps.rag_client is not None,
                "topic_registry": deps.topic_resolver is not None,
                "house_view": deps.house_view_loader.load() is not None,
            },
        )

    return router


def _resolve_and_fetch(req: ResearchRequest, deps) -> tuple[BlockInputs, Brief]:
    if req.inputs_override is not None:
        block_inputs = _block_inputs_from_dict(req.inputs_override)
        return block_inputs, block_inputs.brief

    result = deps.topic_resolver.resolve(req.topic)
    if result.brief is None:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "topic not recognised",
                "candidates": result.candidates,
                "source": result.source,
            },
        )
    brief = result.brief

    data_pack = _fetch_data(deps.data_client, brief)
    material_pack = _fetch_material(deps.rag_client, brief)
    house_view = deps.house_view_loader.load() if deps.house_view_loader else None

    extras: dict[str, Any] = {
        "framework": load_framework(brief.report_type, deps.settings.framework_dir),
        "exemplar_pool": load_exemplars(brief.report_type, deps.settings.exemplar_dir),
    }
    block_inputs = BlockInputs(
        brief=brief,
        data_pack=data_pack,
        material_pack=material_pack,
        house_view=house_view,
        extras=extras,
    )
    return block_inputs, brief


def _fetch_data(client: HttpMacroDataClient | None, brief: Brief) -> DataPack | None:
    if client is None:
        return None
    return client.fetch_data_pack(brief)


def _fetch_material(client: HttpRagClient | None, brief: Brief) -> MaterialPack | None:
    if client is None:
        return None
    return client.fetch_material_pack(brief)


def _block_inputs_from_dict(raw: dict[str, Any]) -> BlockInputs:
    brief = Brief(**raw["brief"])
    data_pack = None
    if raw.get("data_pack"):
        dp = raw["data_pack"]
        if "payload" in dp:
            data_pack = DataPack(event_id=dp.get("event_id", brief.event_id), payload=dp["payload"])
        else:
            data_pack = DataPack(event_id=brief.event_id, payload=dp)
    material_pack = None
    if raw.get("material_pack"):
        mp = raw["material_pack"]
        material_pack = MaterialPack(event_id=mp.get("event_id", brief.event_id), payload=mp.get("payload", {}))
    house_view = None
    if raw.get("house_view"):
        house_view = HouseView(**raw["house_view"])
    return BlockInputs(
        brief=brief,
        data_pack=data_pack,
        material_pack=material_pack,
        house_view=house_view,
        extras=raw.get("extras", {}),
    )
