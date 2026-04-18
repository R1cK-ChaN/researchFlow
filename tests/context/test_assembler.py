from __future__ import annotations

from datetime import datetime, timezone

import pytest

from researchflow.context import (
    BlockInputs,
    Brief,
    ContextParams,
    DataPack,
    HouseView,
    build,
)


@pytest.fixture
def inputs() -> BlockInputs:
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
                    "unit": "%",
                    "actual": 3.1,
                    "consensus": 3.2,
                    "prior": 3.0,
                    "tier": 1,
                },
                {
                    "id": "F-CPI-SHELTER-MOM",
                    "label": "Shelter CPI MoM",
                    "unit": "%",
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
        content={"base_case": "Fed cuts 75bp in 2026.", "tone_lean": "modestly_dovish"},
    )
    framework = {
        "sign_map": [{"when": "headline_surprise_bp < -15", "expect": []}],
        "glossary": {"en": {"supercore": {"tier": 1, "def": "Core services ex-shelter."}}},
    }
    return BlockInputs(
        brief=brief,
        data_pack=data_pack,
        house_view=house_view,
        extras={"framework": framework, "exemplar_pool": []},
    )


def test_brief_comment_renders(inputs: BlockInputs) -> None:
    ctx = build("brief_comment", ContextParams(language="en"), inputs)
    assert ctx.recipe_name == "econ_brief_comment"
    assert "brief" in ctx.trace.blocks_rendered
    assert "fact_table" in ctx.trace.blocks_rendered
    assert "<context>" in ctx.rendered_text
    assert "F-CPI-HEAD-YOY" in ctx.rendered_text


def test_fact_table_depth_filtering(inputs: BlockInputs) -> None:
    brief_ctx = build("brief_comment", ContextParams(), inputs)
    deep_ctx = build("deep_research", ContextParams(), inputs)
    # brief recipe uses `include_components: minimal` → tier-2 shelter dropped
    assert "F-CPI-SHELTER-MOM" not in brief_ctx.rendered_text
    # deep research uses `include_components: full` → tier-2 kept
    assert "F-CPI-SHELTER-MOM" in deep_ctx.rendered_text


def test_surprise_metric_computed(inputs: BlockInputs) -> None:
    ctx = build("brief_comment", ContextParams(), inputs)
    # headline actual 3.1 - consensus 3.2 = -0.1
    assert "-0.1" in ctx.rendered_text


def test_language_switches_glossary(inputs: BlockInputs) -> None:
    ctx_en = build("deep_research", ContextParams(language="en"), inputs)
    ctx_cn = build("deep_research", ContextParams(language="zh_cn"), inputs)
    assert "Core services ex-shelter" in ctx_en.rendered_text
    assert "Core services ex-shelter" not in ctx_cn.rendered_text


def test_missing_house_view_skips_block() -> None:
    brief = Brief(
        event_id="e1",
        event_name="e1",
        release_time=datetime(2026, 4, 10, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    inputs = BlockInputs(
        brief=brief,
        data_pack=DataPack(event_id="e1", payload={"facts": []}),
        house_view=None,
    )
    ctx = build("brief_comment", ContextParams(), inputs)
    assert any("house_view" in s for s in ctx.trace.blocks_skipped)
    assert "house_view" not in ctx.trace.blocks_rendered
