from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

from researchflow.clients import HttpMacroDataClient, MacroDataConfig
from researchflow.context.contracts import Brief


def _brief() -> Brief:
    return Brief(
        event_id="us_cpi_2026_03",
        event_name="US CPI — March 2026",
        release_time=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
        report_type="us_cpi",
    )


def test_fetch_data_pack_shape():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"facts": [{"id": "F-X", "actual": 1.0, "consensus": 1.0}]},
        )

    client = HttpMacroDataClient(
        MacroDataConfig(base_url="http://macro.local", api_token="tok"),
        transport=httpx.MockTransport(handler),
    )
    pack = client.fetch_data_pack(_brief())

    assert captured["url"].endswith("/v1/ops/fetch_event_data")
    assert captured["body"] == {"event_id": "us_cpi_2026_03", "report_type": "us_cpi"}
    assert captured["headers"]["authorization"] == "Bearer tok"
    assert pack.event_id == "us_cpi_2026_03"
    assert pack.payload["facts"][0]["id"] == "F-X"


def test_from_env_requires_base_url(monkeypatch):
    monkeypatch.delenv("ANALYST_MACRO_DATA_BASE_URL", raising=False)
    try:
        MacroDataConfig.from_env()
    except RuntimeError as e:
        assert "ANALYST_MACRO_DATA_BASE_URL" in str(e)
    else:  # pragma: no cover
        raise AssertionError("expected RuntimeError")


def test_no_token_omits_authorization():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"facts": []})

    client = HttpMacroDataClient(
        MacroDataConfig(base_url="http://macro.local"),
        transport=httpx.MockTransport(handler),
    )
    client.fetch_data_pack(_brief())
    assert "authorization" not in captured["headers"]
