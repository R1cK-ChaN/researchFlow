from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import (
    filter_facts_by_depth,
    register_block,
    rough_tokens,
)
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class FactTableBlock:
    """Normalizes DataPack.payload['facts'] into a stable-ID fact table.

    Each inbound fact is expected to carry at least an `id`. Everything
    else is passed through so downstream (generator / validator) can rely
    on well-known fields (`actual`, `consensus`, `prior`, `unit`, `period`,
    `source`, `label`, `tier`) without this layer gatekeeping.
    """

    name: ClassVar[str] = "fact_table"
    required_inputs: ClassVar[set[str]] = {"data_pack"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        assert inputs.data_pack is not None
        raw = inputs.data_pack.payload.get("facts", [])
        depth = config.get("include_components", "minimal")
        facts = filter_facts_by_depth(raw, depth)
        content = {"facts": facts}
        return RenderedBlock(
            name=self.name,
            content=content,
            token_estimate=rough_tokens(content),
            trace={"depth": depth, "kept": len(facts), "dropped": len(raw) - len(facts)},
        )
