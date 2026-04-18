"""LLM judge: does the report contradict the house view without flagging divergence?"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationIssue
from researchflow.validation.judge import DEFAULT_JUDGE_MODEL, PARSE_ERROR_SENTINEL, run_judge
from researchflow.validation.validators.base import register_validator

SYSTEM_PROMPT = """\
You are a compliance reviewer checking a sell-side research report for
consistency with the firm's current house view.

Input format:
- <report>: the draft report text.
- <house_view>: the current house view (base_case, tone_lean, alternatives).

Your task: identify statements in the report that either:
(a) contradict the house view's base_case WITHOUT explicitly flagging
    divergence, or
(b) claim a tone (hawkish / dovish / neutral) opposite to tone_lean without
    explicit justification.

Do NOT flag:
- Statements consistent with the house view.
- Explicitly flagged divergences (e.g. "we now diverge from our base case
  because ...", "this changes our forecast ...", "vs our prior view").
- Clearly hypothetical scenario discussion ("the hawkish tail case would...").

Output format: a single JSON object with key "violations", value is a list.
Each violation is an object with keys:
- "quote": the exact verbatim substring from the report.
- "contradicts": what in the house view it contradicts.
- "flagged": true/false — whether the report explicitly acknowledges it.
- "explanation": one short sentence.

If no violations, return {"violations": []}.
Output ONLY the JSON object. No preamble, no fences, no trailing text.
"""


@register_validator
class HouseViewReconciliationValidator:
    name: ClassVar[str] = "house_view_reconciliation"
    requires_llm: ClassVar[bool] = True

    def validate(
        self,
        report: Report,
        context: Context,
        config: dict[str, Any],
        *,
        judge_client: Any = None,
    ) -> list[ValidationIssue]:
        if judge_client is None:
            return []

        house_view = _extract_block(context, "house_view")
        if not house_view:
            return []

        user_content = (
            f"<report>\n{report.raw_text}\n</report>\n\n"
            f"<house_view>\n{json.dumps(house_view, indent=2, ensure_ascii=False)}\n</house_view>"
        )

        violations = run_judge(
            judge_client,
            model=config.get("model", DEFAULT_JUDGE_MODEL),
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            temperature=config.get("temperature", 0.0),
            max_tokens=config.get("max_tokens", 2000),
        )
        return [self._to_issue(v) for v in violations]

    def _to_issue(self, v: dict) -> ValidationIssue:
        if v.get(PARSE_ERROR_SENTINEL):
            return ValidationIssue(
                validator=self.name,
                severity=Severity.INFO,
                code="judge_output_malformed",
                message=f"Judge output did not parse: {v.get('detail')}",
                context={"raw_snippet": v.get("raw", "")},
            )
        flagged = bool(v.get("flagged"))
        severity = Severity.INFO if flagged else Severity.WARNING
        code = "house_view_divergence_flagged" if flagged else "house_view_contradiction"
        return ValidationIssue(
            validator=self.name,
            severity=severity,
            code=code,
            message=v.get("explanation") or "Report diverges from house view.",
            location=v.get("quote"),
            context={
                "quote": v.get("quote"),
                "contradicts": v.get("contradicts"),
                "flagged": flagged,
            },
        )


def _extract_block(context: Context, name: str) -> dict:
    for block in context.blocks:
        if block.name == name:
            return block.content
    return {}
