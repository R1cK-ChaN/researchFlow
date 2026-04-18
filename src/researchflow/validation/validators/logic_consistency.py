"""LLM judge: does the report's directional claims respect the framework sign_map?"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from researchflow.context.contracts import Context
from researchflow.generation.contracts import Report
from researchflow.validation.contracts import Severity, ValidationIssue
from researchflow.validation.judge import DEFAULT_JUDGE_MODEL, PARSE_ERROR_SENTINEL, run_judge
from researchflow.validation.validators.base import register_validator

SYSTEM_PROMPT = """\
You are an economics compliance reviewer checking a sell-side research report
for directional consistency with the firm's reaction-function rules.

Input format:
- <report>: the draft report text.
- <sign_map>: a list of rules. Each rule has a trigger condition and expected
  (asset, sign) pairs.
- <derived_metrics>: the surprise / delta values that determine which rule
  applies.

Your task: identify statements in the report that assert market moves in the
OPPOSITE direction of what the applicable sign_map rule specifies, WITHOUT
explicit justification.

Do not flag:
- Statements consistent with the sign_map.
- Non-directional statements (level commentary, caveats, long-horizon calls).
- Statements where the report explicitly justifies the deviation.

Output format: a single JSON object with key "violations", value is a list.
Each violation is an object with keys:
- "quote": the exact verbatim substring from the report.
- "violates": description of the rule violated.
- "expected_direction": what the sign_map says.
- "claimed_direction": what the report says.
- "explanation": one short sentence.

If no violations, return {"violations": []}.
Output ONLY the JSON object. No preamble, no fences, no trailing text.
"""


@register_validator
class LogicConsistencyValidator:
    name: ClassVar[str] = "logic_consistency"
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

        sign_map = _extract_block(context, "framework").get("sign_map", [])
        if not sign_map:
            return []
        derived = _extract_block(context, "derived_metrics")

        user_content = (
            f"<report>\n{report.raw_text}\n</report>\n\n"
            f"<sign_map>\n{json.dumps(sign_map, indent=2, ensure_ascii=False)}\n</sign_map>\n\n"
            f"<derived_metrics>\n{json.dumps(derived, indent=2, ensure_ascii=False)}\n</derived_metrics>"
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
        return ValidationIssue(
            validator=self.name,
            severity=Severity.WARNING,
            code="sign_map_violation",
            message=v.get("explanation") or "Directional claim contradicts sign_map.",
            location=v.get("quote"),
            context={
                "quote": v.get("quote"),
                "violates": v.get("violates"),
                "expected_direction": v.get("expected_direction"),
                "claimed_direction": v.get("claimed_direction"),
            },
        )


def _extract_block(context: Context, name: str) -> dict:
    for block in context.blocks:
        if block.name == name:
            return block.content
    return {}
