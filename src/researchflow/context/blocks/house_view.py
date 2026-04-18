from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import register_block, rough_tokens
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class HouseViewBlock:
    name: ClassVar[str] = "house_view"
    required_inputs: ClassVar[set[str]] = {"house_view"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        assert inputs.house_view is not None
        hv = inputs.house_view
        depth = config.get("depth", "summary")

        if depth == "summary":
            content = {
                "version": hv.version,
                "as_of": hv.as_of.isoformat(),
                "base_case": hv.content.get("base_case"),
                "tone_lean": hv.content.get("tone_lean"),
            }
        else:
            content = {"version": hv.version, "as_of": hv.as_of.isoformat(), **hv.content}

        return RenderedBlock(name=self.name, content=content, token_estimate=rough_tokens(content))
