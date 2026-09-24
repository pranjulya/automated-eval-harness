"""Calibration math tests against hand-calculated fixtures."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from eval_harness.domain.judging import (
    CalibrationLabel,
    Rubric,
    SemanticDimension,
    evaluate_calibration,
    exact_pass_agreement,
    repeat_agreement,
    slice_gaps,
    weighted_cohens_kappa,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "judging" / "calibration.json").read_text(
        encoding="utf-8"
    )
)
RUBRIC = Rubric.model_validate_json(
    (REPO_ROOT / "evaluation" / "rubrics" / "relevance-v1.json").read_text(encoding="utf-8")
)


def _close(actual: float | None, expected: float) -> bool:
    return actual is not None and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-9)


def test_fixture_rubric_id_matches() -> None:
    assert RUBRIC.rubric_id == FIXTURE["rubric_id"]
    assert RUBRIC.dimension is SemanticDimension.RELEVANCE


def test_weighted_kappa_matches_hand_calculation() -> None:
    assert _close(
        weighted_cohens_kappa(FIXTURE["human"], FIXTURE["judge"]),
        FIXTURE["expected"]["weighted_kappa"],
    )


def test_exact_agreement_matches_hand_calculation() -> None:
    passed = [value >= 4 for value in FIXTURE["human"]]
    judged = [value >= 4 for value in FIXTURE["judge"]]
    assert _close(exact_pass_agreement(passed, judged), FIXTURE["expected"]["exact_pass_agreement"])


def test_repeat_agreement_matches_hand_calculation() -> None:
    assert _close(repeat_agreement(FIXTURE["repeats"]), FIXTURE["expected"]["repeat_agreement"])


def test_full_calibration_is_eligible() -> None:
    case_ids = [f"c-{index:02d}" for index in range(len(FIXTURE["human"]))]
    labels = tuple(
        CalibrationLabel(case_id=cid, dimension=SemanticDimension.RELEVANCE, human_ordinal=value)
        for cid, value in zip(case_ids, FIXTURE["human"], strict=True)
    )
    judge_ordinals = dict(zip(case_ids, FIXTURE["judge"], strict=True))
    repeats = dict(zip(case_ids, FIXTURE["repeats"], strict=True))
    slices = dict(zip(case_ids, FIXTURE["slices"], strict=True))
    metrics = evaluate_calibration(RUBRIC, labels, judge_ordinals, repeats, slices)
    assert metrics.label_count == FIXTURE["expected"]["label_count"]
    assert metrics.pass_count == FIXTURE["expected"]["pass_count"]
    assert metrics.fail_count == FIXTURE["expected"]["fail_count"]
    assert metrics.eligible is True
    assert metrics.failures == ()
    assert max(metrics.slice_gaps.values()) == pytest.approx(
        FIXTURE["expected"]["max_slice_gap"], abs=1e-9
    )


def test_insufficient_labels_are_ineligible() -> None:
    labels = tuple(
        CalibrationLabel(case_id=f"c-{i}", dimension=SemanticDimension.RELEVANCE, human_ordinal=5)
        for i in range(5)
    )
    metrics = evaluate_calibration(RUBRIC, labels, {f"c-{i}": 5 for i in range(5)})
    assert metrics.eligible is False
    assert "insufficient_labels" in metrics.failures
    assert "labels_lack_both_outcomes" in metrics.failures


def test_low_kappa_is_ineligible() -> None:
    human = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    judge = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    case_ids = [f"c-{i}" for i in range(20)]
    labels = tuple(
        CalibrationLabel(case_id=cid, dimension=SemanticDimension.RELEVANCE, human_ordinal=value)
        for cid, value in zip(case_ids, human, strict=True)
    )
    metrics = evaluate_calibration(
        RUBRIC,
        labels,
        dict(zip(case_ids, judge, strict=True)),
        dict.fromkeys(case_ids, (5, 5, 5)),
    )
    assert metrics.eligible is False
    assert "kappa_below_threshold" in metrics.failures
    assert "exact_agreement_below_threshold" in metrics.failures


def test_kappa_unavailable_when_expected_agreement_is_one() -> None:
    assert weighted_cohens_kappa([3, 3, 3], [3, 3, 3]) is None
    assert exact_pass_agreement([], []) is None
    assert repeat_agreement([]) is None


def test_slice_gap_flags_biased_slice() -> None:
    human = [True] * 10 + [True] * 10
    judge = [True] * 10 + [False] * 10
    gaps = slice_gaps(human, judge, ["a"] * 10 + ["b"] * 10)
    assert gaps["a"] == 0.0
    assert gaps["b"] == pytest.approx(0.5)
