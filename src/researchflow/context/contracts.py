"""Typed contracts for the context builder."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Language = Literal["en", "zh_cn", "zh_hk"]
ReaderTier = Literal["trading_desk", "pm", "broad_client"]


class ContextParams(BaseModel):
    """Runtime knobs for context assembly. Do not define structure."""

    language: Language = "en"
    reader_tier: ReaderTier = "pm"
    extras: dict[str, Any] = Field(default_factory=dict)


class Brief(BaseModel):
    """The trigger and framing for a report."""

    event_id: str
    event_name: str
    release_time: datetime
    report_type: str


class DataPack(BaseModel):
    """Opaque payload from the external data service (e.g. macro-data-service).

    The shape is intentionally loose at this layer; individual blocks own
    the interpretation of `payload`.
    """

    event_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MaterialPack(BaseModel):
    """Opaque payload from the external materials service (e.g. rag-service)."""

    event_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class HouseView(BaseModel):
    version: str
    as_of: datetime
    content: dict[str, Any] = Field(default_factory=dict)


class BlockInputs(BaseModel):
    """The bag of inputs passed to every block's render(). Blocks pull
    only what they need, declared via `required_inputs`."""

    brief: Brief
    data_pack: DataPack | None = None
    material_pack: MaterialPack | None = None
    house_view: HouseView | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class RenderedBlock(BaseModel):
    """Output of a block's render(). Renderer-agnostic structured content."""

    name: str
    content: dict[str, Any]
    token_estimate: int = 0
    trace: dict[str, Any] = Field(default_factory=dict)


class ContextTrace(BaseModel):
    recipe_name: str
    params: ContextParams
    blocks_rendered: list[str]
    blocks_skipped: list[str] = Field(default_factory=list)
    total_token_estimate: int = 0
    notes: list[str] = Field(default_factory=list)


class Context(BaseModel):
    """Final assembled context, ready for the generator."""

    recipe_name: str
    params: ContextParams
    rendered_text: str
    blocks: list[RenderedBlock]
    trace: ContextTrace
