from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import register_block, rough_tokens
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class FrameworkBlock:
    """Renders the economic-logic backbone: sign-map, transmission graph, glossary.

    MVP reads the framework from `inputs.extras['framework']` (a dict that the
    caller assembles, typically from a versioned YAML). The block only filters
    and renders; it does not load from disk.
    """

    name: ClassVar[str] = "framework"
    required_inputs: ClassVar[set[str]] = {"brief"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        fw: dict[str, Any] = inputs.extras.get("framework", {})
        glossary_mode = config.get("glossary", "minimal")
        include_sign_map = config.get("sign_map", True)
        include_transmission = config.get("transmission", False)

        glossary = fw.get("glossary", {}).get(params.language, {})
        if glossary_mode == "none":
            glossary = {}
        elif glossary_mode == "minimal":
            glossary = {k: v for k, v in glossary.items() if v.get("tier", 1) == 1}

        content = {
            "sign_map": fw.get("sign_map", []) if include_sign_map else [],
            "transmission": fw.get("transmission", []) if include_transmission else [],
            "glossary": glossary,
        }
        return RenderedBlock(name=self.name, content=content, token_estimate=rough_tokens(content))
