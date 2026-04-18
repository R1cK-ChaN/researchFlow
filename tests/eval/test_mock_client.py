from __future__ import annotations

import pytest

from researchflow.eval.mock_client import QueueClient


def test_returns_responses_in_order():
    c = QueueClient(["first", "second"])
    r1 = c.chat.completions.create(model="m", messages=[])
    r2 = c.chat.completions.create(model="m", messages=[])
    assert r1.choices[0].message.content == "first"
    assert r2.choices[0].message.content == "second"
    assert c.remaining() == 0


def test_exhausted_queue_raises():
    c = QueueClient(["only"])
    c.chat.completions.create(model="m", messages=[])
    with pytest.raises(RuntimeError):
        c.chat.completions.create(model="m", messages=[])


def test_records_calls():
    c = QueueClient(["x"])
    c.chat.completions.create(model="m", messages=[{"role": "user", "content": "hi"}])
    assert len(c.calls) == 1
    assert c.calls[0]["model"] == "m"
