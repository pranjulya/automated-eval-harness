"""Immutable findings, stable failure codes, and case-state derivation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue

__all__ = [
    "CaseState",
    "FailureCode",
    "Finding",
    "Severity",
    "derive_case_state",
]


class Severity(StrEnum):
    HARD_INVARIANT = "hard_invariant"
    DETERMINISTIC = "deterministic"
    OPERATIONAL = "operational"
    SEMANTIC = "semantic"
    INFO = "info"


class FailureCode(StrEnum):
    """Stable failure taxonomy from the evaluation strategy §12."""

    DATASET_INVALID = "DATASET_INVALID"
    FIXTURE_MISSING = "FIXTURE_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    BASELINE_INCOMPATIBLE = "BASELINE_INCOMPATIBLE"
    INVOCATION_TIMEOUT = "INVOCATION_TIMEOUT"
    TARGET_RATE_LIMITED = "TARGET_RATE_LIMITED"
    TARGET_ERROR = "TARGET_ERROR"
    MALFORMED_OUTCOME = "MALFORMED_OUTCOME"
    TEXT_ASSERTION_FAILED = "TEXT_ASSERTION_FAILED"
    SAFETY_REFUSAL_FAILED = "SAFETY_REFUSAL_FAILED"
    SECRET_DISCLOSURE = "SECRET_DISCLOSURE"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    BUSINESS_ASSERTION_FAILED = "BUSINESS_ASSERTION_FAILED"
    RETRIEVAL_MISS = "RETRIEVAL_MISS"
    RANKING_REGRESSION = "RANKING_REGRESSION"
    CONTEXT_EVIDENCE_LOST = "CONTEXT_EVIDENCE_LOST"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    CITATION_INVALID = "CITATION_INVALID"
    CITATION_INCORRECT = "CITATION_INCORRECT"
    CITATION_INCOMPLETE = "CITATION_INCOMPLETE"
    NO_ANSWER_FALSE_POSITIVE = "NO_ANSWER_FALSE_POSITIVE"
    NO_ANSWER_FALSE_NEGATIVE = "NO_ANSWER_FALSE_NEGATIVE"
    TOOL_SELECTION_FAILED = "TOOL_SELECTION_FAILED"
    TOOL_ARGUMENT_FAILED = "TOOL_ARGUMENT_FAILED"
    TOOL_ORDER_FAILED = "TOOL_ORDER_FAILED"
    FORBIDDEN_TOOL_ATTEMPTED = "FORBIDDEN_TOOL_ATTEMPTED"
    TOOL_LOOP = "TOOL_LOOP"
    JUDGE_UNAVAILABLE = "JUDGE_UNAVAILABLE"
    JUDGE_INVALID = "JUDGE_INVALID"
    JUDGE_UNCALIBRATED = "JUDGE_UNCALIBRATED"
    LATENCY_REGRESSION = "LATENCY_REGRESSION"
    COST_REGRESSION = "COST_REGRESSION"
    ARTIFACT_INCOMPLETE = "ARTIFACT_INCOMPLETE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"


class CaseState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INVALID = "INVALID"
    ERROR = "ERROR"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluator_id: str
    code: str
    severity: Severity
    passed: bool
    score: float | None = None
    message: str = ""
    evidence: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def is_failure(self) -> bool:
        return not self.passed


def derive_case_state(
    findings: tuple[Finding, ...],
    *,
    outcome_usable: bool,
    required_semantic_available: bool | None = None,
) -> CaseState:
    """Derive the case state from findings using the locked precedence.

    1. No usable outcome -> ``ERROR``.
    2. Any failing hard invariant or deterministic finding -> ``FAIL``.
    3. Required semantic evidence unavailable -> ``REVIEW_REQUIRED``.
    4. Otherwise ``PASS``.

    ``INVALID`` is reserved for run-level dataset/config failure and is never
    produced here; a per-case invalid after a successful load is a defect.
    """

    if not outcome_usable:
        return CaseState.ERROR
    if any(finding.is_failure for finding in findings):
        return CaseState.FAIL
    if required_semantic_available is False:
        return CaseState.REVIEW_REQUIRED
    return CaseState.PASS
