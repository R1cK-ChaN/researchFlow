"""Recipe YAML loader.

A recipe is a declarative spec of which blocks go into a given report type.
Block entries may be bare strings (`- brief`) or single-key dicts carrying
per-block config (`- fact_table: { include_components: full }`).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class BlockSpec(BaseModel):
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class Recipe(BaseModel):
    name: str
    description: str = ""
    token_budget: int = 8000
    renderer: str = "xml"
    blocks: list[BlockSpec]


def _normalize_block_entries(raw: list[Any]) -> list[BlockSpec]:
    out: list[BlockSpec] = []
    for entry in raw:
        if isinstance(entry, str):
            out.append(BlockSpec(name=entry))
        elif isinstance(entry, dict):
            if len(entry) != 1:
                raise ValueError(f"Block entry must have exactly one key, got: {entry}")
            ((name, cfg),) = entry.items()
            out.append(BlockSpec(name=name, config=cfg or {}))
        else:
            raise TypeError(f"Unsupported block entry type: {type(entry)}")
    return out


def load_recipe(name_or_path: str, search_dir: Path | None = None) -> Recipe:
    """Load a recipe by name (searches packaged `recipes/`) or by path."""
    path = Path(name_or_path)
    if path.is_file():
        text = path.read_text()
    elif search_dir and (search_dir / f"{name_or_path}.yaml").is_file():
        text = (search_dir / f"{name_or_path}.yaml").read_text()
    else:
        text = resources.files("researchflow.context.recipes").joinpath(f"{name_or_path}.yaml").read_text()
    raw = yaml.safe_load(text)
    raw["blocks"] = _normalize_block_entries(raw.get("blocks", []))
    return Recipe(**raw)
