from __future__ import annotations

from researchflow.validation.validators.structure import StructureValidator


def _issues(report, context):
    return StructureValidator().validate(report, context, {})


def _codes(issues):
    return {i.code for i in issues}


def test_correct_structure_passes(context, make_report):
    body_words = "lorem ipsum " * 80
    text = (
        "## Bottom line\n"
        + body_words
        + "\n\n## What happened\n"
        + body_words
        + "\n\n## What it means\n"
        + body_words
        + "\n\nDisclaimer: ..."
    )
    issues = _issues(make_report(text), context)
    assert "missing_sections" not in _codes(issues)
    assert "disclaimer_not_injected" not in _codes(issues)


def test_missing_section_flagged(context, make_report):
    text = "## Bottom line\ntext\n\n## What it means\ntext\n\nDisclaimer."
    issues = _issues(make_report(text), context)
    assert "missing_sections" in _codes(issues)


def test_out_of_order_sections_warned(context, make_report):
    text = "## What it means\nA\n\n## What happened\nB\n\n## Bottom line\nC\n\nDisclaimer."
    issues = _issues(make_report(text), context)
    assert "section_order" in _codes(issues)


def test_too_short_warning(context, make_report):
    text = "## Bottom line\nshort\n\n## What happened\ntext\n\n## What it means\ntext\n\nDisclaimer."
    issues = _issues(make_report(text), context)
    assert "too_short" in _codes(issues)


def test_disclaimer_placeholder_flagged(context, make_report):
    body = "word " * 180
    text = (
        "## Bottom line\n" + body
        + "\n## What happened\n" + body
        + "\n## What it means\n" + body
        + "\n\n{{DISCLAIMER}}"
    )
    issues = _issues(make_report(text), context)
    assert "disclaimer_not_injected" in _codes(issues)
