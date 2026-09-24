"""Tool-use deterministic evaluator tests."""

from __future__ import annotations

from pathlib import Path

from eval_harness.datasets import load_suite
from eval_harness.domain.findings import FailureCode
from eval_harness.domain.outcomes import NormalizedOutcome, OutcomeStatus, ToolCall
from eval_harness.evaluators.tools import ToolEvaluator

EVALUATOR = ToolEvaluator()


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings if not finding.passed}


def test_expected_call_with_subset_arguments(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-001")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        tool_calls=(
            ToolCall(name="search", arguments={"query": "cancellation policy", "top_k": 5}),
        ),
    )
    assert EVALUATOR.evaluate(case, outcome) == ()


def test_missing_expected_call(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK)
    assert FailureCode.TOOL_SELECTION_FAILED in _codes(EVALUATOR.evaluate(case, outcome))


def test_exact_argument_mismatch(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-002")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        tool_calls=(
            ToolCall(name="create_ticket", arguments={"title": "Refund", "priority": "high"}),
        ),
    )
    assert FailureCode.TOOL_ARGUMENT_FAILED in _codes(EVALUATOR.evaluate(case, outcome))


def test_repeated_call_detected(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-006")
    repeated = ToolCall(name="search", arguments={"query": "policy"})
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, tool_calls=(repeated, repeated))
    assert FailureCode.TOOL_LOOP in _codes(EVALUATOR.evaluate(case, outcome))


def test_max_steps_exceeded(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-005")
    calls = tuple(ToolCall(name="search", arguments={"query": f"q{i}"}) for i in range(3))
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, tool_calls=calls)
    assert FailureCode.TOOL_LOOP in _codes(EVALUATOR.evaluate(case, outcome))


def test_extra_call_after_termination(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-010")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK, tool_calls=(ToolCall(name="search", arguments={}),)
    )
    assert FailureCode.TOOL_SELECTION_FAILED in _codes(EVALUATOR.evaluate(case, outcome))


def test_recovery_sequence_passes(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("tool-007")
    outcome = NormalizedOutcome(
        status=OutcomeStatus.OK,
        tool_calls=(
            ToolCall(name="search", arguments={"query": "x"}, succeeded=False),
            ToolCall(name="create_ticket", arguments={"title": "t"}),
        ),
    )
    assert EVALUATOR.evaluate(case, outcome) == ()
