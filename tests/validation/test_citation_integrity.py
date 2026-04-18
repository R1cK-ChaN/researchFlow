from __future__ import annotations

from researchflow.validation.validators.citation_integrity import CitationIntegrityValidator


def _issues(report, context):
    return CitationIntegrityValidator().validate(report, context, {})


def test_valid_citation_passes(context, make_report):
    text = "Headline rose [F-CPI-HEAD-YOY] and core [F-CPI-CORE-YOY]."
    assert _issues(make_report(text), context) == []


def test_unknown_citation_flagged(context, make_report):
    text = "See [F-MADE-UP] for details."
    issues = _issues(make_report(text), context)
    assert len(issues) == 1
    assert issues[0].code == "unknown_fact_id"
    assert issues[0].context["fact_id"] == "F-MADE-UP"


def test_duplicate_unknown_reported_once(context, make_report):
    text = "[F-MADE-UP] and again [F-MADE-UP]."
    issues = _issues(make_report(text), context)
    assert len(issues) == 1
