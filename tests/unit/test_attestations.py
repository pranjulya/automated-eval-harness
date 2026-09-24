"""Gate attestation build and verification tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eval_harness.domain.attestations import (
    build_attestation,
    compute_attestation_hash,
    verify_attestation,
)
from eval_harness.domain.gates import GateDecision

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _attestation(decision: GateDecision = GateDecision.PASS):
    return build_attestation(
        commit="abc123",
        run_id="run-1",
        run_manifest_hash="manifest-hash",
        baseline_hash="baseline-hash",
        workflow=".github/workflows/eval-release.yml",
        decision=decision,
        reason_codes=("REGRESSION_TOTAL_PASSED",),
        now=NOW,
    )


def test_attestation_hash_is_stable() -> None:
    attestation = _attestation()
    assert attestation.attestation_hash == compute_attestation_hash(attestation)


def test_valid_pass_attestation_verifies() -> None:
    result = verify_attestation(
        _attestation(),
        now=NOW,
        expected_commit="abc123",
        expected_run_manifest_hash="manifest-hash",
        expected_baseline_hash="baseline-hash",
    )
    assert result.ok is True
    assert result.failures == ()


def test_stale_commit_is_rejected() -> None:
    result = verify_attestation(_attestation(), now=NOW, expected_commit="different")
    assert result.ok is False
    assert "stale_commit" in result.failures


def test_wrong_run_manifest_is_rejected() -> None:
    result = verify_attestation(_attestation(), now=NOW, expected_run_manifest_hash="other")
    assert "wrong_run_manifest" in result.failures


def test_wrong_baseline_is_rejected() -> None:
    result = verify_attestation(_attestation(), now=NOW, expected_baseline_hash="other")
    assert "wrong_baseline" in result.failures


def test_non_pass_decision_is_rejected() -> None:
    result = verify_attestation(_attestation(GateDecision.BLOCK), now=NOW)
    assert result.ok is False
    assert "decision_not_pass" in result.failures


def test_expired_attestation_is_rejected_unless_allowed() -> None:
    expired = verify_attestation(_attestation(), now=NOW + timedelta(hours=48))
    assert "expired" in expired.failures
    allowed = verify_attestation(_attestation(), now=NOW + timedelta(hours=48), allow_expired=True)
    assert allowed.ok is True


def test_tampered_attestation_is_rejected() -> None:
    attestation = _attestation()
    tampered = attestation.model_copy(update={"run_id": "other-run"})
    result = verify_attestation(tampered, now=NOW)
    assert "hash_mismatch" in result.failures
