"""Explicit, authorized baseline promotion with an immutable predecessor link."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from ..adapters.artifacts.filesystem import FilesystemArtifactStore
from ..datasets.hashing import hash_file
from ..domain.baselines import BaselineRecord, PromotionAuthorization, baseline_record_hash
from ..domain.runs import Summary
from ..errors import HarnessError

__all__ = ["PromotionService"]


class PromotionService:
    def __init__(
        self,
        store: FilesystemArtifactStore,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._store = store
        self._now = now

    def promote(
        self,
        run_id: str,
        suite_name: str,
        channel: str,
        authorization: PromotionAuthorization,
        policy_hash: str,
    ) -> BaselineRecord:
        self._store.read_bundle(run_id)  # verify bundle integrity before promoting
        manifest = self._store.read_manifest(run_id)
        bundle = self._store.run_dir(run_id)
        summary = Summary.model_validate_json((bundle / "summary.json").read_text(encoding="utf-8"))
        if not summary.comparable or summary.completed != summary.expected:
            raise HarnessError(
                "only a complete comparable run can become a baseline",
                details={
                    "run_id": run_id,
                    "completed": summary.completed,
                    "expected": summary.expected,
                },
            )
        if manifest.dataset.name != suite_name:
            raise HarnessError(
                "run suite does not match the requested baseline suite",
                details={"run_suite": manifest.dataset.name, "requested": suite_name},
            )

        predecessor: str | None = None
        if self._store.baseline_exists(suite_name, channel):
            predecessor = self._store.read_baseline(suite_name, channel).record_hash

        record = BaselineRecord(
            suite_name=suite_name,
            channel=channel,
            run_id=run_id,
            suite_hash=manifest.dataset.content_hash,
            schema_version_of_suite=manifest.dataset.schema_version,
            evaluator_version=manifest.evaluator_version,
            gate_policy_hash=policy_hash,
            run_manifest_hash=hash_file(bundle / "manifest.json"),
            approver=authorization.actor,
            approval_evidence=authorization.approval_evidence,
            reason=authorization.reason,
            created=self._now().isoformat(),
            superseded=predecessor,
        )
        record = record.model_copy(update={"record_hash": baseline_record_hash(record)})
        self._store.write_baseline(record)
        return record
