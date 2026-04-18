"""Reads artifact trees produced by the flow; whitelist-guards traversal."""

from __future__ import annotations

import json
from pathlib import Path

# Only artifacts within these stage directories are retrievable via API.
_ALLOWED_STAGES = {"01_context", "02_generation", "03_postprocess", "04_validation"}
_ALLOWED_EXTS = {".md", ".xml", ".json"}


def read_flow_summary(runs_dir: Path, run_id: str) -> dict | None:
    p = runs_dir / run_id / "flow_summary.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def read_artifact(runs_dir: Path, run_id: str, stage: str, artifact: str) -> str | None:
    if stage not in _ALLOWED_STAGES:
        return None
    if "/" in artifact or ".." in artifact:
        return None
    if not any(artifact.endswith(ext) for ext in _ALLOWED_EXTS):
        return None
    p = runs_dir / run_id / stage / artifact
    # Resolve and ensure still inside runs_dir/run_id to block traversal.
    try:
        full = p.resolve()
        anchor = (runs_dir / run_id).resolve()
    except OSError:
        return None
    if not str(full).startswith(str(anchor)):
        return None
    if not full.is_file():
        return None
    return full.read_text()
