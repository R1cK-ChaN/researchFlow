"""Deterministic post-processing of raw generator output.

MVP scope: inject the static disclaimer where the generator left its
placeholder. Citation canonicalization (swapping LLM numbers for FactTable
values) is intentionally deferred — it mutates LLM text and should only land
once the eval harness can compare before/after.
"""

from __future__ import annotations

from researchflow.generation.contracts import Report

DEFAULT_DISCLAIMER = (
    "This note is for institutional use only. It does not constitute investment "
    "advice, an offer to sell, or a solicitation of an offer to buy any security. "
    "Past performance is not indicative of future results."
)

PLACEHOLDER = "{{DISCLAIMER}}"


def post_process(report: Report, *, disclaimer: str | None = None) -> Report:
    """Return a new Report with the disclaimer placeholder replaced.

    If the generator omitted the placeholder, the text is returned unchanged;
    the structure validator will flag it separately.
    """
    text = report.raw_text
    if PLACEHOLDER in text:
        text = text.replace(PLACEHOLDER, disclaimer or DEFAULT_DISCLAIMER)
    return report.model_copy(update={"raw_text": text})
