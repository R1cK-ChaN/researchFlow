from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from researchflow.clients import HttpRagClient, RagConfig
from researchflow.context.contracts import Brief


def _brief() -> Brief:
    return Brief(
        event_id="us_cpi_2026_03",
        event_name="US CPI — March 2026",
        release_time=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
        report_type="us_cpi",
    )


def test_fetch_material_pack_shape():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"evidence": [{"doc_id": "d1"}]})

    client = HttpRagClient(
        RagConfig(base_url="http://rag.local", api_token="tok", default_top_k=3),
        transport=httpx.MockTransport(handler),
    )
    pack = client.fetch_material_pack(_brief())

    assert captured["url"].endswith("/v1/retrieve")
    assert captured["body"]["event_id"] == "us_cpi_2026_03"
    assert captured["body"]["top_k"] == 3
    assert pack.payload["evidence"][0]["doc_id"] == "d1"


def test_top_k_override_wins_over_default():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={})

    client = HttpRagClient(
        RagConfig(base_url="http://rag.local", default_top_k=3),
        transport=httpx.MockTransport(handler),
    )
    client.fetch_material_pack(_brief(), top_k=10)
    assert captured["body"]["top_k"] == 10
