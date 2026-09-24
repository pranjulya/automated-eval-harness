"""Gate engine reason codes, boundaries, and decision precedence."""

from __future__ import annotations

from eval_harness.domain.cases import Profile
from eval_harness.domain.findings import CaseState, Finding, Severity
from eval_harness.domain.gates import (
    ComparisonRun,
    GateDecision,
    GatePolicy,
    ReasonCode,
    compare_runs,
)
from eval_harness.domain.runs import CaseResult, ProfileAggregate, Summary

PROFILES = {
    "text-001": Profile.TEXT_SEMANTIC,
    "text-002": Profile.TEXT_SEMANTIC,
    "text-003": Profile.TEXT_SEMANTIC,
    "text-004": Profile.TEXT_SEMANTIC,
    "text-005": Profile.TEXT_SEMANTIC,
    "safe-001": Profile.SAFETY_ABSTENTION,
    "safe-002": Profile.SAFETY_ABSTENTION,
    "struct-001": Profile.STRUCTURED_OUTPUT,
    "struct-002": Profile.STRUCTURED_OUTPUT,
    "rag-001": Profile.RAG,
}
CASE_IDS = sorted(PROFILES)


def make_run(
    run_id: str,
    failing: set[str] | None = None,
    *,
    findings: dict[str, tuple[Finding, ...]] | None = None,
    p95: float | None = 1000.0,
    cost: float | None = 1.0,
    suite_hash: str = "suite-a",
    evaluator_version: str = "evaluators.v1",
    schema_version: str = "eval.case.v1",
    manifest_hash: str = "manifest-a",
    semantic: dict[str, float] | None = None,
) -> ComparisonRun:
    failing = failing or set()
    findings = dict(findings or {})
    semantic = semantic or {}
    states = {
        case_id: (CaseState.FAIL if case_id in failing else CaseState.PASS) for case_id in CASE_IDS
    }
    cases: list[CaseResult] = []
    for sequence, case_id in enumerate(CASE_IDS):
        case_findings = list(findings.get(case_id, ()))
        if case_id in semantic:
            case_findings.append(
                Finding(
                    evaluator_id="judge:relevance-v1@1.0.0",
                    code="SEMANTIC_PASS",
                    severity=Severity.SEMANTIC,
                    passed=True,
                    score=semantic[case_id],
                )
            )
        cases.append(
            CaseResult(
                run_id=run_id,
                case_id=case_id,
                primary_profile=PROFILES[case_id],
                sequence=sequence,
                state=states[case_id],
                findings=tuple(case_findings),
                latency_ms=int(p95) if p95 is not None else None,
                attempts=1,
            )
        )
    counts = {state.value: 0 for state in CaseState}
    for state in states.values():
        counts[state.value] += 1
    passed = counts[CaseState.PASS.value]
    profiles: list[ProfileAggregate] = []
    for profile in sorted(set(PROFILES.values()), key=lambda item: item.value):
        ids = [case_id for case_id, value in PROFILES.items() if value is profile]
        profile_passed = sum(1 for case_id in ids if states[case_id] is CaseState.PASS)
        profiles.append(
            ProfileAggregate(
                profile=profile,
                expected=len(ids),
                completed=len(ids),
                passed=profile_passed,
                pass_rate=profile_passed / len(ids),
            )
        )
    summary = Summary(
        run_id=run_id,
        expected=len(CASE_IDS),
        completed=len(CASE_IDS),
        state_counts=counts,
        pass_rate=passed / len(CASE_IDS),
        profiles=tuple(profiles),
        comparable=True,
        p95_latency_ms=p95,
        total_cost_usd=cost,
    )
    return ComparisonRun(
        run_id=run_id,
        suite_name="golden-v1",
        suite_hash=suite_hash,
        schema_version=schema_version,
        evaluator_version=evaluator_version,
        manifest_hash=manifest_hash,
        summary=summary,
        cases=tuple(cases),
        target={"model": "fake"},
    )


def codes(comparison) -> set[str]:
    return {reason.code for reason in comparison.reasons}


def test_identical_runs_pass() -> None:
    baseline = make_run("base")
    candidate = make_run("cand")
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert comparison.decision is GateDecision.PASS
    assert comparison.reasons == ()


def test_overall_floor_boundary() -> None:
    baseline = make_run("base")
    # Exactly 9/10 = 0.90 is still acceptable (boundary).
    at_floor = make_run("at-floor", failing={"text-005"})
    assert ReasonCode.FLOOR_OVERALL.value not in codes(
        compare_runs(at_floor, baseline, GatePolicy())
    )
    # 8/10 = 0.80 is below the 0.90 floor.
    below = make_run("below", failing={"text-004", "text-005"})
    comparison = compare_runs(below, baseline, GatePolicy())
    assert ReasonCode.FLOOR_OVERALL.value in codes(comparison)
    assert comparison.decision is GateDecision.BLOCK


def test_safety_floor_blocks_any_safety_failure() -> None:
    baseline = make_run("base")
    candidate = make_run("cand", failing={"safe-001"})
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.FLOOR_SAFETY.value in codes(comparison)


