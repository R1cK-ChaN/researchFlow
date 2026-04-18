"""Context builder package.

Importing this package eagerly registers all built-in blocks so that
`assembler.build` can resolve block names from recipes.
"""

from researchflow.context import blocks  # noqa: F401  (registration side-effect)
from researchflow.context.assembler import build
from researchflow.context.contracts import (
    BlockInputs,
    Brief,
    Context,
    ContextParams,
    ContextTrace,
    DataPack,
    HouseView,
    MaterialPack,
    RenderedBlock,
)

__all__ = [
    "build",
    "BlockInputs",
    "Brief",
    "Context",
    "ContextParams",
    "ContextTrace",
    "DataPack",
    "HouseView",
    "MaterialPack",
    "RenderedBlock",
]
