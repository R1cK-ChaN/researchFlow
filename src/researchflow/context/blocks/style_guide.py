from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import register_block, rough_tokens
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class StyleGuideBlock:
    name: ClassVar[str] = "style_guide"
    required_inputs: ClassVar[set[str]] = {"brief"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        content = {
            "language": params.language,
            "reader_tier": params.reader_tier,
            "length_words": config.get("length_words", [200, 400]),
            "sections": config.get("sections", []),
            "citation_required": config.get("citation_required", True),
            "disclaimer_placeholder": "{{DISCLAIMER}}",
            "voice_notes": config.get("voice_notes", []),
        }
        return RenderedBlock(name=self.name, content=content, token_estimate=rough_tokens(content))
