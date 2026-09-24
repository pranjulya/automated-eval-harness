"""Waiver acceptance/rejection and its effect on a comparison."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eval_harness.domain.gates import Comparison, GateDecision, GateReason
from eval_harness.domain.statistics import BootstrapResult
from eval_harness.domain.waivers import (
    Waiver,
    apply_waivers,
    compute_waiver_hash,
    validate_waiver,
)

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _bootstrap() -> BootstrapResult:
    return BootstrapResult(available=False)


def _reason(code: str, decision: GateDecision) -> GateReason:
    return GateReason(code=code, decision=decision, message=code)


def _comparison(reasons: tuple[GateReason, ...], decision: GateDecision) -> Comparison:
    return Comparison(
        candidate_run_id="candidate",
        baseline_run_id="baseline",
        suite_name="golden-v1",
        channel="stable",
        comparable=True,
        decision=decision,
        reasons=reasons,
        semantic_bootstrap=_bootstrap(),
    )


def _waiver(**overrides: object) -> Waiver:
    payload: dict[str, object] = {
        "waiver_id": "w-1",
        "owner": "team-eval",
        "approver": "reviewer",
        "approval_evidence": ("github:review/1",),
        "suite": "golden-v1",
        "channel": "stable",
        "scope_reasons": ("BUDGET_LATENCY",),
        "scope_cases": (),
        "compensating_control": "monitor latency for 7 days",
        "created": NOW.isoformat(),
        "expires_at": (NOW + timedelta(days=7)).isoformat(),
    }
    payload.update(overrides)
    waiver = Waiver.model_validate(payload)
    return waiver.model_copy(update={"waiver_hash": compute_waiver_hash(waiver)})


def _budget_comparison() -> Comparison:
    return _comparison(
        (_reason("BUDGET_LATENCY", GateDecision.REVIEW_REQUIRED),), GateDecision.REVIEW_REQUIRED
    )


def test_valid_budget_waiver_is_accepted_and_clears_review() -> None:
    comparison = _budget_comparison()
    decision = validate_waiver(_waiver(), comparison, NOW)
    assert decision.accepted is True
    assert decision.suppressed_reasons == ("BUDGET_LATENCY",)
    updated, _ = apply_waivers(comparison, (_waiver(),), NOW)
    assert updated.decision is GateDecision.PASS
    assert updated.accepted_waivers == ("w-1",)


def test_expired_waiver_is_rejected() -> None:
    decision = validate_waiver(_waiver(), _budget_comparison(), NOW + timedelta(days=8))
    assert decision.accepted is False
    assert "expired" in decision.failures


def test_expiry_longer_than_fourteen_days_is_rejected() -> None:
    decision = validate_waiver(
        _waiver(expires_at=(NOW + timedelta(days=20)).isoformat()),
        _budget_comparison(),
        NOW,
    )
    assert "expiry_too_long" in decision.failures


def test_missing_github_approval_is_rejected() -> None:
    decision = validate_waiver(_waiver(approval_evidence=()), _budget_comparison(), NOW)
    assert "missing_github_approval" in decision.failures


def test_wildcard_scope_is_overbroad() -> None:
    decision = validate_waiver(_waiver(scope_reasons=("*",)), _budget_comparison(), NOW)
    assert "overbroad" in decision.failures


def test_hard_invariant_cannot_be_waived() -> None:
    comparison = _comparison(
        (_reason("REGRESSION_DETERMINISTIC_CASE", GateDecision.BLOCK),), GateDecision.BLOCK
    )
    decision = validate_waiver(
        _waiver(scope_reasons=("REGRESSION_DETERMINISTIC_CASE",)), comparison, NOW
    )
    assert "hard_invariant_not_waivable" in decision.failures
    updated, _ = apply_waivers(
        comparison, (_waiver(scope_reasons=("REGRESSION_DETERMINISTIC_CASE",)),), NOW
    )
    assert updated.decision is GateDecision.BLOCK


def test_scope_reason_not_present_is_rejected() -> None:
    decision = validate_waiver(_waiver(scope_reasons=("BUDGET_COST",)), _budget_comparison(), NOW)
    assert "scope_not_present" in decision.failures


def test_suite_or_channel_mismatch_is_rejected() -> None:
    decision = validate_waiver(_waiver(channel="other"), _budget_comparison(), NOW)
    assert "scope_mismatch" in decision.failures


def test_tampered_waiver_hash_is_rejected() -> None:
    waiver = _waiver().model_copy(update={"waiver_hash": "deadbeef"})
    decision = validate_waiver(waiver, _budget_comparison(), NOW)
    assert "integrity_mismatch" in decision.failures


def test_case_scope_must_exist() -> None:
    decision = validate_waiver(_waiver(scope_cases=("text-999",)), _budget_comparison(), NOW)
    assert "case_scope_not_present" in decision.failures
