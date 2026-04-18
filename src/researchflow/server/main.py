"""FastAPI app + dependency wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from researchflow.clients import (
    HouseViewLoader,
    HttpMacroDataClient,
    HttpRagClient,
    MacroDataConfig,
    RagConfig,
)
from researchflow.generation.provider import OPENROUTER_BASE_URL
from researchflow.resolve import LocalRegistry, TopicResolver
from researchflow.server.auth import make_auth_dependency
from researchflow.server.config import Settings
from researchflow.server.resources import load_disclaimer
from researchflow.server.routes import build_router


@dataclass
class Dependencies:
    settings: Settings
    topic_resolver: TopicResolver
    data_client: HttpMacroDataClient | None
    rag_client: HttpRagClient | None
    house_view_loader: HouseViewLoader
    generator_client: Any | None
    judge_client: Any | None
    runs_dir: Path
    disclaimer: str | None


def _build_generator_client(settings: Settings):
    if not settings.openrouter_api_key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=settings.openrouter_api_key, base_url=OPENROUTER_BASE_URL)


def build_dependencies(settings: Settings) -> Dependencies:
    topic_resolver = TopicResolver(LocalRegistry.from_yaml(settings.topic_registry_path))
    house_view_loader = HouseViewLoader(settings.house_view_path)
    runs_dir = Path(settings.runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    data_client: HttpMacroDataClient | None = None
    if settings.macro_data_base_url:
        data_client = HttpMacroDataClient(
            MacroDataConfig(
                base_url=settings.macro_data_base_url,
                api_token=settings.macro_data_api_token,
                timeout=settings.macro_data_timeout,
            )
        )

    rag_client: HttpRagClient | None = None
    if settings.rag_base_url:
        rag_client = HttpRagClient(
            RagConfig(
                base_url=settings.rag_base_url,
                api_token=settings.rag_api_token,
                timeout=settings.rag_timeout,
            )
        )

    generator_client = _build_generator_client(settings)

    return Dependencies(
        settings=settings,
        topic_resolver=topic_resolver,
        data_client=data_client,
        rag_client=rag_client,
        house_view_loader=house_view_loader,
        generator_client=generator_client,
        judge_client=generator_client,  # OpenRouter client doubles as judge client
        runs_dir=runs_dir,
        disclaimer=load_disclaimer(settings.disclaimer_path),
    )


def create_app(
    settings: Settings | None = None,
    *,
    deps: Dependencies | None = None,
) -> FastAPI:
    settings = settings or Settings()
    deps = deps or build_dependencies(settings)

    app = FastAPI(title="researchFlow", version="0.0.1")
    app.state.deps = deps

    auth_dep = make_auth_dependency(settings)
    app.include_router(build_router(auth_dep))
    return app


app = create_app()
