"""Judge service eligibility, fail-closed behavior, and redaction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_harness.adapters.judges import FakeJudgeAdapter, JudgeConfig, RawJudgeResponse
from eval_harness.application.judging import JudgeService, score_dimensions
from eval_harness.application.run import _has_decisive_failure
from eval_harness.domain.cases import parse_case
from eval_harness.domain.findings import FailureCode, Severity
from eval_harness.domain.judging import (
    CalibrationLabel,
    CalibrationRecord,
    Rubric,
    SemanticDimension,
    evaluate_calibration,
)
from eval_harness.domain.outcomes import NormalizedOutcome, OutcomeStatus
from eval_harness.evaluators import case_state

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "judging" / "calibration.json").read_text(
        encoding="utf-8"
    )
)
RUBRIC = Rubric.model_validate_json(
    (REPO_ROOT / "evaluation" / "rubrics" / "relevance-v1.json").read_text(encoding="utf-8")
)
CONFIG = JudgeConfig(provider="fake", model="judge-v1")


def _semantic_case(case_id: str = "text-777"):
    return parse_case(
        {
            "schema_version": "eval.case.v1",
            "case_id": case_id,
            "title": "Semantic",
            "primary_profile": "text_semantic",
            "tags": [],
            "weight": 1,
            "input": {"messages": [{"role": "user", "content": "q"}]},
            "expectation": {
                "outcome": "answered",
                "deterministic": {"kind": "text", "required_values": []},
                "semantic": {
                    "rubric_id": "relevance-v1",
                    "reference_answer": "a",
                    "dimensions": ["relevance"],
                },
            },
            "limits": {"timeout_ms": 1000, "max_output_bytes": 1024},
            "provenance": {
                "author": "a",
                "reviewers": ["r"],
                "source_classification": "synthetic",
                "rationale": "test",
            },
        }
    )


def _approved_calibration() -> CalibrationRecord:
    case_ids = [f"c-{index:02d}" for index in range(len(FIXTURE["human"]))]
    labels = tuple(
        CalibrationLabel(case_id=cid, dimension=SemanticDimension.RELEVANCE, human_ordinal=value)
        for cid, value in zip(case_ids, FIXTURE["human"], strict=True)
    )
    judge_ordinals = dict(zip(case_ids, FIXTURE["judge"], strict=True))
    repeats = {cid: tuple(values) for cid, values in zip(case_ids, FIXTURE["repeats"], strict=True)}
    slices = dict(zip(case_ids, FIXTURE["slices"], strict=True))
    metrics = evaluate_calibration(RUBRIC, labels, judge_ordinals, repeats, slices)
    assert metrics.eligible
    return CalibrationRecord(
        rubric_id="relevance-v1",
        rubric_version="1.0.0",
        status="approved",
        labels=labels,
        judge_ordinals=judge_ordinals,
        repeat_ordinals=repeats,
        slices=slices,
        metrics=metrics,
        reviewer_evidence=("github:review/123",),
        created="2026-09-10",
        labels_hash="sha256:test",
    )


def _service(responses: dict[str, dict]) -> JudgeService:
    return JudgeService(FakeJudgeAdapter(responses), CONFIG)


def test_calibrated_pass_is_available() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="good answer")
    service = _service({"relevance-v1|text-777": {"ordinal": 5}})
    score = service.score(case, outcome, RUBRIC, _approved_calibration())
    assert score.available is True
    assert score.findings[0].passed is True
    assert score.findings[0].score == 1.0


def test_calibrated_failure_is_semantic_fail() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="bad answer")
    service = _service({"relevance-v1|text-777": {"ordinal": 2}})
    score = service.score(case, outcome, RUBRIC, _approved_calibration())
    assert score.available is True
    assert score.findings[0].severity is Severity.SEMANTIC
    assert score.findings[0].is_failure is True


def test_draft_calibration_is_uncalibrated_review() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    calibration = _approved_calibration()
    draft = calibration.model_copy(update={"status": "draft", "reviewer_evidence": ()})
    service = _service({"relevance-v1|text-777": {"ordinal": 5}})
    score = service.score(case, outcome, RUBRIC, draft)
    assert score.available is False
    assert score.findings[0].code == str(FailureCode.JUDGE_UNCALIBRATED)
    assert score.findings[0].severity is Severity.INFO
    assert not _has_decisive_failure(list(score.findings))


def test_missing_calibration_is_uncalibrated() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    score = _service({}).score(case, outcome, RUBRIC, None)
    assert score.available is False
    assert score.findings[0].code == str(FailureCode.JUDGE_UNCALIBRATED)


def test_judge_outage_is_review_not_fail() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    score = _service({}).score(case, outcome, RUBRIC, _approved_calibration())
    assert score.available is False
    assert score.findings[0].code == str(FailureCode.JUDGE_UNAVAILABLE)
    assert not _has_decisive_failure(list(score.findings))


def test_judge_malformed_is_review() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    score = _service({"relevance-v1|text-777": {"ordinal": 9}}).score(
        case, outcome, RUBRIC, _approved_calibration()
    )
    assert score.available is False
    assert score.findings[0].code == str(FailureCode.JUDGE_INVALID)


def test_redaction_applied_before_judging() -> None:
    captured: dict[str, str] = {}

    class CapturingJudge:
        @property
        def adapter_id(self) -> str:
            return "capturing"

        def judge(self, request, config):
            captured["candidate"] = request.candidate_text
            return RawJudgeResponse(ordinal=5)

    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="token SECRET123 leaked")
    service = JudgeService(
        CapturingJudge(), CONFIG, redactor=lambda value: value.replace("SECRET123", "[REDACTED]")
    )
    service.score(case, outcome, RUBRIC, _approved_calibration())
    assert "SECRET123" not in captured["candidate"]
    assert "[REDACTED]" in captured["candidate"]


def test_scored_dimension_drives_review_when_unavailable() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    scored = score_dimensions(_service({}), case, outcome, {"relevance": RUBRIC}, {})
    assert scored.available is False
    assert (
        case_state(case, outcome, scored.findings, semantic_available=scored.available).value
        == "REVIEW_REQUIRED"
    )


def test_scored_dimension_passes_when_calibrated() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    calibration = _approved_calibration()
    scored = score_dimensions(
        _service({"relevance-v1|text-777": {"ordinal": 5}}),
        case,
        outcome,
        {"relevance": RUBRIC},
        {RUBRIC.rubric_id: calibration},
    )
    assert scored.available is True
    assert case_state(case, outcome, scored.findings, semantic_available=True).value == "PASS"


def test_missing_rubric_is_unavailable() -> None:
    case = _semantic_case("text-777")
    outcome = NormalizedOutcome(status=OutcomeStatus.OK, text="answer")
    scored = score_dimensions(_service({}), case, outcome, {}, {})
    assert scored.available is False
    assert scored.findings[0].code == str(FailureCode.JUDGE_UNCALIBRATED)


@pytest.mark.parametrize("severity", [Severity.HARD_INVARIANT, Severity.DETERMINISTIC])
def test_decisive_failure_skips_judging(severity: Severity) -> None:
    from eval_harness.domain.findings import Finding

    finding = Finding(evaluator_id="x", code="X", severity=severity, passed=False)
    assert _has_decisive_failure([finding]) is True
    info = Finding(evaluator_id="x", code="JUDGE_UNAVAILABLE", severity=Severity.INFO, passed=False)
    assert _has_decisive_failure([info]) is False
