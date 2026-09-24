"""Registry dispatch and case-state precedence tests."""

from __future__ import annotations

from pathlib import Path

from eval_harness.datasets import load_suite
from eval_harness.domain.cases import parse_case
from eval_harness.domain.findings import CaseState, Severity
from eval_harness.domain.outcomes import NormalizedOutcome, OutcomeStatus
from eval_harness.evaluators import build_registry, case_state, evaluate_case


def _semantic_case() -> object:
    return parse_case(
        {
            "schema_version": "eval.case.v1",
            "case_id": "text-777",
            "title": "Semantic only",
            "primary_profile": "text_semantic",
            "tags": [],
            "weight": 1,
            "input": {"messages": [{"role": "user", "content": "q"}]},
            "expectation": {
                "outcome": "answered",
                "deterministic": {"kind": "text", "required_values": []},
                "semantic": {
                    "rubric_id": "relevance-v1",
                    "reference_answer": "a",
                    "dimensions": ["relevance"],
                },
            },
            "limits": {"timeout_ms": 1000, "max_output_bytes": 1024},
            "provenance": {
                "author": "a",
                "reviewers": ["r"],
                "source_classification": "synthetic",
                "rationale": "test",
            },
        }
    )


def test_registry_covers_all_profiles() -> None:
    registry = build_registry()
    assert len(registry) == 5


def test_evaluate_case_combines_invariants_and_profile(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="Canberra")
    findings = evaluate_case(case, outcome)
    assert all(finding.passed for finding in findings)


def test_case_state_error_when_outcome_unusable(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.TIMEOUT)
    assert case_state(case, outcome, ()) is CaseState.ERROR


def test_case_state_fail_on_deterministic_finding(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="wrong")
    findings = evaluate_case(case, outcome)
    assert any(finding.severity is Severity.DETERMINISTIC for finding in findings)
    assert case_state(case, outcome, findings) is CaseState.FAIL


def test_case_state_review_when_semantic_required_without_judge() -> None:
    case = _semantic_case()
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="a")
    findings = evaluate_case(case, outcome)
    assert case_state(case, outcome, findings) is CaseState.REVIEW_REQUIRED


def test_case_state_pass(golden_suite: Path) -> None:
    case = load_suite(golden_suite).by_id("text-001")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="Canberra")
    assert case_state(case, outcome, evaluate_case(case, outcome)) is CaseState.PASS


def test_hard_invariant_precedes_review_required() -> None:
    case = parse_case(
        {
            "schema_version": "eval.case.v1",
            "case_id": "safe-777",
            "title": "Hard invariant with semantic",
            "primary_profile": "safety_abstention",
            "tags": [],
            "weight": 1,
            "input": {"messages": [{"role": "user", "content": "q"}]},
            "expectation": {
                "outcome": "refused",
                "deterministic": {
                    "kind": "safety",
                    "required_outcome": "refused",
                    "canaries": ["CANARY-X"],
                },
                "semantic": {
                    "rubric_id": "faithfulness-v1",
                    "reference_answer": "a",
                    "dimensions": ["faithfulness"],
                },
            },
            "limits": {"timeout_ms": 1000, "max_output_bytes": 1024},
            "provenance": {
                "author": "a",
                "reviewers": ["r"],
                "source_classification": "synthetic",
                "rationale": "test",
            },
        }
    )
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="CANARY-X")
    findings = evaluate_case(case, outcome)
    assert case_state(case, outcome, findings) is CaseState.FAIL
