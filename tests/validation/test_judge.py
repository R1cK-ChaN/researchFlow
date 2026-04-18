from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from researchflow.validation.judge import PARSE_ERROR_SENTINEL, run_judge


def _fake_response(text: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_parses_valid_violations():
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        '{"violations": [{"quote": "yields rise", "explanation": "wrong sign"}]}'
    )
    result = run_judge(client, model="m", system_prompt="s", user_content="u")
    assert len(result) == 1
    assert result[0]["quote"] == "yields rise"


def test_empty_violations():
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response('{"violations": []}')
    assert run_judge(client, model="m", system_prompt="s", user_content="u") == []


def test_malformed_json_returns_parse_error_sentinel():
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("not json at all")
    result = run_judge(client, model="m", system_prompt="s", user_content="u")
    assert len(result) == 1 and result[0][PARSE_ERROR_SENTINEL] is True


def test_code_fenced_json_is_parsed():
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        '```json\n{"violations": [{"quote": "q"}]}\n```'
    )
    result = run_judge(client, model="m", system_prompt="s", user_content="u")
    assert result[0]["quote"] == "q"


def test_non_dict_items_filtered():
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(
        '{"violations": [{"ok": 1}, "garbage", null]}'
    )
    result = run_judge(client, model="m", system_prompt="s", user_content="u")
    assert result == [{"ok": 1}]


def test_passes_model_and_prompts_to_client():
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response('{"violations": []}')
    run_judge(
        client,
        model="test-model",
        system_prompt="SYS",
        user_content="USR",
        temperature=0.2,
        max_tokens=1500,
    )
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USR"},
    ]
    assert kwargs["temperature"] == 0.2
    assert kwargs["max_tokens"] == 1500