def test_contract_floor_blocks_any_structured_failure() -> None:
    baseline = make_run("base")
    candidate = make_run("cand", failing={"struct-001"})
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.FLOOR_CONTRACT.value in codes(comparison)


def test_hard_invariant_code_is_reported() -> None:
    finding = Finding(
        evaluator_id="invariants.v1",
        code="HARD_INVARIANT_SECRET_DISCLOSURE",
        severity=Severity.HARD_INVARIANT,
        passed=False,
    )
    baseline = make_run("base")
    candidate = make_run("cand", failing={"safe-001"}, findings={"safe-001": (finding,)})
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert "HARD_INVARIANT_SECRET_DISCLOSURE" in codes(comparison)
    assert comparison.decision is GateDecision.BLOCK


def test_total_passed_regression() -> None:
    baseline = make_run("base")
    candidate = make_run("cand", failing={"text-005"})
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.REGRESSION_TOTAL_PASSED.value in codes(comparison)
    assert comparison.regressions == ("text-005",)


def test_incompatible_suite_is_not_comparable() -> None:
    baseline = make_run("base", suite_hash="suite-a")
    candidate = make_run("cand", suite_hash="suite-b")
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert comparison.comparable is False
    assert comparison.compatibility_failures == ("suite_hash",)
    assert ReasonCode.BASELINE_INCOMPATIBLE.value in codes(comparison)


def test_provenance_incomplete_blocks() -> None:
    baseline = make_run("base")
    candidate = make_run("cand", manifest_hash="")
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.PROVENANCE_INCOMPLETE.value in codes(comparison)


def test_latency_budget_review() -> None:
    baseline = make_run("base", p95=1000.0)
    candidate = make_run("cand", p95=2000.0)
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.BUDGET_LATENCY.value in codes(comparison)
    assert comparison.decision is GateDecision.REVIEW_REQUIRED
    assert comparison.latency_delta_pct == 1.0


def test_latency_unavailable_reviews() -> None:
    baseline = make_run("base")
    candidate = make_run("cand", p95=None)
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.BUDGET_LATENCY.value in codes(comparison)
    assert comparison.decision is GateDecision.REVIEW_REQUIRED


def test_cost_budget_review() -> None:
    baseline = make_run("base", cost=1.0)
    candidate = make_run("cand", cost=1.5)
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert ReasonCode.BUDGET_COST.value in codes(comparison)
    assert comparison.decision is GateDecision.REVIEW_REQUIRED


def test_block_takes_precedence_over_review() -> None:
    baseline = make_run("base", p95=1000.0, cost=1.0)
    candidate = make_run("cand", failing={"text-005"}, p95=2000.0, cost=1.5)
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert comparison.decision is GateDecision.BLOCK


def test_semantic_non_inferiority_blocks_on_decline() -> None:
    baseline_scores = dict.fromkeys(CASE_IDS, 0.9)
    candidate_scores = {
        "text-001": 0.6,
        "text-002": 0.55,
        "text-003": 0.6,
        "text-004": 0.5,
        "text-005": 0.65,
        "safe-001": 0.6,
        "safe-002": 0.55,
        "struct-001": 0.5,
        "struct-002": 0.6,
        "rag-001": 0.55,
    }
    baseline = make_run("base", semantic=baseline_scores)
    candidate = make_run("cand", semantic=candidate_scores)
    comparison = compare_runs(candidate, baseline, GatePolicy(require_semantic=True))
    assert comparison.semantic_bootstrap.available is True
    assert ReasonCode.SEMANTIC_LCB_FAIL.value in codes(comparison)
    assert comparison.decision is GateDecision.BLOCK


def test_semantic_flat_decline_blocks_and_flat_parity_passes() -> None:
    baseline = make_run("base", semantic=dict.fromkeys(CASE_IDS, 0.9))
    decline = make_run("decline", semantic=dict.fromkeys(CASE_IDS, 0.6))
    blocked = compare_runs(decline, baseline, GatePolicy(require_semantic=True))
    assert ReasonCode.SEMANTIC_LCB_FAIL.value in codes(blocked)
    flat = make_run("flat", semantic=dict.fromkeys(CASE_IDS, 0.9))
    passed = compare_runs(flat, baseline, GatePolicy(require_semantic=True))
    assert passed.decision is GateDecision.PASS


def test_semantic_insufficient_sample_reviews() -> None:
    baseline = make_run("base", semantic={"text-001": 0.9})
    candidate = make_run("cand", semantic={"text-001": 0.9})
    comparison = compare_runs(candidate, baseline, GatePolicy(require_semantic=True))
    assert ReasonCode.SEMANTIC_SAMPLE_INSUFFICIENT.value in codes(comparison)
    assert comparison.decision is GateDecision.REVIEW_REQUIRED


def test_changed_variables_are_reported() -> None:
    baseline = make_run("base")
    candidate = make_run("cand")
    candidate = candidate.model_copy(update={"target": {"model": "new-model"}})
    comparison = compare_runs(candidate, baseline, GatePolicy())
    assert comparison.changed_variables == ("model",)
