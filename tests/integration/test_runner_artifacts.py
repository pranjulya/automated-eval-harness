"""Runner artifact lifecycle: atomic publication, interruption, replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_harness.adapters.artifacts.filesystem import FilesystemArtifactStore
from eval_harness.adapters.targets import FakeTargetAdapter
from eval_harness.adapters.targets.base import AttemptResult, TargetConfig, TargetIdentity
from eval_harness.application.aggregate import summary_hash
from eval_harness.application.replay import ReplayService
from eval_harness.application.run import RunRequest
from eval_harness.domain.runs import RunStatus, Summary
from eval_harness.errors import InfrastructureError
from eval_harness.evaluators import build_registry
from eval_harness.evaluators.schema_store import load_schema_resolver

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_V1 = REPO_ROOT / "evaluation" / "datasets" / "golden-v1"
FAKE_RESPONSES = REPO_ROOT / "evaluation" / "fixtures" / "fake-target-v1.json"

REQUIRED_FILES = {
    "manifest.json",
    "inputs.jsonl",
    "attempts.jsonl",
    "cases.jsonl",
    "outcomes.jsonl",
    "summary.json",
    "report.md",
    "COMPLETE",
}


def test_run_publishes_complete_bundle(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    bundle = Path(outcome.bundle_path)
    assert {path.name for path in bundle.iterdir()} == REQUIRED_FILES
    store = FilesystemArtifactStore(Path(config.artifact_root))
    store.read_bundle(outcome.run_id)
    manifest = store.read_manifest(outcome.run_id)
    assert manifest.status is RunStatus.COMPLETED
    assert len(manifest.finished_case_ids) == 50
    assert outcome.summary.comparable is True


def test_existing_run_id_is_rejected(run_factory) -> None:
    service, config = run_factory()
    first = service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id="fixed-run"))
    assert first.run_id == "fixed-run"
    with pytest.raises(InfrastructureError):
        service.run(RunRequest(suite_path=GOLDEN_V1, config=config, run_id="fixed-run"))


def test_abandoned_staging_leaves_no_bundle(tmp_path: Path) -> None:
    store = FilesystemArtifactStore(tmp_path / "artifacts")
    writer = store.begin("partial")
    writer.write_json("manifest.json", {"partial": True})
    writer.abandon()
    assert not store.run_dir("partial").exists()
    assert store.list_runs() == []


class _FailingAdapter:
    @property
    def adapter_id(self) -> str:
        return "failing"

    def identity(self, config: TargetConfig) -> TargetIdentity:
        return TargetIdentity(
            adapter="failing",
            adapter_version="1.0.0",
            endpoint_id="failing://test",
            request_template_hash="sha256:x",
            model=config.model,
            deterministic=True,
            seed_supported=False,
            externally_nondeterministic=False,
        )

    def invoke(self, case, config: TargetConfig) -> AttemptResult:
        del case, config
        raise RuntimeError("boom")


def test_interrupted_run_publishes_nothing(run_factory, tmp_path: Path) -> None:
    service, config = run_factory(adapter=_FailingAdapter())
    store = FilesystemArtifactStore(Path(config.artifact_root))
    with pytest.raises(RuntimeError):
        service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    assert store.list_runs() == []


def test_corrupt_bundle_is_detected(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = FilesystemArtifactStore(Path(config.artifact_root))
    (store.run_dir(outcome.run_id) / "cases.jsonl").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(InfrastructureError):
        store.read_bundle(outcome.run_id)


def test_selector_limits_run(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config, case_ids=("text-001",)))
    assert outcome.summary.expected == 1
    assert outcome.summary.completed == 1
    assert outcome.summary.pass_rate == 1.0


def test_replay_reproduces_summary_hash(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    store = FilesystemArtifactStore(Path(config.artifact_root))
    stored = Summary.model_validate_json(
        (store.run_dir(outcome.run_id) / "summary.json").read_text(encoding="utf-8")
    )
    replayed = ReplayService(build_registry(load_schema_resolver(REPO_ROOT))).replay(
        store, outcome.run_id
    )
    assert summary_hash(replayed.summary) == summary_hash(stored)
    assert replayed.replay_of == outcome.run_id


def test_bundle_index_hash_is_self_consistent(run_factory) -> None:
    service, config = run_factory()
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config))
    bundle = Path(outcome.bundle_path)
    index = json.loads((bundle / "COMPLETE").read_text(encoding="utf-8"))
    assert index["files"]
    assert index["index_hash"]
    for name in index["files"]:
        assert (bundle / name).is_file()


def test_unusable_outcome_is_case_error(run_factory) -> None:
    responses = json.loads(FAKE_RESPONSES.read_text(encoding="utf-8"))
    responses["text-001"] = {"status": "timeout"}
    service, config = run_factory(adapter=FakeTargetAdapter(responses))
    outcome = service.run(RunRequest(suite_path=GOLDEN_V1, config=config, case_ids=("text-001",)))
    assert outcome.summary.state_counts["ERROR"] == 1
    assert outcome.summary.pass_rate == 0.0
