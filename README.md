# researchFlow

A compositional pipeline for generating sell-side research reports from structured
inputs. Owns **context assembly → LLM generation → validation**. Data fetching
and material retrieval live in sibling services and reach this pipeline via API.

The design goal is simple: let an LLM write the prose while the pipeline keeps
the numbers grounded, the economic logic honest, and the style consistent across
report types.

## Architecture

```
Brief + DataPack + MaterialPack + HouseView
                ↓
          Context Builder        ← declarative recipes, reusable blocks
                ↓
            Generator            ← single LLM call via OpenRouter
                ↓
           Validation            ← (next) numeric grounding, structure,
                ↓                   logic consistency, house-view reconciliation
    Report + ValidationTrace
```

### Context builder

Three layers:

- **Blocks** — stateless units that render a slice of context (`fact_table`,
  `derived_metrics`, `framework`, `house_view`, `exemplars`, `style_guide`, …).
  Each declares its required inputs; blocks whose inputs are absent are skipped
  and recorded in the trace.
- **Recipes** — YAML specs listing which blocks (with what config) compose a
  given report type. Adding a new report type = new YAML, no code.
- **Params** — runtime knobs (`language`, `reader_tier`) threaded through every
  block. Language affects glossary scope and exemplar selection; it does not
  create parallel code paths.

Three recipes ship out of the box: `brief_comment`, `deep_research`,
`trading_daily`. Context is rendered as XML (Claude responds better to tagged
structure than to prose or JSON for long context).

### Generator

One LLM call, whole report out. Style coherence matters more on sell-side than
composition convenience, so the generator does not interleave templated prose
with LLM prose.

Anti-hallucination is enforced at the edges, not the middle:

1. The prompt ships a `FactTable` with stable IDs; every numeric claim in the
   output must carry `[F-xxx]`.
2. A post-processor (next in the pipeline) validates every citation, rejects
   invented IDs or uncited numbers, and injects the static disclaimer.
3. Validators catch the rest.

The provider is OpenRouter. Any model you can route through OpenRouter is
callable via `GeneratorParams(model="...")`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Python 3.11+.

## Quick start

Build a context for a CPI print:

```bash
python examples/smoke_test.py
```

Generate a full report (requires `OPENROUTER_API_KEY`):

```bash
export OPENROUTER_API_KEY=sk-or-...
python examples/generate_sample.py brief_comment anthropic/claude-sonnet-4.5
```

Run the test suite:

```bash
pytest
```

## Using it in code

```python
from datetime import datetime, timezone

from researchflow.context import (
    BlockInputs, Brief, ContextParams, DataPack, HouseView, build,
)
from researchflow.generation import GeneratorParams, generate

brief = Brief(
    event_id="us_cpi_2026_03",
    event_name="US CPI — March 2026",
    release_time=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
    report_type="us_cpi",
)

data_pack = DataPack(
    event_id=brief.event_id,
    payload={"facts": [
        {"id": "F-CPI-HEAD-YOY", "label": "Headline CPI YoY",
         "unit": "%", "actual": 3.1, "consensus": 3.2, "prior": 3.0, "tier": 1},
    ]},
)

house_view = HouseView(
    version="2026-04-15",
    as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
    content={"base_case": "Fed cuts 75bp in 2026.", "tone_lean": "modestly_dovish"},
)

ctx = build(
    "brief_comment",
    ContextParams(language="en", reader_tier="pm"),
    BlockInputs(brief=brief, data_pack=data_pack, house_view=house_view,
                extras={"framework": {}, "exemplar_pool": []}),
)

report = generate(ctx, GeneratorParams(model="anthropic/claude-sonnet-4.5"))
print(report.raw_text)
print(report.fact_citations)
```

## Adding a new report type

1. Add `src/researchflow/context/recipes/<name>.yaml`.
2. Pick blocks and config. Example minimal recipe:

```yaml
name: my_report
token_budget: 6000
renderer: xml
blocks:
  - brief
  - fact_table: { include_components: minimal }
  - derived_metrics: { include_components: minimal }
  - framework: { glossary: minimal, sign_map: true }
  - house_view: { depth: summary }
  - exemplars: { k: 2 }
  - style_guide:
      length_words: [300, 500]
      sections: [bottom_line, analysis, risks]
```

3. Call `build("my_report", params, inputs)`.

No code changes needed unless you want a new block type.

## Adding a new block

Implement the `ContextBlock` protocol and decorate with `@register_block`:

```python
from typing import Any, ClassVar
from researchflow.context.blocks.base import register_block, rough_tokens
from researchflow.context.contracts import BlockInputs, ContextParams, RenderedBlock

@register_block
class CrossAssetBlock:
    name: ClassVar[str] = "cross_asset"
    required_inputs: ClassVar[set[str]] = {"data_pack"}

    def render(self, inputs: BlockInputs, params: ContextParams,
               config: dict[str, Any]) -> RenderedBlock:
        content = {"snapshot": inputs.data_pack.payload.get("cross_asset", {})}
        return RenderedBlock(name=self.name, content=content,
                             token_estimate=rough_tokens(content))
```

Import it from `researchflow/context/blocks/__init__.py` so the registration
fires on package import. It is now usable in any recipe.

## Layout

```
src/researchflow/
├── context/
│   ├── contracts.py          pydantic models
│   ├── blocks/               one module per block + base registry
│   ├── renderers/xml.py      default renderer
│   ├── recipe_loader.py      YAML → Recipe
│   ├── recipes/              brief_comment, deep_research, trading_daily
│   └── assembler.py          build(recipe, params, inputs) → Context
├── generation/
│   ├── contracts.py          GeneratorParams, Report, GenerationTrace
│   ├── prompts.py            system prompt
│   ├── provider.py           OpenRouter client
│   └── generator.py          generate(context, params) → Report
└── validation/
    ├── contracts.py          Severity, ValidationIssue, ValidationReport
    ├── postprocessor.py      post_process(report, disclaimer=...)
    ├── validators/           numeric_grounding, structure, citation_integrity
    └── pipeline.py           validate(report, context, ...) → ValidationReport
```

## Validation pipeline

Four layers, ordered cheapest-first, each producing structured issues
(`error` hard-fails the report; `warning` flags for human review):

| Validator | Kind | Catches |
|---|---|---|
| `numeric_grounding` | deterministic | decimal numbers that aren't cited, cited numbers that don't match the fact, citations to unknown fact ids |
| `structure` | deterministic | missing or out-of-order sections, length bounds, un-injected disclaimer placeholder |
| `citation_integrity` | deterministic | `[F-xxx]` citations that don't resolve to any fact in the context |
| (future) LLM judges | LLM | directional/sign-map violations, unflagged divergence from house view |

LLM judges can be added as new validators with `requires_llm = True`; the
pipeline skips them unless a `judge_client` is passed to `validate()`.

### Usage

```python
from researchflow.validation import post_process, validate

# 1. Inject disclaimer (deterministic, safe)
finalized = post_process(report, disclaimer="For institutional use only...")

# 2. Run validators
vr = validate(finalized, context)
if not vr.passed:
    for issue in vr.errors():
        print(f"[{issue.validator}:{issue.code}] {issue.message}")
```

## Status

- Context builder — implemented, 5 tests.
- Generator — implemented, 4 tests.
- Post-processor — disclaimer injection landed (canonicalization deferred).
- Validation pipeline — 3 deterministic validators landed, 23 tests.
- LLM judges (logic_consistency, house_view_reconciliation) — next.
- Eval harness over golden fixtures — final MVP piece.

## License

MIT. See `LICENSE`.
