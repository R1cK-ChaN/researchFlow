"""Structural checks: sections, ordering, length bounds, disclaimer injection."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationIssue
from researchflow.validation.validators.base import get_style_guide, register_validator

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_WORD_RE = re.compile(r"[A-Za-z\u4e00-\u9fff]+")


@register_validator
class StructureValidator:
    name: ClassVar[str] = "structure"
    requires_llm: ClassVar[bool] = False

    def validate(
        self,
        report: Report,
        context: Context,
        config: dict[str, Any],
        *,
        judge_client: Any = None,
    ) -> list[ValidationIssue]:
        guide = get_style_guide(context)
        if not guide:
            return []

        issues: list[ValidationIssue] = []
        text = report.raw_text

        issues.extend(_check_sections(text, guide, self.name))
        issues.extend(_check_length(text, guide, self.name))
        issues.extend(_check_disclaimer(text, guide, self.name))
        return issues


def _normalize(section: str) -> str:
    return section.strip().lower().replace(" ", "_").replace("-", "_")


def _check_sections(text: str, guide: dict, validator_name: str) -> list[ValidationIssue]:
    expected = [_normalize(s) for s in guide.get("sections", [])]
    if not expected:
        return []

    found = [_normalize(m.group(1)) for m in _H2_RE.finditer(text)]
    issues: list[ValidationIssue] = []

    missing = [s for s in expected if s not in found]
    if missing:
        issues.append(
            ValidationIssue(
                validator=validator_name,
                severity=Severity.ERROR,
                code="missing_sections",
                message=f"Missing required sections: {missing}",
                context={"expected": expected, "found": found},
            )
        )

    present_in_order = [f for f in found if f in expected]
    canonical_indices = [expected.index(s) for s in present_in_order]
    if canonical_indices != sorted(canonical_indices):
        issues.append(
            ValidationIssue(
                validator=validator_name,
                severity=Severity.WARNING,
                code="section_order",
                message=f"Sections not in expected order. Expected {expected}; got {present_in_order}.",
                context={"expected": expected, "found_ordered": present_in_order},
            )
        )
    return issues


def _check_length(text: str, guide: dict, validator_name: str) -> list[ValidationIssue]:
    bounds = guide.get("length_words") or []
    if len(bounds) != 2:
        return []
    low, high = bounds
    count = len(_WORD_RE.findall(text))
    issues: list[ValidationIssue] = []
    if low is not None and count < low:
        issues.append(
            ValidationIssue(
                validator=validator_name,
                severity=Severity.WARNING,
                code="too_short",
                message=f"Word count {count} below minimum {low}.",
                context={"word_count": count, "min": low, "max": high},
            )
        )
    if high is not None and count > high:
        issues.append(
            ValidationIssue(
                validator=validator_name,
                severity=Severity.WARNING,
                code="too_long",
                message=f"Word count {count} above maximum {high}.",
                context={"word_count": count, "min": low, "max": high},
            )
        )
    return issues


def _check_disclaimer(text: str, guide: dict, validator_name: str) -> list[ValidationIssue]:
    placeholder = guide.get("disclaimer_placeholder") or "{{DISCLAIMER}}"
    if placeholder in text:
        return [
            ValidationIssue(
                validator=validator_name,
                severity=Severity.ERROR,
                code="disclaimer_not_injected",
                message=f"Disclaimer placeholder '{placeholder}' still present — post-processor did not run or text was mutated.",
                context={"placeholder": placeholder},
            )
        ]
    return []
