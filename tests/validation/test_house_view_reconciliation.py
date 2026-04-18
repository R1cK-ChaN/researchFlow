from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from researchflow.validation.validators.house_view_reconciliation import (
    SYSTEM_PROMPT,
    HouseViewReconciliationValidator,
)


def _fake_response(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_returns_empty_without_client(context, make_report):
    assert HouseViewReconciliationValidator().validate(make_report("x"), context, {}) == []


def test_unflagged_contradiction_is_warning(context, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        '{"violations": [{"quote": "Fed to hold through 2026",'
        ' "contradicts": "base_case: Fed cuts 75bp",'
        ' "flagged": false,'
        ' "explanation": "directly contradicts base case"}]}'
    )
    issues = HouseViewReconciliationValidator().validate(
        make_report("Fed to hold through 2026."),
        context,
        {},
        judge_client=client,
    )
    assert len(issues) == 1
    assert issues[0].severity.value == "warning"
    assert issues[0].code == "house_view_contradiction"
    assert issues[0].context["flagged"] is False


def test_flagged_divergence_is_info(context, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        '{"violations": [{"quote": "vs our prior base case, we now see no cuts",'
        ' "contradicts": "base_case",'
        ' "flagged": true,'
        ' "explanation": "divergence is explicitly flagged"}]}'
    )
    issues = HouseViewReconciliationValidator().validate(
        make_report("text"), context, {}, judge_client=client
    )
    assert len(issues) == 1
    assert issues[0].severity.value == "info"
    assert issues[0].code == "house_view_divergence_flagged"


def test_prompt_shape(context, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response('{"violations": []}')
    HouseViewReconciliationValidator().validate(
        make_report("body"), context, {}, judge_client=client
    )
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["messages"][0]["content"] == SYSTEM_PROMPT
    user = kwargs["messages"][1]["content"]
    assert "<report>" in user and "body" in user
    assert "<house_view>" in user and "Fed cuts 75bp" in user
