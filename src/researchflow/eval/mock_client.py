"""Deterministic mock LLM client for replay-mode eval."""

from __future__ import annotations

from types import SimpleNamespace


class QueueClient:
    """Returns canned responses from a FIFO queue.

    Matches the shape `client.chat.completions.create(...)` expected by
    both the generator and the judge helper. Raises if the queue is empty,
    so harness tests fail loudly when fewer responses than stages were
    recorded.
    """

    def __init__(self, responses: list[str]):
        self._queue = list(responses)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._queue:
            raise RuntimeError(
                "QueueClient exhausted — recorded fewer mock responses than "
                "the pipeline consumed. Calls so far: "
                + str(len(self.calls))
            )
        content = self._queue.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            id=f"replay_{len(self.calls)}",
        )

    def remaining(self) -> int:
        return len(self._queue)
