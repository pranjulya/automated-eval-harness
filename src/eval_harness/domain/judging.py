"""Semantic judging contracts and calibration math.

Judges are narrow, versioned, and advisory until a frozen calibration slice
meets the locked agreement thresholds. All functions here are pure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .findings import FailureCode, Finding, Severity
from .outcomes import EvidenceHit, Usage

__all__ = [
    "DEFAULT_PASS_CUT",
    "MAX_SLICE_GAP",
    "MIN_EXACT_AGREEMENT",
    "MIN_KAPPA",
    "MIN_LABELS",
    "MIN_REPEAT_AGREEMENT",
    "NORMALIZED_MAP",
    "CalibrationLabel",
    "CalibrationMetrics",
    "CalibrationRecord",
    "JudgeRequest",
    "JudgeResult",
    "Rubric",
    "RubricAnchor",
    "SemanticDimension",
    "evaluate_calibration",
    "exact_pass_agreement",
    "repeat_agreement",
    "semantic_finding",
    "slice_gaps",
    "weighted_cohens_kappa",
]

NORMALIZED_MAP: dict[int, float] = {1: 0.0, 2: 0.25, 3: 0.50, 4: 0.75, 5: 1.0}
DEFAULT_PASS_CUT = 0.75

MIN_LABELS = 20
MIN_KAPPA = 0.70
MIN_EXACT_AGREEMENT = 0.80
MIN_REPEAT_AGREEMENT = 0.85
MAX_SLICE_GAP = 0.10


class SemanticDimension(StrEnum):
    RELEVANCE = "relevance"
    FAITHFULNESS = "faithfulness"
    COMPLETENESS = "completeness"
    CITATION_SUPPORT = "citation_support"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RubricAnchor(_Model):
    score: int = Field(ge=1, le=5)
    description: str = Field(min_length=1)


class Rubric(_Model):
    rubric_id: str
    version: str
    dimension: SemanticDimension
    anchors: tuple[RubricAnchor, ...]
    normalized_map: dict[int, float] = Field(default_factory=lambda: dict(NORMALIZED_MAP))
    pass_cut: float = DEFAULT_PASS_CUT
    prompt_hash: str
    instructions: str

    @model_validator(mode="after")
    def _anchors_cover_scale(self) -> Rubric:
        if sorted(anchor.score for anchor in self.anchors) != [1, 2, 3, 4, 5]:
            raise ValueError("rubric must define anchors 1..5")
        if set(self.normalized_map) != {1, 2, 3, 4, 5}:
            raise ValueError("normalized_map must cover scores 1..5")
        return self


class JudgeRequest(_Model):
    case_id: str
    rubric_id: str
    rubric_version: str
    dimension: SemanticDimension
    prompt_hash: str
    candidate_text: str
    reference_answer: str | None = None
    evidence: tuple[EvidenceHit, ...] = ()
    max_bytes: int = Field(default=32_768, gt=0)


class JudgeResult(_Model):
    rubric_id: str
    rubric_version: str
    dimension: SemanticDimension
    ordinal: int = Field(ge=1, le=5)
    normalized: float = Field(ge=0.0, le=1.0)
    passed: bool
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""
    provider: str
    model: str
    prompt_hash: str
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int | None = Field(default=None, ge=0)
    attempt_index: int = Field(default=1, ge=1)


class CalibrationLabel(_Model):
    case_id: str
    dimension: SemanticDimension
    human_ordinal: int = Field(ge=1, le=5)


class CalibrationMetrics(_Model):
    label_count: int
    pass_count: int
    fail_count: int
    weighted_kappa: float | None = None
    exact_pass_agreement: float | None = None
    repeat_agreement: float | None = None
    slice_gaps: dict[str, float] = Field(default_factory=dict)
    eligible: bool = False
    failures: tuple[str, ...] = ()


class CalibrationRecord(_Model):
    rubric_id: str
    rubric_version: str
    status: Literal["draft", "approved", "rejected"]
    labels: tuple[CalibrationLabel, ...] = ()
    judge_ordinals: dict[str, int] = Field(default_factory=dict)
    repeat_ordinals: dict[str, tuple[int, ...]] = Field(default_factory=dict)
    slices: dict[str, str] = Field(default_factory=dict)
    metrics: CalibrationMetrics
    reviewer_evidence: tuple[str, ...] = ()
    created: str
    labels_hash: str

    @field_validator("reviewer_evidence")
    @classmethod
    def _approved_requires_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return value

    @model_validator(mode="after")
    def _approved_needs_reviewers(self) -> CalibrationRecord:
        if self.status == "approved" and not self.reviewer_evidence:
            raise ValueError("approved calibration requires reviewer evidence")
        return self


def weighted_cohens_kappa(
    human: Sequence[int], judge: Sequence[int], categories: Sequence[int] = (1, 2, 3, 4, 5)
) -> float | None:
    """Linear-weighted Cohen's kappa on an ordinal scale. ``None`` if undefined."""

    n = len(human)
    if n == 0 or n != len(judge):
        return None
    low, high = min(categories), max(categories)
    span = high - low
    if span == 0:
        return None

    def weight(a: int, b: int) -> float:
        return 1.0 - abs(a - b) / span

    observed = sum(weight(h, j) for h, j in zip(human, judge, strict=True)) / n
    rows = dict.fromkeys(categories, 0)
    cols = dict.fromkeys(categories, 0)
    for h, j in zip(human, judge, strict=True):
        rows[h] += 1
        cols[j] += 1
    expected = sum(weight(a, b) * rows[a] * cols[b] for a in categories for b in categories) / (
        n * n
    )
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def exact_pass_agreement(
    human_passed: Sequence[bool], judge_passed: Sequence[bool]
) -> float | None:
    if not human_passed or len(human_passed) != len(judge_passed):
        return None
    return sum(h == j for h, j in zip(human_passed, judge_passed, strict=True)) / len(human_passed)


