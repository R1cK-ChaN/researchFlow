from __future__ import annotations

from researchflow.validation.validators.numeric_grounding import NumericGroundingValidator


def _issues(report, context):
    return NumericGroundingValidator().validate(report, context, {})


def test_matching_cited_value_passes(context, make_report):
    text = "Headline CPI rose 3.1% YoY [F-CPI-HEAD-YOY]."
    assert _issues(make_report(text), context) == []


def test_consensus_match_passes(context, make_report):
    text = "Consensus was 3.2% [F-CPI-HEAD-YOY]."
    assert _issues(make_report(text), context) == []


def test_value_mismatch_flagged(context, make_report):
    text = "Headline came in at 4.5% [F-CPI-HEAD-YOY]."
    issues = _issues(make_report(text), context)
    assert len(issues) == 1
    assert issues[0].code == "value_mismatch"
    assert issues[0].severity.value == "error"


def test_uncited_number_flagged(context, make_report):
    text = "Inflation fell to 2.8%, well below trend."
    issues = _issues(make_report(text), context)
    assert any(i.code == "uncited_number" for i in issues)


def test_unknown_fact_id_flagged(context, make_report):
    text = "Strange figure 9.9% [F-NOT-A-FACT]."
    issues = _issues(make_report(text), context)
    assert any(i.code == "unknown_fact_id" for i in issues)


def test_integer_years_not_flagged(context, make_report):
    text = "Over 2025, headline CPI rose 3.1% [F-CPI-HEAD-YOY]."
    assert _issues(make_report(text), context) == []


def test_tolerance_respected(context, make_report):
    # Fact values: actual=3.1, consensus=3.2, prior=3.0. Default tol=0.05.
    assert _issues(make_report("Reported 3.14% [F-CPI-HEAD-YOY]."), context) == []
    issues = _issues(make_report("Reported 2.80% [F-CPI-HEAD-YOY]."), context)
    assert any(i.code == "value_mismatch" for i in issues)
