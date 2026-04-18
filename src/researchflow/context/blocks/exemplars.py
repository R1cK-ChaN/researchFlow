from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import register_block, rough_tokens
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class ExemplarBlock:
    """Pulls k exemplar reports (analyst-written goldens) into the context.

    MVP selector: language match, then take first k. Pool comes from
    `inputs.extras['exemplar_pool']` — a list of dicts each with keys:
    `language`, `event_type`, `report_text`, and optional `tags`.
    """

    name: ClassVar[str] = "exemplars"
    required_inputs: ClassVar[set[str]] = {"brief"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        pool: list[dict[str, Any]] = inputs.extras.get("exemplar_pool", [])
        k = int(config.get("k", 2))
        want_type = inputs.brief.report_type

        same_lang = [e for e in pool if e.get("language") == params.language]
        same_type = [e for e in same_lang if e.get("event_type") == want_type] or same_lang
        picked = same_type[:k]

        content = {"exemplars": picked}
        return RenderedBlock(
            name=self.name,
            content=content,
            token_estimate=rough_tokens(content),
            trace={"pool_size": len(pool), "picked": len(picked), "k_requested": k},
        )
