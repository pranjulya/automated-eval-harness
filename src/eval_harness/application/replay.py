"""Replay scoring from stored normalized outcomes without target calls."""

from __future__ import annotations

import json

from ..adapters.artifacts.filesystem import FilesystemArtifactStore
from ..application.aggregate import aggregate, summary_hash
from ..application.run import load_outcomes
from ..domain.cases import Profile, parse_case
from ..domain.runs import CaseResult, RunOutcome, RunStatus, Summary
from ..errors import InfrastructureError
from ..evaluators import Evaluator, case_state, evaluate_case

__all__ = ["ReplayService"]


class ReplayService:
    def __init__(self, registry: dict[Profile, tuple[Evaluator, ...]]) -> None:
        self._registry = registry

    def replay(self, store: FilesystemArtifactStore, run_id: str) -> RunOutcome:
        store.read_bundle(run_id)
        bundle = store.run_dir(run_id)
        inputs = [
            parse_case(json.loads(line))
            for line in (bundle / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        outcomes = load_outcomes(bundle)
        stored_cases = {
            row["case_id"]: CaseResult.model_validate(row)
            for row in (
                json.loads(line)
                for line in (bundle / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        results: list[CaseResult] = []
        for sequence, case in enumerate(sorted(inputs, key=lambda item: item.case_id)):
            outcome = outcomes[case.case_id]
            findings = evaluate_case(case, outcome, self._registry)
            results.append(
                CaseResult(
                    run_id=run_id,
                    case_id=case.case_id,
                    primary_profile=case.primary_profile,
                    sequence=sequence,
                    state=case_state(case, outcome, findings),
                    findings=findings,
                    attempts=stored_cases[case.case_id].attempts,
                    latency_ms=stored_cases[case.case_id].latency_ms,
                    usage=outcome.usage,
                )
            )
        summary = aggregate(run_id, inputs, results)
        stored = Summary.model_validate_json((bundle / "summary.json").read_text(encoding="utf-8"))
        if summary_hash(summary) != summary_hash(stored):
            raise InfrastructureError(
                "replay produced a different summary", details={"run_id": run_id}
            )
        return RunOutcome(
            run_id=run_id,
            status=RunStatus.COMPLETED,
            exit_code=0,
            summary=summary,
            report_path=str(bundle / "report.md"),
            bundle_path=str(bundle),
            replay_of=run_id,
        )
