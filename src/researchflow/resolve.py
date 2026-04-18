"""Topic → Brief resolution.

MVP: lookup a small local registry keyed on normalised topic strings.
Swap the registry for a macro-data-service calendar query when that
contract is available — the `CalendarSource` protocol is the extension
point.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

import yaml
from pydantic import BaseModel, Field

from researchflow.context.contracts import Brief


class ResolveResult(BaseModel):
    brief: Brief | None = None
    confidence: float = 0.0
    candidates: list[str] = Field(default_factory=list)
    source: str = "unknown"


class CalendarSource(Protocol):
    def lookup(self, normalised_topic: str) -> Brief | None: ...
    def candidates(self) -> list[str]: ...


class LocalRegistry:
    """Keyword-keyed topic → Brief mapping loaded from a YAML file.

    File shape::

        - topic: "us cpi march 2026"
          brief:
            event_id: us_cpi_2026_03
            event_name: "US CPI — March 2026"
            release_time: "2026-04-10T08:30:00+00:00"
            report_type: us_cpi
    """

    def __init__(self, entries: list[dict]):
        self._entries: dict[str, Brief] = {}
        for entry in entries:
            topic = str(entry["topic"]).strip().lower()
            brief_raw = dict(entry["brief"])
            if isinstance(brief_raw.get("release_time"), str):
                brief_raw["release_time"] = datetime.fromisoformat(brief_raw["release_time"])
            self._entries[topic] = Brief(**brief_raw)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "LocalRegistry":
        p = Path(path)
        if not p.is_file():
            return cls([])
        data = yaml.safe_load(p.read_text()) or []
        return cls(data)

    def lookup(self, normalised_topic: str) -> Brief | None:
        return self._entries.get(normalised_topic)

    def candidates(self) -> list[str]:
        return sorted(self._entries)


class TopicResolver:
    def __init__(self, calendar: CalendarSource):
        self._calendar = calendar

    @staticmethod
    def _normalise(topic: str) -> str:
        return " ".join(topic.strip().lower().split())

    def resolve(self, topic: str) -> ResolveResult:
        normalised = self._normalise(topic)
        if not normalised:
            return ResolveResult(candidates=self._calendar.candidates(), source="local_registry")
        brief = self._calendar.lookup(normalised)
        if brief is not None:
            return ResolveResult(brief=brief, confidence=1.0, source="local_registry")
        return ResolveResult(
            candidates=self._nearest(normalised),
            source="local_registry",
        )

    def _nearest(self, normalised: str) -> list[str]:
        tokens = set(normalised.split())
        scored: list[tuple[int, str]] = []
        for candidate in self._calendar.candidates():
            overlap = len(tokens & set(candidate.split()))
            if overlap:
                scored.append((overlap, candidate))
        scored.sort(reverse=True)
        return [c for _, c in scored[:5]]
