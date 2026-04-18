from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from researchflow.context import (
    BlockInputs,
    Brief,
    ContextParams,
    DataPack,
    HouseView,
)
from researchflow.eval.mock_client import QueueClient
from researchflow.flow import run_research_flow


@pytest.fixture
def block_inputs():
    brief = Brief(
        event_id="us_cpi_2026_03",
        event_name="US CPI — March 2026",
        release_time=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    return BlockInputs(
        brief=brief,
        data_pack=DataPack(
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
                    }
                ]
            },
        ),
        house_view=HouseView(
            version="v",
            as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
            content={"base_case": "cuts", "tone_lean": "dovish"},
        ),
        extras={"framework": {}, "exemplar_pool": []},
    )


def _generator_output() -> str:
    return (
        "## Bottom line\nHeadline slipped to 3.1% [F-CPI-HEAD-YOY] below the 3.2% "
        "consensus [F-CPI-HEAD-YOY]. " + ("word " * 60) + "\n\n"
        "## What happened\n" + ("word " * 80) + "\n\n"
        "## What it means\n" + ("word " * 50) + "\n\n"
        "{{DISCLAIMER}}"
    )


def test_flow_returns_complete_result_without_runs_dir(block_inputs):
    client = QueueClient([_generator_output(), '{"violations": []}'])
    result = run_research_flow(
        block_inputs,
        ContextParams(language="en"),
        "brief_comment",
        generator_client=client,
        judge_client=client,
    )
    assert result.run_id
    assert result.report.fact_citations == ["F-CPI-HEAD-YOY"]
    assert result.validation.passed
    stages = {s.stage for s in result.stage_summary}
    assert stages == {"context", "generation", "postprocess", "validation"}
    assert result.run_dir is None


def test_flow_writes_per_stage_audit_artifacts(block_inputs, tmp_path):
    client = QueueClient([_generator_output(), '{"violations": []}'])
    result = run_research_flow(
        block_inputs,
        ContextParams(language="en"),
        "brief_comment",
        generator_client=client,
        judge_client=client,
        runs_dir=tmp_path,
    )
    run_dir = tmp_path / result.run_id
    assert (run_dir / "01_context" / "output.xml").is_file()
    assert (run_dir / "02_generation" / "output.md").is_file()
    assert (run_dir / "03_postprocess" / "output.md").is_file()
    assert (run_dir / "04_validation" / "report.json").is_file()
    assert (run_dir / "flow_summary.json").is_file()

    summary = json.loads((run_dir / "flow_summary.json").read_text())
    assert summary["recipe"] == "brief_comment"
    assert summary["validation_passed"] is True
    assert summary["fact_citations"] == ["F-CPI-HEAD-YOY"]


def test_flow_uses_explicit_run_id(block_inputs, tmp_path):
    client = QueueClient([_generator_output(), '{"violations": []}'])
    result = run_research_flow(
        block_inputs,
        ContextParams(),
        "brief_comment",
        generator_client=client,
        judge_client=client,
        runs_dir=tmp_path,
        run_id="custom_run_1",
    )
    assert result.run_id == "custom_run_1"
    assert (tmp_path / "custom_run_1").is_dir()


def test_flow_postprocess_injects_disclaimer(block_inputs):
    client = QueueClient([_generator_output(), '{"violations": []}'])
    result = run_research_flow(
        block_inputs,
        ContextParams(),
        "brief_comment",
        generator_client=client,
        judge_client=client,
        disclaimer="CUSTOM_DISCLAIMER_XYZ",
    )
    assert "{{DISCLAIMER}}" not in result.report.raw_text
    assert "CUSTOM_DISCLAIMER_XYZ" in result.report.raw_text
