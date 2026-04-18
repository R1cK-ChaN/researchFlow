"""XML renderer. Claude responds best to XML-tagged structured context."""

from __future__ import annotations

from html import escape
from typing import Any

from researchflow.context.contracts import RenderedBlock


def to_xml(blocks: list[RenderedBlock]) -> str:
    parts = ["<context>"]
    for b in blocks:
        parts.append(_render_dict(b.name, b.content, indent=1))
    parts.append("</context>")
    return "\n".join(parts)


def _render_dict(tag: str, value: Any, indent: int) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        if not value:
            return f"{pad}<{tag}/>"
        inner = "\n".join(_render_dict(k, v, indent + 1) for k, v in value.items())
        return f"{pad}<{tag}>\n{inner}\n{pad}</{tag}>"
    if isinstance(value, list):
        if not value:
            return f"{pad}<{tag}/>"
        child_tag = _singularize(tag)
        inner = "\n".join(_render_dict(child_tag, v, indent + 1) for v in value)
        return f"{pad}<{tag}>\n{inner}\n{pad}</{tag}>"
    return f"{pad}<{tag}>{escape(str(value))}</{tag}>"


def _singularize(tag: str) -> str:
    # Naive: facts → fact, metrics → metric, exemplars → exemplar.
    # Non-plural tags fall back to "item".
    if tag.endswith("ies"):
        return tag[:-3] + "y"
    if tag.endswith("s") and not tag.endswith("ss"):
        return tag[:-1]
    return "item"
