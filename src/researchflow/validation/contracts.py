"""Contracts for post-processing and validation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    validator: str
    severity: Severity
    code: str
    message: str
    location: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    validators_run: list[str] = Field(default_factory=list)
    validators_skipped: list[str] = Field(default_factory=list)

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]
