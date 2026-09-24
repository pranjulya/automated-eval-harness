"""End-to-end gate decisions against fake-target runs."""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.adapters.targets import FakeTargetAdapter
from eval_harness.application.compare import CompareService
from eval_harness.application.promote import PromotionService
from eval_harness.application.run import RunRequest
from eval_harness.domain.baselines import PromotionAuthorization
from eval_harness.domain.gates import GateDecision, GatePolicy

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
FAKE_RESPONSES = REPO_ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"

AUTHORIZATION = PromotionAuthorization(
    actor="quality-owner", approval_evidence=("github:review/1",), reason="baseline"
)


def _responses() -> dict:
    return json.loads(FAKE_RESPONSES.read_text(encoding="utf-8"))


def _run(service, config, run_id: str):
    return service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id=run_id))


def test_decision_pass_block_review(run_factory) -> None:
    # Baseline from a clean fake run.
    baseline_service, config = run_factory()
    baseline_run = _run(baseline_service, config, "baseline")
    store = FilesystemArtifactStore(Path(config.artifact_root))
    policy = GatePolicy()
    PromotionService(store).promote(
        baseline_run.run_id, "golden-v1", "stable", AUTHORIZATION, policy.policy_hash()
    )

    # PASS: an identical candidate.
    pass_service, pass_config = run_factory()
    pass_run = _run(pass_service, pass_config, "candidate-pass")
    passed = CompareService(store).compare(pass_run.run_id, "golden-v1", "stable", policy)
    assert passed.decision is GateDecision.PASS

    # BLOCK: a candidate that regresses text-001.
    blocked_responses = _responses()
    blocked_responses["text-001"] = {"status": "ok", "text": "Sydney"}
    block_service, block_config = run_factory(adapter=FakeTargetAdapter(blocked_responses))
    block_run = _run(block_service, block_config, "candidate-block")
    blocked = CompareService(store).compare(block_run.run_id, "golden-v1", "stable", policy)
    assert blocked.decision is GateDecision.BLOCK
    assert "text-001" in blocked.regressions

    # REVIEW_REQUIRED: semantic gating required but unavailable.
    review_service, review_config = run_factory()
    review_run = _run(review_service, review_config, "candidate-review")
    reviewed = CompareService(store).compare(
        review_run.run_id, "golden-v1", "stable", GatePolicy(require_semantic=True)
    )
    assert reviewed.decision is GateDecision.REVIEW_REQUIRED
