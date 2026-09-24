"""Baseline promotion and candidate comparison integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.adapters.targets import FakeTargetAdapter
from eval_harness.application.compare import CompareService
from eval_harness.application.promote import PromotionService
from eval_harness.application.run import RunRequest
from eval_harness.domain.baselines import PromotionAuthorization
from eval_harness.domain.gates import GateDecision, GatePolicy
from eval_harness.errors import HarnessError

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
FAKE_RESPONSES = REPO_ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"

AUTHORIZATION = PromotionAuthorization(
    actor="quality-owner",
    approval_evidence=("github:review/1",),
    reason="initial reviewed baseline",
)


def _store(config) -> FilesystemArtifactStore:
    return FilesystemArtifactStore(Path(config.artifact_root))


def _promote(run_factory, failing_case: str | None = None):
    responses = json.loads(FAKE_RESPONSES.read_text(encoding="utf-8"))
    if failing_case == "text-001":
        responses["text-001"] = {"status": "ok", "text": "Sydney"}
    adapter = FakeTargetAdapter(responses)
    service, config = run_factory(adapter=adapter)
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = _store(config)
    policy = GatePolicy()
    record = PromotionService(store).promote(
        outcome.run_id, "golden-v1", "stable", AUTHORIZATION, policy.policy_hash()
    )
    return outcome, record, store, policy


def test_promotion_writes_pointer_and_history(run_factory) -> None:
    outcome, record, store, _policy = _promote(run_factory)
    assert record.run_id == outcome.run_id
    assert record.superseded is None
    assert record.record_hash
    assert store.baseline_exists("golden-v1", "stable")
    history = store.baselines / "golden-v1" / "history" / "stable"
    assert (history / f"{record.record_hash}.json").is_file()
    assert store.list_baseline_channels("golden-v1") == ["stable"]


def test_second_promotion_links_predecessor(run_factory) -> None:
    _outcome, first, store, policy = _promote(run_factory)
    outcome, config = run_factory()
    second_run = outcome.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    second = PromotionService(store).promote(
        second_run.run_id, "golden-v1", "stable", AUTHORIZATION, policy.policy_hash()
    )
    assert second.superseded == first.record_hash
    # The first record stays immutable on disk.
    history = store.baselines / "golden-v1" / "history" / "stable"
    stored = json.loads((history / f"{first.record_hash}.json").read_text(encoding="utf-8"))
    assert stored["record_hash"] == first.record_hash


def test_promotion_rejects_suite_mismatch(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = _store(config)
    with pytest.raises(HarnessError, match="suite"):
        PromotionService(store).promote(
            outcome.run_id, "other-suite", "stable", AUTHORIZATION, GatePolicy().policy_hash()
        )


def test_comparison_passes_for_identical_run(run_factory) -> None:
    _outcome, _record, store, policy = _promote(run_factory)
    service, config = run_factory()
    candidate = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    comparison = CompareService(store).compare(candidate.run_id, "golden-v1", "stable", policy)
    assert comparison.comparable is True
    assert comparison.decision is GateDecision.PASS


def test_comparison_blocks_a_regression(run_factory) -> None:
    _outcome, _record, store, policy = _promote(run_factory)
    responses = json.loads(FAKE_RESPONSES.read_text(encoding="utf-8"))
    responses["text-001"] = {"status": "ok", "text": "Sydney"}
    service, config = run_factory(adapter=FakeTargetAdapter(responses))
    candidate = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    comparison = CompareService(store).compare(candidate.run_id, "golden-v1", "stable", policy)
    assert comparison.decision is GateDecision.BLOCK
    assert "text-001" in comparison.regressions


def test_missing_baseline_channel_errors(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = _store(config)
    with pytest.raises(HarnessError, match="baseline channel"):
        CompareService(store).compare(outcome.run_id, "golden-v1", "absent", GatePolicy())


def test_review_required_when_semantic_gating_is_required(run_factory) -> None:
    _outcome, _record, store, _policy = _promote(run_factory)
    service, config = run_factory()
    candidate = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    policy = GatePolicy(require_semantic=True)
    comparison = CompareService(store).compare(candidate.run_id, "golden-v1", "stable", policy)
    assert comparison.decision is GateDecision.REVIEW_REQUIRED
