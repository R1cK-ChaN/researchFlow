"""Versioned house-view loader (YAML file on disk)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from researchflow.context.contracts import HouseView


class HouseViewLoader:
    """Reads the current house view from a YAML file.

    Expected shape::

        version: "2026-04-15"
        as_of: "2026-04-15T00:00:00+00:00"
        content:
          base_case: "..."
          tone_lean: modestly_dovish
          ...
    """

    def __init__(self, path: Path | str):
        self._path = Path(path)

    def load(self) -> HouseView | None:
        if not self._path.is_file():
            return None
        raw = yaml.safe_load(self._path.read_text()) or {}
        if not raw:
            return None
        as_of = raw.get("as_of")
        if isinstance(as_of, str):
            as_of_dt = datetime.fromisoformat(as_of)
        elif isinstance(as_of, datetime):
            as_of_dt = as_of
        else:
            as_of_dt = datetime.now(timezone.utc)
        return HouseView(
            version=str(raw.get("version", "unversioned")),
            as_of=as_of_dt,
            content=raw.get("content", {}),
        )
