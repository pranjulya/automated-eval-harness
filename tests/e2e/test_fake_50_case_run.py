"""End-to-end 50-case fake-target run and replay."""

from __future__ import annotations

from pathlib import Path

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.application.replay import ReplayService
from eval_harness.application.run import RunRequest
from eval_harness.evaluators import build_registry
from eval_harness.evaluators.schema_store import load_schema_resolver

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"


def test_full_fake_suite_run(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    summary = outcome.summary
    assert summary.expected == 50
    assert summary.completed == 50
    assert summary.pass_rate == 1.0
    assert summary.invariant_failures == 0
    assert summary.comparable is True
    counts = {profile.profile.value: profile.expected for profile in summary.profiles}
    assert counts == {
        "text_semantic": 12,
        "safety_abstention": 6,
        "structured_output": 10,
        "rag": 12,
        "tool_use": 10,
    }


def test_full_run_replay_is_byte_equivalent(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = FilesystemArtifactStore(Path(config.artifact_root))
    replayed = ReplayService(build_registry(load_schema_resolver(REPO_ROOT))).replay(
        store, outcome.run_id
    )
    assert replayed.summary.completed == 50
    assert replayed.summary.pass_rate == 1.0


def test_report_written_for_full_run(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    report = Path(outcome.report_path).read_text(encoding="utf-8")
    assert "# Evaluation run" in report
    assert "text-001" in report
    assert "50" in report
