"""Block protocol + registry."""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@runtime_checkable
class ContextBlock(Protocol):
    name: ClassVar[str]
    required_inputs: ClassVar[set[str]]

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock: ...


_REGISTRY: dict[str, type] = {}


def register_block(cls: type) -> type:
    """Class decorator: register a block under its `name` attribute."""
    name = getattr(cls, "name", None)
    if not name:
        raise ValueError(f"{cls.__name__} missing `name` classvar")
    if name in _REGISTRY:
        raise ValueError(f"Block name collision: {name}")
    _REGISTRY[name] = cls
    return cls


def get_block(name: str) -> ContextBlock:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown block '{name}'. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()


def all_blocks() -> list[str]:
    return sorted(_REGISTRY)


def rough_tokens(content: Any) -> int:
    """MVP token estimate: ~4 chars per token. Replace with tiktoken later."""
    return max(1, len(str(content)) // 4)


def filter_facts_by_depth(facts: list[dict], depth: str) -> list[dict]:
    """Shared tier filter so fact_table and derived_metrics stay consistent.

    `minimal` keeps tier-1 only; `full` keeps everything.
    """
    if depth == "full":
        return list(facts)
    return [f for f in facts if f.get("tier", 1) == 1]
