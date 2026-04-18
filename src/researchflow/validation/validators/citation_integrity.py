"""Every [F-xxx] in the report must resolve to a fact in the context's fact_table."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationIssue
from researchflow.validation.validators.base import get_fact_map, register_validator

_CITATION_RE = re.compile(r"\[(F-[A-Z0-9][A-Z0-9\-_]*)\]")


@register_validator
class CitationIntegrityValidator:
    name: ClassVar[str] = "citation_integrity"
    requires_llm: ClassVar[bool] = False

    def validate(
        self,
        report: Report,
        context: Context,
        config: dict[str, Any],
    ) -> list[ValidationIssue]:
        fact_map = get_fact_map(context)
        issues: list[ValidationIssue] = []
        seen: set[str] = set()

        for m in _CITATION_RE.finditer(report.raw_text):
            fact_id = m.group(1)
            if fact_id in seen:
                continue
            seen.add(fact_id)
            if fact_id not in fact_map:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=Severity.ERROR,
                        code="unknown_fact_id",
                        message=f"Report cites [{fact_id}] but no such fact in the context's fact_table.",
                        context={"fact_id": fact_id, "available": sorted(fact_map)},
                    )
                )
        return issues
