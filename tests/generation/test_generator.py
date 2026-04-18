from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from researchflow.context import (
    BlockInputs,
    Brief,
    ContextParams,
    DataPack,
    HouseView,
    build,
)
from researchflow.generation import GeneratorParams, generate
from researchflow.generation.generator import _extract_citations


@pytest.fixture
def context():
    brief = Brief(
        event_id="us_cpi_2026_03",
        event_name="US CPI — March 2026",
        release_time=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    data_pack = DataPack(
        event_id=brief.event_id,
        payload={
            "facts": [
                {
                    "id": "F-CPI-HEAD-YOY",
                    "label": "Headline CPI YoY",
                    "unit": "%",
                    "actual": 3.1,
                    "consensus": 3.2,
                    "prior": 3.0,
                    "tier": 1,
                }
            ]
        },
    )
    house_view = HouseView(
        version="2026-04-15",
        as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
        content={"base_case": "Fed cuts 75bp in 2026.", "tone_lean": "modestly_dovish"},
    )
    return build(
        "brief_comment",
        ContextParams(language="en"),
        BlockInputs(
            brief=brief,
            data_pack=data_pack,
            house_view=house_view,
            extras={"framework": {}, "exemplar_pool": []},
        ),
    )


def _fake_response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=80, total_tokens=180),
        id="req_test_123",
    )


def test_generate_passes_context_to_client(context):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        "## Bottom line\nHeadline CPI slipped to 3.1% [F-CPI-HEAD-YOY].\n\n{{DISCLAIMER}}"
    )

    report = generate(context, GeneratorParams(model="test/model"), client=client)

    call_kwargs = client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "test/model"
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "sell-side research analyst" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "F-CPI-HEAD-YOY" in messages[1]["content"]


def test_generate_parses_response_and_citations(context):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        "Headline 3.1% [F-CPI-HEAD-YOY] and core [F-CPI-CORE-YOY] were in focus.\n{{DISCLAIMER}}"
    )

    report = generate(context, GeneratorParams(model="test/model"), client=client)

    assert report.recipe_name == context.recipe_name
    assert "{{DISCLAIMER}}" in report.raw_text
    assert report.fact_citations == ["F-CPI-HEAD-YOY", "F-CPI-CORE-YOY"]
    assert report.trace.usage["total_tokens"] == 180
    assert report.trace.request_id == "req_test_123"


def test_citation_extractor_dedupes_and_preserves_order():
    text = "a [F-A] then [F-B] and [F-A] again, plus [F-C-1]."
    assert _extract_citations(text) == ["F-A", "F-B", "F-C-1"]


def test_citation_extractor_rejects_non_fact_brackets():
    text = "No [note] or [123] or [f-lower], only [F-OK]."
    assert _extract_citations(text) == ["F-OK"]
