"""Evaluation runner: invoke, score, aggregate, and publish one bundle."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..adapters.artifacts.filesystem import FilesystemArtifactStore
from ..adapters.targets.base import TargetAdapter, TargetConfig
from ..application.aggregate import aggregate
from ..application.invocation import InvocationService, RetryPolicy
from ..application.judging import JudgeService, requires_semantic, score_dimensions
from ..datasets import load_suite
from ..datasets.hashing import canonical_json, sha256_hex
from ..domain.cases import EvalCase, Profile
from ..domain.findings import Finding, Severity
from ..domain.judging import CalibrationRecord, Rubric
from ..domain.outcomes import NormalizedOutcome
from ..domain.runs import (
    AttemptRecord,
    CaseResult,
    CodeIdentity,
    DatasetRef,
    RunManifest,
    RunOutcome,
    RunStatus,
)
from ..errors import HarnessError
from ..evaluators import Evaluator, case_state, evaluate_case
from ..reporting import render_report

__all__ = ["RunConfig", "RunRequest", "RunService"]


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: TargetConfig
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    concurrency: int = Field(default=5, ge=1, le=16)
    artifact_root: str = "artifacts"
    fake_responses: str | None = None


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suite_path: Path
    config: RunConfig
    case_ids: tuple[str, ...] = ()
    profile: Profile | None = None
    tag: str | None = None
    run_id: str | None = None


class RunService:
    def __init__(
        self,
        *,
        adapter: TargetAdapter,
        registry: dict[Profile, tuple[Evaluator, ...]],
        code: CodeIdentity,
        environment: str = "development",
        invocation: InvocationService | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        judge: JudgeService | None = None,
        judge_identity: dict[str, object] | None = None,
        rubrics: Mapping[str, Rubric] | None = None,
        calibrations: Mapping[str, CalibrationRecord] | None = None,
    ) -> None:
        self._adapter = adapter
        self._registry = registry
        self._code = code
        self._environment = environment
        self._invocation = invocation or InvocationService()
        self._now = now
        self._judge = judge
        self._judge_identity = judge_identity
        self._rubrics: Mapping[str, Rubric] = rubrics or {}
        self._calibrations: Mapping[str, CalibrationRecord] = calibrations or {}

    def run(self, request: RunRequest) -> RunOutcome:
        suite = load_suite(request.suite_path)
        cases = _select_cases(suite.cases, request)
        run_id = request.run_id or _new_run_id()
        store = FilesystemArtifactStore(Path(request.config.artifact_root))
        started = self._now().isoformat()
        manifest = RunManifest(
            run_id=run_id,
            status=RunStatus.RUNNING,
            started_at=started,
            command="run",
            dataset=DatasetRef(
                name=suite.identity.name,
                suite_version=suite.identity.suite_version,
                schema_version=suite.identity.schema_version,
                content_hash=suite.identity.content_hash,
                case_ids=tuple(case.case_id for case in cases),
            ),
            target=self._adapter.identity(request.config.target).model_dump(mode="json"),
            evaluator_version="evaluators.v1",
            retry_policy=request.config.retry.model_dump(mode="json"),
            concurrency=request.config.concurrency,
            code=self._code,
            environment=self._environment,
            requested_case_ids=tuple(case.case_id for case in cases),
            nondeterministic=request.config.target.externally_nondeterministic,
            judge=dict(self._judge_identity) if self._judge_identity else None,
        )
        writer = store.begin(run_id)
        try:
            writer.write_json("manifest.json", manifest.model_dump(mode="json"))
            writer.write_jsonl("inputs.jsonl", [case.model_dump(mode="json") for case in cases])
            results, attempt_rows, outcome_rows = self._process_all(cases, run_id, request)
            summary = aggregate(run_id, cases, results)
            writer.write_jsonl("attempts.jsonl", attempt_rows)
            writer.write_jsonl(
                "cases.jsonl", [result.model_dump(mode="json") for result in results]
            )
            writer.write_jsonl("outcomes.jsonl", outcome_rows)
            writer.write_json("summary.json", summary.model_dump(mode="json"))
            writer.write_text("report.md", render_report(manifest, summary, results))
            finished = manifest.model_copy(
                update={
                    "status": RunStatus.COMPLETED,
                    "finished_at": self._now().isoformat(),
                    "finished_case_ids": tuple(result.case_id for result in results),
                }
            )
            writer.write_json("manifest.json", finished.model_dump(mode="json"))
            writer.finalize(store.run_dir(run_id))
        except BaseException:
            writer.abandon()
            raise
        return RunOutcome(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            exit_code=0,
            summary=summary,
            report_path=str(store.run_dir(run_id) / "report.md"),
            bundle_path=str(store.run_dir(run_id)),
        )

    def _process_all(
        self, cases: list[EvalCase], run_id: str, request: RunRequest
    ) -> tuple[list[CaseResult], list[dict[str, object]], list[dict[str, object]]]:
        results: list[CaseResult] = []
        attempt_rows: list[dict[str, object]] = []
        outcome_rows: list[dict[str, object]] = []
        with ThreadPoolExecutor(max_workers=request.config.concurrency) as pool:
            futures = {
                pool.submit(self._process_one, case, run_id, request, sequence): sequence
                for sequence, case in enumerate(cases)
            }
            for future in as_completed(futures):
                result, attempts, outcome_row = future.result()
                results.append(result)
                attempt_rows.extend(attempts)
                outcome_rows.append(outcome_row)
        results.sort(key=lambda result: result.sequence)
        attempt_rows.sort(key=lambda row: (str(row["case_id"]), int(str(row["attempt_index"]))))
        outcome_rows.sort(key=lambda row: str(row["case_id"]))
        return results, attempt_rows, outcome_rows

    def _process_one(
        self,
        case: EvalCase,
        run_id: str,
        request: RunRequest,
        sequence: int,
    ) -> tuple[CaseResult, list[dict[str, object]], dict[str, object]]:
        record = self._invocation.invoke(
            case, self._adapter, request.config.target, request.config.retry
        )
        outcome = record.outcome
        findings = list(evaluate_case(case, outcome, self._registry))
        semantic_available: bool | None = None
        if (
            self._judge is not None
            and requires_semantic(case)
            and not _has_decisive_failure(findings)
        ):
            scored = score_dimensions(self._judge, case, outcome, self._rubrics, self._calibrations)
            findings.extend(scored.findings)
            semantic_available = scored.available
        state = case_state(case, outcome, tuple(findings), semantic_available=semantic_available)
        attempts = [
            AttemptRecord(
                run_id=run_id,
                case_id=case.case_id,
                attempt_index=attempt.attempt_index,
                state=attempt.state.value,
                request_hash=attempt.request_hash,
                response_hash=attempt.response_hash,
                http_status=attempt.http_status,
                error=attempt.error,
                elapsed_ms=attempt.elapsed_ms,
            )
            for attempt in record.attempts
        ]
        result = CaseResult(
            run_id=run_id,
            case_id=case.case_id,
            primary_profile=case.primary_profile,
            sequence=sequence,
            state=state,
            findings=tuple(findings),
            outcome_hash=sha256_hex(canonical_json(outcome.model_dump(mode="json"))),
            attempts=len(attempts),
            latency_ms=attempts[-1].elapsed_ms,
            usage=outcome.usage,
        )
        outcome_row: dict[str, object] = {
            "case_id": case.case_id,
            "outcome": outcome.model_dump(mode="json"),
        }
        return result, [record_row.model_dump(mode="json") for record_row in attempts], outcome_row


def _has_decisive_failure(findings: list[Finding]) -> bool:
    decisive = {Severity.HARD_INVARIANT, Severity.DETERMINISTIC}
    return any(finding.is_failure and finding.severity in decisive for finding in findings)


def _select_cases(cases: tuple[EvalCase, ...], request: RunRequest) -> list[EvalCase]:
    selected = list(cases)
    if request.case_ids:
        wanted = set(request.case_ids)
        selected = [case for case in selected if case.case_id in wanted]
    if request.profile is not None:
        selected = [case for case in selected if case.primary_profile is request.profile]
    if request.tag is not None:
        selected = [case for case in selected if request.tag in case.tags]
    if not selected:
        raise HarnessError("selector matched no cases", details={"command": "run"})
    return sorted(selected, key=lambda case: case.case_id)


def _new_run_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{uuid4().hex[:8]}"


def load_outcomes(bundle: Path) -> dict[str, NormalizedOutcome]:
    outcomes: dict[str, NormalizedOutcome] = {}
    for line in (bundle / "outcomes.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            outcomes[row["case_id"]] = NormalizedOutcome.model_validate(row["outcome"])
    return outcomes
