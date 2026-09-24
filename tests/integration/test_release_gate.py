"""Release gate: evaluation evidence binds a commit and non-pass stops deploy."""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.adapters.targets import FakeTargetAdapter
from eval_harness.application.compare import CompareService
from eval_harness.application.promote import PromotionService
from eval_harness.application.run import RunRequest
from eval_harness.datasets.hashing import hash_file
from eval_harness.domain.attestations import build_attestation, verify_attestation
from eval_harness.domain.baselines import PromotionAuthorization
from eval_harness.domain.gates import GatePolicy

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
FAKE_RESPONSES = REPO_ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"
AUTHORIZATION = PromotionAuthorization(
    actor="quality-owner", approval_evidence=("github:review/1",), reason="baseline"
)
WORKFLOW = ".github/workflows/eval-release.yml"


def test_pass_and_block_attestations(run_factory) -> None:
    service, config = run_factory()
    service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id="baseline"))
    store = FilesystemArtifactStore(Path(config.artifact_root))
    policy = GatePolicy()
    record = PromotionService(store).promote(
        "baseline", "golden-v1", "stable", AUTHORIZATION, policy.policy_hash()
    )

    # PASS path: identical candidate, attestation verifies.
    pass_comparison = CompareService(store).compare("baseline", "golden-v1", "stable", policy)
    pass_manifest_hash = hash_file(store.run_dir("baseline") / "manifest.json")
    pass_attestation = build_attestation(
        commit="sha-1",
        run_id="baseline",
        run_manifest_hash=pass_manifest_hash,
        baseline_hash=record.record_hash,
        workflow=WORKFLOW,
        decision=pass_comparison.decision,
    )
    verification = verify_attestation(
        pass_attestation,
        expected_commit="sha-1",
        expected_run_manifest_hash=pass_manifest_hash,
        expected_baseline_hash=record.record_hash,
    )
    assert verification.ok is True

    # BLOCK path: regression candidate, attestation cannot authorize deploy.
    responses = json.loads(FAKE_RESPONSES.read_text(encoding="utf-8"))
    responses["text-001"] = {"status": "ok", "text": "Sydney"}
    block_service, block_config = run_factory(adapter=FakeTargetAdapter(responses))
    block_service.run(RunRequest(suite_path=GOLDEN_V1, config=block_config, run_id="blocked"))
    block_comparison = CompareService(store).compare("blocked", "golden-v1", "stable", policy)
    assert block_comparison.decision.value == "BLOCK"
    block_attestation = build_attestation(
        commit="sha-2",
        run_id="blocked",
        run_manifest_hash=hash_file(store.run_dir("blocked") / "manifest.json"),
        baseline_hash=record.record_hash,
        workflow=WORKFLOW,
        decision=block_comparison.decision,
    )
    block_verification = verify_attestation(block_attestation)
    assert block_verification.ok is False
    assert "decision_not_pass" in block_verification.failures
