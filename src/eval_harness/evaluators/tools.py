"""Tool-use deterministic evaluator."""

from __future__ import annotations

from itertools import pairwise

from pydantic import JsonValue

from ..domain.cases import EvalCase, ToolCallExpectation, ToolCase
from ..domain.findings import FailureCode, Finding, Severity
from ..domain.outcomes import NormalizedOutcome, ToolCall
from .base import Evaluator, make_finding

__all__ = ["ToolEvaluator"]

EVALUATOR_ID = "tools.v1"


class ToolEvaluator(Evaluator):
    @property
    def evaluator_id(self) -> str:
        return EVALUATOR_ID

    def evaluate(self, case: EvalCase, outcome: NormalizedOutcome) -> tuple[Finding, ...]:
        if not isinstance(case, ToolCase):
            return ()
        deterministic = case.expectation.deterministic
        actual = list(outcome.tool_calls)
        findings: list[Finding] = []

        if len(actual) > deterministic.max_steps:
            findings.append(
                make_finding(
                    EVALUATOR_ID,
                    FailureCode.TOOL_LOOP,
                    passed=False,
                    severity=Severity.DETERMINISTIC,
                    message="tool-call count exceeds the maximum steps",
                    evidence={"max_steps": deterministic.max_steps, "actual": len(actual)},
                )
            )

        for previous, current in pairwise(actual):
            if previous.name == current.name and previous.arguments == current.arguments:
                findings.append(
                    make_finding(
                        EVALUATOR_ID,
                        FailureCode.TOOL_LOOP,
                        passed=False,
                        severity=Severity.DETERMINISTIC,
                        message="repeated identical tool call detected",
                        evidence={"tool": current.name},
                    )
                )
                break

        findings.extend(_expected_calls(deterministic.expected_calls, actual))

        if deterministic.require_termination and not deterministic.expected_calls and actual:
            findings.append(
                make_finding(
                    EVALUATOR_ID,
                    FailureCode.TOOL_SELECTION_FAILED,
                    passed=False,
                    severity=Severity.DETERMINISTIC,
                    message="unexpected tool call after termination",
                )
            )
        return tuple(findings)


def _expected_calls(
    expected: tuple[ToolCallExpectation, ...], actual: list[ToolCall]
) -> list[Finding]:
    findings: list[Finding] = []
    cursor = 0
    for expectation in expected:
        found: int | None = None
        for index in range(cursor, len(actual)):
            if actual[index].name == expectation.name:
                found = index
                break
        if found is None:
            findings.append(
                make_finding(
                    EVALUATOR_ID,
                    FailureCode.TOOL_SELECTION_FAILED,
                    passed=False,
                    severity=Severity.DETERMINISTIC,
                    message="expected tool call not made",
                    evidence={"tool": expectation.name},
                )
            )
            continue
        cursor = found + 1
        if not _arguments_match(actual[found].arguments, expectation.arguments, expectation.exact):
            findings.append(
                make_finding(
                    EVALUATOR_ID,
                    FailureCode.TOOL_ARGUMENT_FAILED,
                    passed=False,
                    severity=Severity.DETERMINISTIC,
                    message="tool arguments did not match expectation",
                    evidence={"tool": expectation.name},
                )
            )
    return findings


def _arguments_match(
    actual: dict[str, JsonValue], expected: dict[str, JsonValue], exact: bool
) -> bool:
    if exact:
        return actual == expected
    return all(actual.get(key) == value for key, value in expected.items())
