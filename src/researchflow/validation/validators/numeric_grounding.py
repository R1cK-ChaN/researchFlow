"""Numeric grounding: every decimal number must cite a fact whose value matches.

MVP only checks decimal numbers (`\\d+\\.\\d+`); integers are skipped because
they are dominated by years, counts, and basis points that are rarely raw
data claims. Tighten later via a domain-aware extractor.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationIssue
from researchflow.validation.validators.base import get_fact_map, register_validator

_NUMBER_RE = re.compile(r"-?\d+\.\d+")
_CITATION_RE = re.compile(r"\[(F-[A-Z0-9][A-Z0-9\-_]*)\]")

_CANDIDATE_KEYS = ("actual", "consensus", "prior", "value", "mom", "yoy", "qoq", "ann")
_DEFAULT_LOOKAHEAD = 60
_DEFAULT_TOLERANCE = 0.05


@register_validator
class NumericGroundingValidator:
    name: ClassVar[str] = "numeric_grounding"
    requires_llm: ClassVar[bool] = False

    def validate(
        self,
        report: Report,
        context: Context,
        config: dict[str, Any],
    ) -> list[ValidationIssue]:
        lookahead = int(config.get("lookahead_chars", _DEFAULT_LOOKAHEAD))
        tolerance = float(config.get("tolerance", _DEFAULT_TOLERANCE))
        fact_map = get_fact_map(context)
        issues: list[ValidationIssue] = []
        text = report.raw_text

        for m in _NUMBER_RE.finditer(text):
            value = float(m.group(0))
            span_end = m.end()
            window = text[span_end : span_end + lookahead]
            cite = _CITATION_RE.search(window)
            snippet = text[max(0, m.start() - 30) : span_end + 20]

            if cite is None:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=Severity.ERROR,
                        code="uncited_number",
                        message=f"Decimal {value} at offset {m.start()} is not followed by a fact citation.",
                        location=f"offset={m.start()}",
                        context={"value": value, "snippet": snippet},
                    )
                )
                continue

            fact_id = cite.group(1)
            fact = fact_map.get(fact_id)
            if fact is None:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=Severity.ERROR,
                        code="unknown_fact_id",
                        message=f"Citation [{fact_id}] near {value} does not resolve to any fact.",
                        location=f"offset={m.start()}",
                        context={"fact_id": fact_id, "value": value},
                    )
                )
                continue

            candidates = _candidate_values(fact)
            if not any(abs(value - cv) <= tolerance for cv in candidates):
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=Severity.ERROR,
                        code="value_mismatch",
                        message=(
                            f"Cited value {value} does not match any value in fact {fact_id}: "
                            f"{candidates}."
                        ),
                        location=f"offset={m.start()}",
                        context={
                            "cited_value": value,
                            "fact_id": fact_id,
                            "fact_values": candidates,
                            "tolerance": tolerance,
                        },
                    )
                )

        return issues


def _candidate_values(fact: dict) -> list[float]:
    return [float(fact[k]) for k in _CANDIDATE_KEYS if isinstance(fact.get(k), (int, float))]
