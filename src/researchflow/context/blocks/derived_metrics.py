from __future__ import annotations

from typing import Any, ClassVar

from researchflow.context.blocks.base import (
    filter_facts_by_depth,
    register_block,
    rough_tokens,
)
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock


@register_block
class DerivedMetricsBlock:
    """Derives surprise / z-score / base-effect flags from the DataPack.

    MVP arithmetic only — no history look-ups. Anything needing history
    should come pre-computed in the inbound payload and will be passed
    through under `derived_metrics.precomputed`.
    """

    name: ClassVar[str] = "derived_metrics"
    required_inputs: ClassVar[set[str]] = {"data_pack"}

    def render(
        self,
        inputs: BlockInputs,
        params: ContextParams,
        config: dict[str, Any],
    ) -> RenderedBlock:
        assert inputs.data_pack is not None
        depth = config.get("include_components", "minimal")
        facts = filter_facts_by_depth(inputs.data_pack.payload.get("facts", []), depth)
        metrics: list[dict[str, Any]] = []

        if config.get("surprise", True):
            for f in facts:
                actual, consensus = f.get("actual"), f.get("consensus")
                if actual is None or consensus is None:
                    continue
                metrics.append(
                    {
                        "type": "surprise",
                        "fact_ref": f.get("id"),
                        "vs": "consensus",
                        "value": round(actual - consensus, 4),
                        "unit": f.get("unit"),
                    }
                )

        if config.get("prior_delta", True):
            for f in facts:
                actual, prior = f.get("actual"), f.get("prior")
                if actual is None or prior is None:
                    continue
                metrics.append(
                    {
                        "type": "prior_delta",
                        "fact_ref": f.get("id"),
                        "value": round(actual - prior, 4),
                        "unit": f.get("unit"),
                    }
                )

        precomputed = inputs.data_pack.payload.get("derived_precomputed", [])
        content = {"metrics": metrics, "precomputed": precomputed}
        return RenderedBlock(name=self.name, content=content, token_estimate=rough_tokens(content))
