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
from researchflow.generation.contracts import GenerationTrace, Report


@pytest.fixture
def context():
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
                    "id": "F-CPI-CORE-YOY",
                    "label": "Core CPI YoY",
                    "unit": "%",
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
        content={"base_case": "Fed cuts 75bp in 2026.", "tone_lean": "modestly_dovish"},
    )
    return build(
        "brief_comment",
        ContextParams(language="en"),
        BlockInputs(
            brief=brief,
            data_pack=data_pack,
            house_view=house_view,
            extras={"framework": {}, "exemplar_pool": []},
        ),
    )


@pytest.fixture
def make_report():
    def _make(text: str, *, recipe_name: str = "econ_brief_comment") -> Report:
        now = datetime.now(timezone.utc)
        return Report(
            recipe_name=recipe_name,
            raw_text=text,
            fact_citations=[],
            trace=GenerationTrace(model="test/model", started_at=now, finished_at=now),
        )

    return _make
