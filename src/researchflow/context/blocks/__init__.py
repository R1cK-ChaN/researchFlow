"""Block implementations. Importing this module registers each block."""

from researchflow.context.blocks import (  # noqa: F401
    brief,
    derived_metrics,
    exemplars,
    fact_table,
    framework,
    house_view,
    style_guide,
)
from researchflow.context.blocks.base import all_blocks, get_block, register_block

__all__ = ["all_blocks", "get_block", "register_block"]
