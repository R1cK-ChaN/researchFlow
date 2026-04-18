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
from researchflow.eval.scorers import (
    score_context,
    score_generation,
    score_postprocess,
    score_validation,
)
from researchflow.generation.contracts import GenerationTrace, Report
from researchflow.validation.contracts import Severity, ValidationIssue, ValidationReport


def _ctx():
    brief = Brief(
        event_id="e1",
        event_name="e1",
        release_time=datetime(2026, 4, 10, tzinfo=timezone.utc),
        report_type="us_cpi",
    )
    data_pack = DataPack(
        event_id="e1",
        payload={
            "facts": [
                {"id": "F-CPI-HEAD-YOY", "actual": 3.1, "consensus": 3.2, "prior": 3.0, "tier": 1},
            ]
        },
    )
    house_view = HouseView(
        version="v",
        as_of=datetime(2026, 4, 15, tzinfo=timezone.utc),
        content={"base_case": "x"},
    )
    return build(
        "brief_comment",
        ContextParams(),
        BlockInputs(
            brief=brief,
            data_pack=data_pack,
            house_view=house_view,
            extras={"framework": {}, "exemplar_pool": []},
        ),
    )


def _report(text="some body [F-CPI-HEAD-YOY]"):
    now = datetime.now(timezone.utc)
    return Report(
        recipe_name="econ_brief_comment",
        raw_text=text,
        fact_citations=["F-CPI-HEAD-YOY"],
        trace=GenerationTrace(model="m", started_at=now, finished_at=now),
    )


def test_score_context_passes_when_blocks_present():
    score = score_context(_ctx(), {"blocks_rendered": ["brief", "fact_table"]})
    assert score.passed


def test_score_context_fails_when_block_missing():
    score = score_context(_ctx(), {"blocks_rendered": ["brief", "not_a_block"]})
    assert not score.passed
    assert "not_a_block" in str(score.notes)


def test_score_context_checks_fact_ids_present():
    score = score_context(_ctx(), {"must_contain_fact_ids": ["F-CPI-HEAD-YOY"]})
    assert score.passed
    score = score_context(_ctx(), {"must_contain_fact_ids": ["F-MISSING"]})
    assert not score.passed


def test_score_generation_requires_citations():
    r = _report("text [F-CPI-HEAD-YOY]")
    assert score_generation(r, {"must_cite": ["F-CPI-HEAD-YOY"]}).passed
    assert not score_generation(r, {"must_cite": ["F-OTHER"]}).passed


def test_score_generation_word_count_bounds():
    short = _report("one two [F-CPI-HEAD-YOY]")
    assert not score_generation(short, {"word_count": [100, 200]}).passed


def test_score_postprocess_flags_placeholder():
    r = _report("body {{DISCLAIMER}}")
    score = score_postprocess(r, {"disclaimer_injected": True})
    assert not score.passed


def test_score_validation_matches_pass_flag():
    vr = ValidationReport(passed=True, issues=[], validators_run=["structure"], validators_skipped=[])
    assert score_validation(vr, {"passed": True, "max_errors": 0}).passed

    vr_fail = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                validator="numeric_grounding",
                severity=Severity.ERROR,
                code="value_mismatch",
                message="x",
            )
        ],
        validators_run=["numeric_grounding"],
        validators_skipped=[],
    )
    assert not score_validation(vr_fail, {"passed": True, "max_errors": 0}).passed


def test_score_validation_required_codes():
    vr = ValidationReport(
        passed=False,
        issues=[
            ValidationIssue(
                validator="x",
                severity=Severity.ERROR,
                code="uncited_number",
                message="y",
            )
        ],
        validators_run=["x"],
        validators_skipped=[],
    )
    assert score_validation(vr, {"require_codes": ["uncited_number"]}).passed
    assert not score_validation(vr, {"require_codes": ["unknown_fact_id"]}).passed
