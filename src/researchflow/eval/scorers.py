"""Per-stage scorers. Each compares stage output to fixture expectations."""

from __future__ import annotations

import re
from typing import Any

from researchflow.context.contracts import Context
from researchflow.eval.contracts import StageScore
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationReport

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_WORD_RE = re.compile(r"[A-Za-z\u4e00-\u9fff]+")
_CITATION_RE = re.compile(r"\[(F-[A-Z0-9][A-Z0-9\-_]*)\]")


def score_context(context: Context, expected: dict[str, Any]) -> StageScore:
    if not expected:
        return StageScore(stage="context", passed=True, notes=["no expectations declared"])

    metrics: dict[str, Any] = {}
    notes: list[str] = []
    ok = True

    expect_blocks = expected.get("blocks_rendered")
    if expect_blocks is not None:
        missing = [b for b in expect_blocks if b not in context.trace.blocks_rendered]
        metrics["blocks_missing"] = missing
        if missing:
            ok = False
            notes.append(f"blocks not rendered: {missing}")

    must_ids = expected.get("must_contain_fact_ids", [])
    if must_ids:
        text = context.rendered_text
        missing_ids = [fid for fid in must_ids if fid not in text]
        metrics["fact_ids_missing"] = missing_ids
        if missing_ids:
            ok = False
            notes.append(f"expected fact ids not in rendered context: {missing_ids}")

    budget = expected.get("max_token_estimate")
    if budget is not None:
        metrics["token_estimate"] = context.trace.total_token_estimate
        if context.trace.total_token_estimate > budget:
            ok = False
            notes.append(
                f"token estimate {context.trace.total_token_estimate} exceeds {budget}"
            )

    return StageScore(stage="context", passed=ok, metrics=metrics, notes=notes)


def score_generation(report: Report, expected: dict[str, Any]) -> StageScore:
    if not expected:
        return StageScore(stage="generation", passed=True, notes=["no expectations declared"])

    metrics: dict[str, Any] = {}
    notes: list[str] = []
    ok = True

    must_cite = expected.get("must_cite", [])
    cited = set(report.fact_citations)
    missing = [fid for fid in must_cite if fid not in cited]
    metrics["required_citations_missing"] = missing
    if missing:
        ok = False
        notes.append(f"missing required fact citations: {missing}")

    bounds = expected.get("word_count")
    word_count = len(_WORD_RE.findall(report.raw_text))
    metrics["word_count"] = word_count
    if bounds and len(bounds) == 2:
        lo, hi = bounds
        if lo is not None and word_count < lo:
            ok = False
            notes.append(f"word count {word_count} below minimum {lo}")
        if hi is not None and word_count > hi:
            ok = False
            notes.append(f"word count {word_count} above maximum {hi}")

    required_sections = expected.get("must_have_sections", [])
    if required_sections:
        found = {_norm(m.group(1)) for m in _H2_RE.finditer(report.raw_text)}
        missing_sections = [s for s in required_sections if _norm(s) not in found]
        metrics["sections_missing"] = missing_sections
        if missing_sections:
            ok = False
            notes.append(f"missing sections: {missing_sections}")

    return StageScore(stage="generation", passed=ok, metrics=metrics, notes=notes)


def score_postprocess(report: Report, expected: dict[str, Any]) -> StageScore:
    if not expected:
        return StageScore(stage="postprocess", passed=True, notes=["no expectations declared"])

    metrics: dict[str, Any] = {}
    notes: list[str] = []
    ok = True

    if expected.get("disclaimer_injected") is True:
        has_placeholder = "{{DISCLAIMER}}" in report.raw_text
        metrics["placeholder_remaining"] = has_placeholder
        if has_placeholder:
            ok = False
            notes.append("disclaimer placeholder still present")

    return StageScore(stage="postprocess", passed=ok, metrics=metrics, notes=notes)


def score_validation(vr: ValidationReport, expected: dict[str, Any]) -> StageScore:
    if not expected:
        return StageScore(stage="validation", passed=True, notes=["no expectations declared"])

    metrics: dict[str, Any] = {
        "passed": vr.passed,
        "error_count": len(vr.errors()),
        "warning_count": len(vr.warnings()),
        "validators_run": vr.validators_run,
        "validators_skipped": vr.validators_skipped,
    }
    notes: list[str] = []
    ok = True

    if "passed" in expected and vr.passed != expected["passed"]:
        ok = False
        notes.append(f"expected passed={expected['passed']} got {vr.passed}")

    if "max_errors" in expected and len(vr.errors()) > expected["max_errors"]:
        ok = False
        notes.append(
            f"error count {len(vr.errors())} exceeds max_errors {expected['max_errors']}"
        )

    required_codes = expected.get("require_codes", [])
    seen_codes = {i.code for i in vr.issues}
    missing_codes = [c for c in required_codes if c not in seen_codes]
    if missing_codes:
        ok = False
        notes.append(f"expected issue codes not raised: {missing_codes}")

    forbidden_codes = expected.get("forbid_codes", [])
    forbidden_hit = [c for c in forbidden_codes if c in seen_codes]
    if forbidden_hit:
        ok = False
        notes.append(f"forbidden issue codes raised: {forbidden_hit}")

    metrics["codes_seen"] = sorted(seen_codes)
    return StageScore(stage="validation", passed=ok, metrics=metrics, notes=notes)


def _norm(s: str) -> str:
    return s.strip().lower().replace(" ", "_").replace("-", "_")
