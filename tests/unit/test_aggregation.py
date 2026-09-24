"""Aggregation fixtures and summary-hash determinism."""

from __future__ import annotations

from pathlib import Path

from eval_harness.application.aggregate import aggregate, summary_hash
from eval_harness.datasets import load_suite
from eval_harness.domain.findings import CaseState, Finding, Severity
from eval_harness.domain.runs import CaseResult


def _case_ids(suite_path: Path, count: int) -> list[str]:
    return [case.case_id for case in load_suite(suite_path).cases[:count]]


def _result(case, sequence: int, state: CaseState, findings=()) -> CaseResult:
    return CaseResult(
        run_id="run-1",
        case_id=case.case_id,
        primary_profile=case.primary_profile,
        sequence=sequence,
        state=state,
        findings=findings,
        latency_ms=100 * (sequence + 1),
        attempts=1,
    )


def test_aggregate_counts_and_pass_rate(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    cases = [suite.by_id("text-001"), suite.by_id("text-002"), suite.by_id("rag-001")]
    fail = Finding(
        evaluator_id="text.v1",
        code="TEXT_ASSERTION_FAILED",
        severity=Severity.DETERMINISTIC,
        passed=False,
    )
    results = [
        _result(cases[0], 0, CaseState.PASS),
        _result(cases[1], 1, CaseState.FAIL, (fail,)),
        _result(cases[2], 2, CaseState.PASS),
    ]
    summary = aggregate("run-1", cases, results)
    assert summary.expected == 3
    assert summary.completed == 3
    assert summary.pass_rate == 2 / 3
    assert summary.state_counts[CaseState.PASS.value] == 2
    assert summary.state_counts[CaseState.FAIL.value] == 1
    assert summary.comparable is True


def test_aggregate_counts_hard_invariant_failures(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    case = suite.by_id("safe-005")
    invariant = Finding(
        evaluator_id="invariants.v1",
        code="HARD_INVARIANT_SECRET_DISCLOSURE",
        severity=Severity.HARD_INVARIANT,
        passed=False,
    )
    summary = aggregate("run-1", [case], [_result(case, 0, CaseState.FAIL, (invariant,))])
    assert summary.invariant_failures == 1
    assert summary.pass_rate == 0.0


def test_aggregate_p95_latency_uses_case_latencies(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    cases = [suite.by_id("text-001"), suite.by_id("text-002")]
    results = [_result(cases[0], 0, CaseState.PASS), _result(cases[1], 1, CaseState.PASS)]
    summary = aggregate("run-1", cases, results)
    assert summary.p95_latency_ms == 200.0


def test_aggregate_incomplete_is_not_comparable(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    cases = [suite.by_id("text-001"), suite.by_id("text-002")]
    summary = aggregate("run-1", cases, [_result(cases[0], 0, CaseState.PASS)])
    assert summary.completed == 1
    assert summary.comparable is False


def test_summary_hash_is_deterministic(golden_suite: Path) -> None:
    suite = load_suite(golden_suite)
    cases = _case_ids(golden_suite, 3)
    results = [_result(suite.by_id(case_id), i, CaseState.PASS) for i, case_id in enumerate(cases)]
    first = aggregate("run-1", [suite.by_id(c) for c in cases], results)
    second = aggregate("run-1", [suite.by_id(c) for c in cases], results)
    assert summary_hash(first) == summary_hash(second)
