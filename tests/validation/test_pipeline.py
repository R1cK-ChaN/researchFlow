from __future__ import annotations

from researchflow.validation import post_process, validate
from researchflow.validation.validators.base import all_validators


def test_pipeline_runs_all_deterministic_validators(context, make_report):
    report = make_report("## Bottom line\nWord " * 180 + "{{DISCLAIMER}}")
    report = post_process(report)
    vr = validate(report, context)
    assert set(vr.validators_run) == set(all_validators())
    assert vr.validators_skipped == []


def test_pipeline_passes_on_clean_report(context, make_report):
    body = "word " * 60
    clean = (
        "## Bottom line\nHeadline rose 3.1% [F-CPI-HEAD-YOY]. " + body + "\n\n"
        "## What happened\nCore at 3.3% [F-CPI-CORE-YOY]. " + body + "\n\n"
        "## What it means\nBond-friendly. " + body + "\n\n"
        "{{DISCLAIMER}}"
    )
    report = post_process(make_report(clean))
    vr = validate(report, context)
    assert vr.passed, [i.model_dump() for i in vr.errors()]


def test_pipeline_fails_on_fabricated_number(context, make_report):
    body = "word " * 60
    dirty = (
        "## Bottom line\nHeadline jumped to 5.9% [F-CPI-HEAD-YOY]. " + body + "\n\n"
        "## What happened\n" + body + "\n\n"
        "## What it means\n" + body + "\n\n"
        "{{DISCLAIMER}}"
    )
    report = post_process(make_report(dirty))
    vr = validate(report, context)
    assert not vr.passed
    assert any(i.code == "value_mismatch" for i in vr.errors())


def test_pipeline_enabled_subset(context, make_report):
    report = post_process(make_report("text [F-NOT-REAL] {{DISCLAIMER}}"))
    vr = validate(report, context, enabled=["citation_integrity"])
    assert vr.validators_run == ["citation_integrity"]
    assert any(i.code == "unknown_fact_id" for i in vr.errors())
