"""Structural checks on the CI and release workflows."""

from __future__ import annotations

from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_ci_runs_the_full_test_suite() -> None:
    text = _text("ci.yml")
    assert "uv run pytest tests " in text
    assert "uv run ruff check ." in text
    assert "uv run mypy src/eval_harness" in text


def test_release_deploy_depends_on_gate_pass() -> None:
    text = _text("eval-release.yml")
    assert "needs: gate" in text
    assert "if: needs.gate.outputs.decision == 'PASS'" in text
    assert "decision: ${{ steps.decide.outputs.decision }}" in text
    assert "verify-attestation" in text


def test_release_uploads_evidence_on_every_outcome() -> None:
    text = _text("eval-release.yml")
    assert "if: always()" in text
    assert "actions/upload-artifact@v4" in text


def test_release_fails_closed_without_a_baseline() -> None:
    text = _text("eval-release.yml")
    assert "BASELINE_UNTRUSTED" in text


def test_promotion_uses_a_separate_protected_environment() -> None:
    text = _text("promote-baseline.yml")
    assert "environment: baseline-promotion" in text
    assert "promote-baseline" in text
    assert ".github/workflows/eval-release.yml" not in text
