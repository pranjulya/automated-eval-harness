"""Deterministic aggregation of case results into a run summary."""

from __future__ import annotations

from collections.abc import Sequence

from ..datasets.hashing import canonical_json, sha256_hex
from ..domain.cases import EvalCase, Profile
from ..domain.findings import CaseState, Finding, Severity
from ..domain.metrics import p95
from ..domain.runs import CaseResult, ProfileAggregate, Summary

__all__ = ["aggregate", "summary_hash"]


def aggregate(
    run_id: str, expected_cases: Sequence[EvalCase], results: Sequence[CaseResult]
) -> Summary:
    expected = len(expected_cases)
    completed = len(results)
    state_counts: dict[str, int] = {state.value: 0 for state in CaseState}
    for result in results:
        state_counts[result.state.value] += 1

    passed = state_counts[CaseState.PASS.value]
    profiles: list[ProfileAggregate] = []
    for profile in Profile:
        expected_profile = sum(1 for case in expected_cases if case.primary_profile is profile)
        if expected_profile == 0:
            continue
        profile_results = [result for result in results if result.primary_profile is profile]
        profile_passed = sum(1 for result in profile_results if result.state is CaseState.PASS)
        profiles.append(
            ProfileAggregate(
                profile=profile,
                expected=expected_profile,
                completed=len(profile_results),
                passed=profile_passed,
                pass_rate=(profile_passed / expected_profile) if expected_profile else None,
            )
        )

    invariant_failures = sum(1 for result in results if _has_invariant_failure(result.findings))
    latencies = [result.latency_ms for result in results if result.latency_ms is not None]
    costs = [
        result.usage.estimated_cost_usd
        for result in results
        if result.usage.estimated_cost_usd is not None
    ]
    comparable = completed == expected and state_counts[CaseState.INVALID.value] == 0

    return Summary(
        run_id=run_id,
        expected=expected,
        completed=completed,
        state_counts=state_counts,
        pass_rate=(passed / expected) if expected else None,
        profiles=tuple(profiles),
        invariant_failures=invariant_failures,
        semantic_reviews=state_counts[CaseState.REVIEW_REQUIRED.value],
        p95_latency_ms=p95(latencies),
        total_cost_usd=(sum(costs) if costs else None),
        comparable=comparable,
    )


def _has_invariant_failure(findings: tuple[Finding, ...]) -> bool:
    return any(
        finding.is_failure and finding.severity is Severity.HARD_INVARIANT for finding in findings
    )


def summary_hash(summary: Summary) -> str:
    payload = summary.model_dump(mode="json")
    return sha256_hex(canonical_json(payload))
