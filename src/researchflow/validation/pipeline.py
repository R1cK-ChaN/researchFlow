"""Validation orchestrator: run registered validators, aggregate issues."""

from __future__ import annotations

from typing import Any

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationReport
from researchflow.validation.validators import all_validators, get_validator


def validate(
    report: Report,
    context: Context,
    *,
    enabled: list[str] | None = None,
    judge_client: Any | None = None,
    configs: dict[str, dict] | None = None,
) -> ValidationReport:
    """Run the validation pipeline over a report.

    `enabled` — subset of validator names to run; default is all registered.
    `judge_client` — optional LLM client for validators with requires_llm=True.
                     Validators needing a judge are skipped if no client.
    `configs` — per-validator config dict keyed by validator name.
    """
    configs = configs or {}
    names = enabled if enabled is not None else all_validators()

    run: list[str] = []
    skipped: list[str] = []
    all_issues = []

    for name in names:
        v = get_validator(name)
        if getattr(v, "requires_llm", False) and judge_client is None:
            skipped.append(f"{name} (no judge_client)")
            continue
        run.append(name)
        all_issues.extend(v.validate(report, context, configs.get(name, {})))

    passed = not any(i.severity == Severity.ERROR for i in all_issues)
    return ValidationReport(
        passed=passed,
        issues=all_issues,
        validators_run=run,
        validators_skipped=skipped,
    )
