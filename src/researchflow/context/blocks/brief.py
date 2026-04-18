from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import register_block, rough_tokens
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class BriefBlock:
    name: ClassVar[str] = "brief"
    required_inputs: ClassVar[set[str]] = {"brief"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        b = inputs.brief
        content = {
            "event": b.event_name,
            "event_id": b.event_id,
            "release_time": b.release_time.isoformat(),
            "report_type": b.report_type,
            "reader_tier": params.reader_tier,
            "language": params.language,
        }
        return RenderedBlock(name=self.name, content=content, token_estimate=rough_tokens(content))
