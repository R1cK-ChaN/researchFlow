"""Context assembler: recipe + params + inputs → Context."""

from __future__ import annotations

from pathlib import Path

from researchflow.context.blocks.base import get_block
from researchflow.context.contracts import (
    BlockInputs,
    Context,
    ContextParams,
    ContextTrace,
    RenderedBlock,
)
from researchflow.context.recipe_loader import Recipe, load_recipe
from researchflow.context.renderers import get_renderer


def build(
    recipe: str | Recipe,
    params: ContextParams,
    inputs: BlockInputs,
    recipes_dir: Path | None = None,
) -> Context:
    """Assemble a Context from a recipe name (or Recipe object), params, and inputs.

    Blocks declaring required_inputs that are missing from `inputs` are
    skipped and recorded in the ContextTrace rather than erroring — this
    keeps the pipeline degradation-tolerant during iteration.
    """
    recipe_obj = recipe if isinstance(recipe, Recipe) else load_recipe(recipe, recipes_dir)

    rendered: list[RenderedBlock] = []
    skipped: list[str] = []
    notes: list[str] = []
    total = 0

    for spec in recipe_obj.blocks:
        block = get_block(spec.name)
        missing = [req for req in block.required_inputs if getattr(inputs, req, None) is None]
        if missing:
            skipped.append(f"{spec.name} (missing inputs: {sorted(missing)})")
            continue
        rb = block.render(inputs, params, spec.config)
        rendered.append(rb)
        total += rb.token_estimate

    if total > recipe_obj.token_budget:
        notes.append(f"token estimate {total} exceeds budget {recipe_obj.token_budget}")

    renderer = get_renderer(recipe_obj.renderer)
    text = renderer(rendered)

    trace = ContextTrace(
        recipe_name=recipe_obj.name,
        params=params,
        blocks_rendered=[b.name for b in rendered],
        blocks_skipped=skipped,
        total_token_estimate=total,
        notes=notes,
    )
    return Context(
        recipe_name=recipe_obj.name,
        params=params,
        rendered_text=text,
        blocks=rendered,
        trace=trace,
    )
