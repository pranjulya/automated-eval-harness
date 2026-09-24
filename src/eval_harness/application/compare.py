"""Application service that compares a candidate run to a trusted baseline."""

from __future__ import annotations

import json
from pathlib import Path

from ..adapters.artifacts.filesystem import FilesystemArtifactStore
from ..datasets.hashing import hash_file
from ..domain.gates import Comparison, ComparisonRun, GatePolicy, compare_runs
from ..domain.runs import CaseResult, Summary

__all__ = ["CompareService", "load_comparison_run"]


def load_comparison_run(store: FilesystemArtifactStore, run_id: str) -> ComparisonRun:
    store.read_bundle(run_id)
    bundle = store.run_dir(run_id)
    manifest = store.read_manifest(run_id)
    summary = Summary.model_validate_json((bundle / "summary.json").read_text(encoding="utf-8"))
    cases = tuple(
        CaseResult.model_validate(json.loads(line))
        for line in (bundle / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    return ComparisonRun(
        run_id=run_id,
        suite_name=manifest.dataset.name,
        suite_hash=manifest.dataset.content_hash,
        schema_version=manifest.dataset.schema_version,
        evaluator_version=manifest.evaluator_version,
        manifest_hash=hash_file(bundle / "manifest.json"),
        summary=summary,
        cases=cases,
        target=manifest.target,
    )


class CompareService:
    def __init__(self, store: FilesystemArtifactStore) -> None:
        self._store = store

    def compare(
        self,
        candidate_run_id: str,
        suite_name: str,
        channel: str,
        policy: GatePolicy,
    ) -> Comparison:
        candidate = load_comparison_run(self._store, candidate_run_id)
        record = self._store.read_baseline(suite_name, channel)
        baseline = load_comparison_run(self._store, record.run_id)
        return compare_runs(candidate, baseline, policy)


def load_policy(path: Path) -> GatePolicy:
    return GatePolicy.model_validate_json(path.read_text(encoding="utf-8"))
