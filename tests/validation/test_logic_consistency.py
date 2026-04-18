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
from researchflow.validation.validators.logic_consistency import (
    SYSTEM_PROMPT,
    LogicConsistencyValidator,
)


def _fake_response(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


@pytest.fixture
def context_with_signmap():
    brief = Brief(
        event_id="e1",
        event_name="e1",
        release_time=datetime(2026, 4, 10, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    data_pack = DataPack(
        event_id=brief.event_id,
        payload={
            "facts": [
                {
                    "id": "F-CPI-HEAD-YOY",
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
        version="v",
        as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
        content={"base_case": "Cuts", "tone_lean": "dovish"},
    )
    framework = {
        "sign_map": [
            {
                "when": "headline_surprise_bp < -15",
                "expect": [
                    {"asset": "ust_2y", "sign": "-"},
                    {"asset": "equities", "sign": "+"},
                ],
            }
        ]
    }
    return build(
        "brief_comment",
        ContextParams(language="en"),
        BlockInputs(
            brief=brief,
            data_pack=data_pack,
            house_view=house_view,
            extras={"framework": framework, "exemplar_pool": []},
        ),
    )


def test_returns_empty_without_client(context_with_signmap, make_report):
    v = LogicConsistencyValidator()
    assert v.validate(make_report("text"), context_with_signmap, {}) == []


def test_skips_when_sign_map_empty(make_report):
    brief = Brief(
        event_id="e1",
        event_name="e1",
        release_time=datetime(2026, 4, 10, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    ctx = build(
        "brief_comment",
        ContextParams(),
        BlockInputs(
            brief=brief,
            data_pack=DataPack(event_id="e1", payload={"facts": []}),
            house_view=HouseView(
                version="v",
                as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
                content={},
            ),
            extras={"framework": {}, "exemplar_pool": []},
        ),
    )
    client = MagicMock()
    result = LogicConsistencyValidator().validate(
        make_report("text"), ctx, {}, judge_client=client
    )
    assert result == []
    client.chat.completions.create.assert_not_called()


def test_flags_violations(context_with_signmap, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        '{"violations": [{"quote": "yields should rise despite the miss",'
        ' "violates": "rule headline_surprise<-15bp",'
        ' "expected_direction": "ust_2y -",'
        ' "claimed_direction": "ust_2y +",'
        ' "explanation": "contradicts sign_map"}]}'
    )
    issues = LogicConsistencyValidator().validate(
        make_report("yields should rise despite the miss [F-CPI-HEAD-YOY]"),
        context_with_signmap,
        {},
        judge_client=client,
    )
    assert len(issues) == 1
    assert issues[0].code == "sign_map_violation"
    assert issues[0].severity.value == "warning"
    assert issues[0].context["claimed_direction"] == "ust_2y +"


def test_malformed_output_becomes_info(context_with_signmap, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("not json")
    issues = LogicConsistencyValidator().validate(
        make_report("text"), context_with_signmap, {}, judge_client=client
    )
    assert len(issues) == 1
    assert issues[0].code == "judge_output_malformed"
    assert issues[0].severity.value == "info"


def test_prompt_shape(context_with_signmap, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response('{"violations": []}')
    LogicConsistencyValidator().validate(
        make_report("sample body"),
        context_with_signmap,
        {"model": "test/m", "temperature": 0.1, "max_tokens": 500},
        judge_client=client,
    )
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test/m"
    assert kwargs["temperature"] == 0.1
    assert kwargs["max_tokens"] == 500
    assert kwargs["messages"][0]["content"] == SYSTEM_PROMPT
    user = kwargs["messages"][1]["content"]
    assert "<report>" in user and "sample body" in user
    assert "<sign_map>" in user and "ust_2y" in user
    assert "<derived_metrics>" in user
