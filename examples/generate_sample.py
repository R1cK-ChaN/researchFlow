"""End-to-end example: build context + call OpenRouter to generate a report.

Requires OPENROUTER_API_KEY in the environment.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from researchflow.context import (
    BlockInputs,
    Brief,
    ContextParams,
    DataPack,
    HouseView,
    build,
)
from researchflow.generation import GeneratorParams, generate


def main() -> None:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set — set it and re-run.", file=sys.stderr)
        sys.exit(1)

    recipe_name = sys.argv[1] if len(sys.argv) > 1 else "brief_comment"
    model = sys.argv[2] if len(sys.argv) > 2 else "anthropic/claude-sonnet-4.5"

    brief = Brief(
        event_id="us_cpi_2026_03",
        event_name="US CPI — March 2026",
        release_time=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    data_pack = DataPack(
        event_id=brief.event_id,
        payload={
            "facts": [
                {
                    "id": "F-CPI-HEAD-YOY",
                    "label": "Headline CPI YoY",
                    "period": "2026-03",
                    "unit": "%",
                    "source": "bls",
                    "actual": 3.1,
                    "consensus": 3.2,
                    "prior": 3.0,
                    "tier": 1,
                },
                {
                    "id": "F-CPI-CORE-YOY",
                    "label": "Core CPI YoY",
                    "period": "2026-03",
                    "unit": "%",
                    "source": "bls",
                    "actual": 3.3,
                    "consensus": 3.3,
                    "prior": 3.4,
                    "tier": 1,
                },
            ]
        },
    )
    house_view = HouseView(
        version="2026-04-15",
        as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
        content={
            "base_case": "Fed cuts 75bp in 2026, first cut June.",
            "tone_lean": "modestly_dovish",
        },
    )
    framework = {
        "sign_map": [
            {
                "when": "headline_surprise_bp < -15",
                "expect": [
                    {"asset": "ust_2y", "sign": "-"},
                    {"asset": "dxy", "sign": "-"},
                    {"asset": "equities", "sign": "+"},
                    {"asset": "cut_odds_jun", "sign": "+"},
                ],
            },
        ],
        "glossary": {
            "en": {"supercore": {"tier": 1, "def": "Core services ex-shelter."}},
        },
    }

    ctx = build(
        recipe_name,
        ContextParams(language="en", reader_tier="pm"),
        BlockInputs(
            brief=brief,
            data_pack=data_pack,
            house_view=house_view,
            extras={"framework": framework, "exemplar_pool": []},
        ),
    )

    report = generate(ctx, GeneratorParams(model=model, temperature=0.3, max_tokens=2000))

    print("=" * 80)
    print(f"MODEL: {report.trace.model}")
    print(f"USAGE: {report.trace.usage}")
    print(f"CITED FACTS: {report.fact_citations}")
    print("=" * 80)
    print(report.raw_text)


if __name__ == "__main__":
    main()
