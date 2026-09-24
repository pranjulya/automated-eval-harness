"""Explicit evaluator registry.

The registry maps each primary profile to its ordered evaluators. Adding a
first-party profile means adding a discriminated expectation, an evaluator, and
an entry here; it never forks the runner or the gate engine.
"""

from __future__ import annotations

from ..domain.cases import EvalCase, Profile
from ..domain.findings import CaseState, Finding, derive_case_state
from ..domain.outcomes import NormalizedOutcome
from .base import Evaluator, SchemaResolver
from .invariants import InvariantEvaluator
from .rag import RagEvaluator
from .safety import SafetyEvaluator
from .structured import StructuredEvaluator
from .text import TextEvaluator
from .tools import ToolEvaluator

__all__ = [
    "INVARIANT_EVALUATORS",
    "Evaluator",
    "SchemaResolver",
    "build_registry",
    "case_state",
    "evaluate_case",
]

INVARIANT_EVALUATORS: tuple[Evaluator, ...] = (InvariantEvaluator(),)


def build_registry(
    resolver: SchemaResolver | None = None,
) -> dict[Profile, tuple[Evaluator, ...]]:
    return {
        Profile.TEXT_SEMANTIC: (TextEvaluator(),),
        Profile.SAFETY_ABSTENTION: (SafetyEvaluator(),),
        Profile.STRUCTURED_OUTPUT: (StructuredEvaluator(resolver),),
        Profile.RAG: (RagEvaluator(),),
        Profile.TOOL_USE: (ToolEvaluator(),),
    }


def evaluate_case(
    case: EvalCase,
    outcome: NormalizedOutcome,
    registry: dict[Profile, tuple[Evaluator, ...]] | None = None,
) -> tuple[Finding, ...]:
    active = registry if registry is not None else build_registry()
    findings: list[Finding] = []
    for evaluator in INVARIANT_EVALUATORS:
        findings.extend(evaluator.evaluate(case, outcome))
    for evaluator in active[case.primary_profile]:
        findings.extend(evaluator.evaluate(case, outcome))
    return tuple(findings)


def case_state(
    case: EvalCase, outcome: NormalizedOutcome, findings: tuple[Finding, ...]
) -> CaseState:
    semantic = case.expectation.semantic
    requires_semantic = semantic is not None and bool(semantic.dimensions)
    return derive_case_state(
        findings,
        outcome_usable=outcome.usable,
        required_semantic_available=not requires_semantic,
    )
