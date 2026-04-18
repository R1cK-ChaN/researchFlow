"""Report generator: single LLM call over a built Context."""

from researchflow.generation.contracts import GeneratorParams, GenerationTrace, Report
from researchflow.generation.generator import generate

__all__ = ["GeneratorParams", "GenerationTrace", "Report", "generate"]
