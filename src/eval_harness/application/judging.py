"""Judge service: eligibility, bounded requests, and fail-closed scoring."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from ..adapters.judges.base import JudgeAdapter, JudgeConfig
from ..domain.cases import EvalCase
from ..domain.findings import FailureCode, Finding, Severity
from ..domain.judging import (
    CalibrationRecord,
    JudgeRequest,
    JudgeResult,
    Rubric,
    semantic_finding,
)
from ..domain.outcomes import NormalizedOutcome
from ..errors import JudgeInvalidError, JudgeUnavailableError

__all__ = ["JudgeService", "SemanticScore"]

MAX_EVIDENCE_HITS = 20


@dataclass(frozen=True, slots=True)
class SemanticScore:
    findings: tuple[Finding, ...]
    available: bool


def _info(code: FailureCode | str, message: str, case_id: str) -> Finding:
    return Finding(
        evaluator_id="judge.v1",
        code=str(code),
        severity=Severity.INFO,
        passed=False,
        message=message,
        evidence={"case_id": case_id},
    )


class JudgeService:
    def __init__(
        self,
        adapter: JudgeAdapter,
        config: JudgeConfig,
        *,
        redactor: Callable[[str], str] | None = None,
    ) -> None:
        self._adapter = adapter
        self._config = config
        self._redactor = redactor or (lambda value: value)

    def score(
        self,
        case: EvalCase,
        outcome: NormalizedOutcome,
        rubric: Rubric,
        calibration: CalibrationRecord | None,
    ) -> SemanticScore:
        if not self.is_eligible(rubric, calibration):
            return SemanticScore(
                (
                    _info(
                        FailureCode.JUDGE_UNCALIBRATED,
                        "rubric has no approved eligible calibration",
                        case.case_id,
                    ),
                ),
                available=False,
            )
        request = self._build_request(case, outcome, rubric)
        try:
            raw = self._adapter.judge(request, self._config)
        except JudgeUnavailableError as error:
            return SemanticScore(
                (_info(FailureCode.JUDGE_UNAVAILABLE, error.message, case.case_id),),
                available=False,
            )
        except JudgeInvalidError as error:
            return SemanticScore(
                (_info(FailureCode.JUDGE_INVALID, error.message, case.case_id),),
                available=False,
            )
        normalized = rubric.normalized_map[raw.ordinal]
        passed = normalized >= rubric.pass_cut
        result = JudgeResult(
            rubric_id=rubric.rubric_id,
            rubric_version=rubric.version,
            dimension=rubric.dimension,
            ordinal=raw.ordinal,
            normalized=normalized,
            passed=passed,
            evidence_ids=raw.evidence_ids,
            rationale=raw.rationale,
            provider=self._config.provider,
            model=self._config.model,
            prompt_hash=rubric.prompt_hash,
        )
        code = "SEMANTIC_PASS" if passed else "SEMANTIC_SCORE_BELOW_CUT"
        message = "semantic dimension passed" if passed else "semantic score below cut"
        return SemanticScore(
            (semantic_finding(result, passed, code, message),),
            available=True,
        )

    def is_eligible(self, rubric: Rubric, calibration: CalibrationRecord | None) -> bool:
        if calibration is None:
            return False
        return (
            calibration.status == "approved"
            and calibration.rubric_id == rubric.rubric_id
            and calibration.rubric_version == rubric.version
            and calibration.metrics.eligible
        )

    def _build_request(
        self, case: EvalCase, outcome: NormalizedOutcome, rubric: Rubric
    ) -> JudgeRequest:
        semantic = case.expectation.semantic
        candidate = self._redactor(outcome.text or "")
        encoded = candidate.encode("utf-8")[:32_768]
        return JudgeRequest(
            case_id=case.case_id,
            rubric_id=rubric.rubric_id,
            rubric_version=rubric.version,
            dimension=rubric.dimension,
            prompt_hash=rubric.prompt_hash,
            candidate_text=encoded.decode("utf-8", errors="ignore"),
            reference_answer=semantic.reference_answer if semantic else None,
            evidence=outcome.evidence[:MAX_EVIDENCE_HITS],
        )


def requires_semantic(case: EvalCase) -> bool:
    semantic = case.expectation.semantic
    return semantic is not None and bool(semantic.dimensions)


def semantic_dimensions(case: EvalCase) -> tuple[str, ...]:
    semantic = case.expectation.semantic
    return semantic.dimensions if semantic else ()


def score_dimensions(
    service: JudgeService,
    case: EvalCase,
    outcome: NormalizedOutcome,
    rubrics: Mapping[str, Rubric],
    calibrations: Mapping[str, CalibrationRecord],
) -> SemanticScore:
    """Score every requested dimension; all must be available to count as scored."""

    findings: list[Finding] = []
    available = True
    for dimension in semantic_dimensions(case):
        rubric = rubrics.get(dimension)
        if rubric is None:
            findings.append(
                _info(FailureCode.JUDGE_UNCALIBRATED, f"no rubric for {dimension}", case.case_id)
            )
            available = False
            continue
        score = service.score(case, outcome, rubric, calibrations.get(rubric.rubric_id))
        findings.extend(score.findings)
        available = available and score.available
    return SemanticScore(tuple(findings), available=available and bool(semantic_dimensions(case)))
