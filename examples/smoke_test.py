"""Smoke test: build a Context from a fake CPI event and print the rendered XML."""

from __future__ import annotations

from datetime import datetime, timezone

from researchflow.context import (
    BlockInputs,
    Brief,
    ContextParams,
    DataPack,
    HouseView,
    build,
)


def main() -> None:
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
                {
                    "id": "F-CPI-SHELTER-MOM",
                    "label": "Shelter CPI MoM",
                    "period": "2026-03",
                    "unit": "%",
                    "source": "bls",
                    "actual": 0.28,
                    "consensus": None,
                    "prior": 0.34,
                    "tier": 2,
                },
            ],
        },
    )

    house_view = HouseView(
        version="2026-04-15",
        as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
        content={
            "base_case": "Fed cuts 75bp in 2026, first cut June.",
            "tone_lean": "modestly_dovish",
            "alternatives": [
                {"label": "hawkish", "prob": 0.25, "trigger": "core >3.5% for 2 consecutive prints"},
                {"label": "dovish", "prob": 0.15, "trigger": "labour weakens materially"},
            ],
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
            {
                "when": "headline_surprise_bp > +15",
                "expect": [
                    {"asset": "ust_2y", "sign": "+"},
                    {"asset": "dxy", "sign": "+"},
                    {"asset": "equities", "sign": "-"},
                    {"asset": "cut_odds_jun", "sign": "-"},
                ],
            },
        ],
        "transmission": [
            "Higher CPI -> higher nominal yields -> stronger USD -> equities under pressure (duration channel).",
        ],
        "glossary": {
            "en": {
                "supercore": {"tier": 1, "def": "Core services ex-shelter."},
                "base_effect": {"tier": 2, "def": "YoY distortion from prior-year comparison."},
            },
            "zh_cn": {
                "supercore": {"tier": 1, "def": "核心服务通胀剔除房租。"},
            },
        },
    }

    exemplar_pool = [
        {
            "language": "en",
            "event_type": "us_cpi",
            "report_text": "Bottom line: March CPI came in cooler than expected [F-CPI-HEAD-YOY]...",
        },
        {
            "language": "en",
            "event_type": "us_cpi",
            "report_text": "Headline ticked below consensus on easing goods prices [F-CPI-HEAD-YOY]...",
        },
    ]

    inputs = BlockInputs(
        brief=brief,
        data_pack=data_pack,
        house_view=house_view,
        extras={"framework": framework, "exemplar_pool": exemplar_pool},
    )

    for recipe_name in ("brief_comment", "deep_research", "trading_daily"):
        params = ContextParams(language="en", reader_tier="pm")
        ctx = build(recipe_name, params, inputs)
        print("=" * 80)
        print(f"RECIPE: {recipe_name}")
        print(f"  rendered blocks: {ctx.trace.blocks_rendered}")
        print(f"  skipped blocks:  {ctx.trace.blocks_skipped}")
        print(f"  token estimate:  {ctx.trace.total_token_estimate}")
        if ctx.trace.notes:
            print(f"  notes:           {ctx.trace.notes}")
        print()
        print(ctx.rendered_text)
        print()


if __name__ == "__main__":
    main()
