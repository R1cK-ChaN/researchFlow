"""Lightweight loaders for framework + exemplar resources from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_framework(report_type: str, framework_dir: Path | str) -> dict[str, Any]:
    """Load `<framework_dir>/<report_type>.yaml` — sign_map / transmission / glossary.

    Returns an empty dict when the file is missing; the FrameworkBlock
    renders cleanly on empty input.
    """
    p = Path(framework_dir) / f"{report_type}.yaml"
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def load_exemplars(report_type: str, exemplar_dir: Path | str) -> list[dict[str, Any]]:
    """Load every `*.json` under `<exemplar_dir>/<report_type>/` as an exemplar.

    Each file should be a JSON object with at least `language` and
    `report_text`. Returns an empty list if the directory is missing.
    """
    p = Path(exemplar_dir) / report_type
    if not p.is_dir():
        return []
    pool: list[dict[str, Any]] = []
    for f in sorted(p.glob("*.json")):
        try:
            entry = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            pool.append(entry)
    return pool


def load_disclaimer(path: Path | str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    return p.read_text().strip()
