"""HTTP client for macro-data-service.

Follows the sibling-service `HttpXxxClient` + `XxxConfig.from_env()` pattern.
Endpoint contracts here are placeholders matching the `POST /v1/ops/{operation}`
dispatch shape; update them when the real service contract is finalised.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel

from researchflow.context.contracts import Brief, DataPack


class MacroDataConfig(BaseModel):
    base_url: str
    api_token: str | None = None
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "MacroDataConfig":
        base = os.environ.get("ANALYST_MACRO_DATA_BASE_URL")
        if not base:
            raise RuntimeError("ANALYST_MACRO_DATA_BASE_URL is not set")
        return cls(
            base_url=base,
            api_token=os.environ.get("ANALYST_MACRO_DATA_API_TOKEN"),
            timeout=float(os.environ.get("ANALYST_MACRO_DATA_TIMEOUT", "30")),
        )


class HttpMacroDataClient:
    def __init__(
        self,
        config: MacroDataConfig,
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

    def fetch_data_pack(self, brief: Brief) -> DataPack:
        resp = self._client.post(
            "/v1/ops/fetch_event_data",
            json={"event_id": brief.event_id, "report_type": brief.report_type},
        )
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        return DataPack(event_id=brief.event_id, payload=payload)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpMacroDataClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
