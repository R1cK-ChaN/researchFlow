from __future__ import annotations

from researchflow.validation import DEFAULT_DISCLAIMER, post_process


def test_injects_default_disclaimer(make_report):
    report = make_report("## Bottom line\nAll good.\n\n{{DISCLAIMER}}")
    out = post_process(report)
    assert "{{DISCLAIMER}}" not in out.raw_text
    assert DEFAULT_DISCLAIMER in out.raw_text


def test_custom_disclaimer_overrides_default(make_report):
    report = make_report("text {{DISCLAIMER}}")
    out = post_process(report, disclaimer="XYZ")
    assert out.raw_text == "text XYZ"


def test_missing_placeholder_leaves_text_unchanged(make_report):
    report = make_report("no placeholder here")
    out = post_process(report)
    assert out.raw_text == "no placeholder here"


def test_postprocess_returns_new_object(make_report):
    report = make_report("x {{DISCLAIMER}}")
    out = post_process(report)
    assert out is not report
    assert report.raw_text == "x {{DISCLAIMER}}"  # original unchanged
