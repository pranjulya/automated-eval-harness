"""Text/safety deterministic evaluator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_harness.datasets import load_suite
from eval_harness.domain.findings import FailureCode
from eval_harness.domain.outcomes import NormalizedOutcome, OutcomeStatus
from eval_harness.evaluators.safety import SafetyEvaluator
from eval_harness.evaluators.text import TextEvaluator

TEXT = TextEvaluator()
SAFETY = SafetyEvaluator()


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings if not finding.passed}


def test_required_value_present(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="The capital is Canberra.")
    assert TEXT.evaluate(case, outcome) == ()


def test_required_value_missing(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="The capital is Sydney.")
    assert FailureCode.TEXT_ASSERTION_FAILED in _codes(TEXT.evaluate(case, outcome))


def test_unicode_and_whitespace_are_normalized(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-002")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="  CAFE\u0301  ")
    assert TEXT.evaluate(case, outcome) == ()


def test_forbidden_value_present(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-005")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="Earth has a moon.")
    assert FailureCode.TEXT_ASSERTION_FAILED in _codes(TEXT.evaluate(case, outcome))


@pytest.mark.parametrize(
    ("text", "fails"),
    [("order-4821", False), ("order-12", True), ("no id here", True)],
)
def test_trusted_regex(golden_suite: Path, text: str, fails: bool) -> None:
    case = load_suite(golden_suite).by_id("text-009")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text=text)
    assert (FailureCode.TEXT_ASSERTION_FAILED in _codes(TEXT.evaluate(case, outcome))) is fails


def test_safety_required_outcome_from_structured(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("safe-001")
    ok = NormalizedOutcome(status=OutcomeStatus.OK, structured={"outcome": "insufficient_evidence"})
    bad = NormalizedOutcome(status=OutcomeStatus.OK, structured={"outcome": "answered"})
    assert SAFETY.evaluate(case, ok) == ()
    assert FailureCode.SAFETY_REFUSAL_FAILED in _codes(SAFETY.evaluate(case, bad))


def test_refusal_marker_inference(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("safe-004")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="I cannot help with that request.")
    assert SAFETY.evaluate(case, outcome) == ()


def test_forbidden_disclosure_pattern(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("safe-002")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="The internal-key rotates weekly.")
    assert FailureCode.SAFETY_REFUSAL_FAILED in _codes(SAFETY.evaluate(case, outcome))
