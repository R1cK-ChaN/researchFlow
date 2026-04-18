"""Validator protocol + registry."""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import ValidationIssue


@runtime_checkable
class Validator(Protocol):
    name: ClassVar[str]
    requires_llm: ClassVar[bool]

    def validate(
        self,
        report: Report,
        context: Context,
        config: dict[str, Any],
        *,
        judge_client: Any = None,
    ) -> list[ValidationIssue]: ...


_REGISTRY: dict[str, type] = {}


def register_validator(cls: type) -> type:
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"{cls.__name__} missing `name` classvar")
    if name in _REGISTRY:
        raise ValueError(f"Validator name collision: {name}")
    _REGISTRY[name] = cls
    return cls


def get_validator(name: str) -> Validator:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown validator '{name}'. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def all_validators() -> list[str]:
    return sorted(_REGISTRY)


def get_fact_map(context: Context) -> dict[str, dict]:
    """Shared helper: pull fact_id → fact dict out of the context's fact_table block."""
    for block in context.blocks:
        if block.name == "fact_table":
            return {f["id"]: f for f in block.content.get("facts", []) if f.get("id")}
    return {}


def get_style_guide(context: Context) -> dict:
    for block in context.blocks:
        if block.name == "style_guide":
            return block.content
    return {}
