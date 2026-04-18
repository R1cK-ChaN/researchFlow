"""HTTP client for rag-service. Mirrors its `/v1/retrieve` shape."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel

from researchflow.context.contracts import Brief, MaterialPack


class RagConfig(BaseModel):
    base_url: str
    api_token: str | None = None
    timeout: float = 30.0
    default_top_k: int = 5

    @classmethod
    def from_env(cls) -> "RagConfig":
        base = os.environ.get("ANALYST_RAG_BASE_URL")
        if not base:
            raise RuntimeError("ANALYST_RAG_BASE_URL is not set")
        return cls(
            base_url=base,
            api_token=os.environ.get("ANALYST_RAG_API_TOKEN"),
            timeout=float(os.environ.get("ANALYST_RAG_TIMEOUT", "30")),
            default_top_k=int(os.environ.get("ANALYST_RAG_TOP_K", "5")),
        )


class HttpRagClient:
    def __init__(
        self,
        config: RagConfig,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers: dict[str, str] = {}
        if config.api_token:
            headers["Authorization"] = f"Bearer {config.api_token}"
        self._client = httpx.Client(
            base_url=config.base_url,
            headers=headers,
            timeout=config.timeout,
            transport=transport,
        )
        self._top_k = config.default_top_k

    def fetch_material_pack(self, brief: Brief, *, top_k: int | None = None) -> MaterialPack:
        resp = self._client.post(
            "/v1/retrieve",
            json={
                "query": brief.event_name,
                "event_id": brief.event_id,
                "report_type": brief.report_type,
                "top_k": top_k or self._top_k,
            },
        )
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        return MaterialPack(event_id=brief.event_id, payload=payload)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpRagClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