def repeat_agreement(repeats: Sequence[Sequence[int]]) -> float | None:
    """Fraction of judged items whose repeats all agree exactly."""

    if not repeats:
        return None
    agreeing = sum(1 for item in repeats if len(set(item)) == 1)
    return agreeing / len(repeats)


def slice_gaps(
    human_passed: Sequence[bool],
    judge_passed: Sequence[bool],
    slices: Sequence[str],
) -> dict[str, float]:
    """Per-slice shortfall of pass/fail agreement versus overall agreement."""

    overall = exact_pass_agreement(human_passed, judge_passed)
    if overall is None:
        return {}
    grouped: dict[str, list[tuple[bool, bool]]] = {}
    for human, judge, name in zip(human_passed, judge_passed, slices, strict=True):
        grouped.setdefault(name, []).append((human, judge))
    gaps: dict[str, float] = {}
    for name, pairs in grouped.items():
        agreement = sum(h == j for h, j in pairs) / len(pairs)
        gaps[name] = max(0.0, overall - agreement)
    return gaps


def evaluate_calibration(
    rubric: Rubric,
    labels: Sequence[CalibrationLabel],
    judge_ordinals: Mapping[str, int],
    repeat_ordinals: Mapping[str, Sequence[int]] | None = None,
    slices: Mapping[str, str] | None = None,
) -> CalibrationMetrics:
    """Compute agreement metrics and the eligibility decision for one rubric."""

    human = [label.human_ordinal for label in labels]
    judge = [judge_ordinals[label.case_id] for label in labels if label.case_id in judge_ordinals]
    paired_labels = [label for label in labels if label.case_id in judge_ordinals]
    human_passed = [
        rubric.normalized_map[label.human_ordinal] >= rubric.pass_cut for label in paired_labels
    ]
    judge_passed = [
        rubric.normalized_map[judge_ordinals[label.case_id]] >= rubric.pass_cut
        for label in paired_labels
    ]

    kappa = weighted_cohens_kappa(human, judge)
    exact = exact_pass_agreement(human_passed, judge_passed)
    repeats = list(repeat_ordinals.values()) if repeat_ordinals else []
    repeat = repeat_agreement(repeats)
    gap_map: dict[str, float] = {}
    if slices:
        gap_map = slice_gaps(
            human_passed,
            judge_passed,
            [slices[label.case_id] for label in paired_labels],
        )
    max_gap = max(gap_map.values(), default=0.0)

    failures: list[str] = []
    pass_count = sum(
        1 for label in labels if rubric.normalized_map[label.human_ordinal] >= rubric.pass_cut
    )
    fail_count = len(labels) - pass_count
    if len(labels) < MIN_LABELS:
        failures.append("insufficient_labels")
    if pass_count == 0 or fail_count == 0:
        failures.append("labels_lack_both_outcomes")
    if kappa is None or kappa < MIN_KAPPA:
        failures.append("kappa_below_threshold")
    if exact is None or exact < MIN_EXACT_AGREEMENT:
        failures.append("exact_agreement_below_threshold")
    if repeat is None or repeat < MIN_REPEAT_AGREEMENT:
        failures.append("repeat_agreement_below_threshold")
    if max_gap > MAX_SLICE_GAP:
        failures.append("slice_gap_above_threshold")

    return CalibrationMetrics(
        label_count=len(labels),
        pass_count=pass_count,
        fail_count=fail_count,
        weighted_kappa=kappa,
        exact_pass_agreement=exact,
        repeat_agreement=repeat,
        slice_gaps=gap_map,
        eligible=not failures,
        failures=tuple(failures),
    )


def semantic_finding(
    result: JudgeResult,
    passed: bool,
    code: FailureCode | str,
    message: str,
) -> Finding:
    return Finding(
        evaluator_id=f"judge:{result.rubric_id}@{result.rubric_version}",
        code=str(code),
        severity=Severity.SEMANTIC,
        passed=passed,
        score=result.normalized,
        message=message,
        evidence={
            "dimension": result.dimension.value,
            "ordinal": result.ordinal,
            "provider": result.provider,
            "model": result.model,
            "prompt_hash": result.prompt_hash,
        },
    )
