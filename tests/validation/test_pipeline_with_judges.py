from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from researchflow.validation import post_process, validate


def _fake_response(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_llm_validators_skipped_without_client(context, make_report):
    body = "word " * 60
    report = post_process(
        make_report(
            "## Bottom line\n3.1% [F-CPI-HEAD-YOY]. " + body + "\n\n"
            "## What happened\n" + body + "\n\n"
            "## What it means\n" + body + "\n\n{{DISCLAIMER}}"
        )
    )
    vr = validate(report, context)
    assert any("logic_consistency" in s for s in vr.validators_skipped)
    assert any("house_view_reconciliation" in s for s in vr.validators_skipped)


def test_llm_validators_run_when_client_passed(context, make_report):
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response('{"violations": []}')

    body = "word " * 60
    report = post_process(
        make_report(
            "## Bottom line\n3.1% [F-CPI-HEAD-YOY]. " + body + "\n\n"
            "## What happened\n" + body + "\n\n"
            "## What it means\n" + body + "\n\n{{DISCLAIMER}}"
        )
    )
    vr = validate(report, context, judge_client=client)
    assert "logic_consistency" in vr.validators_run
    assert "house_view_reconciliation" in vr.validators_run
    assert vr.passed
    # No sign_map in this fixture's context, so logic_consistency should short-circuit
    # without hitting the client; house_view has content so it will be called once.
    assert client.chat.completions.create.call_count == 1
