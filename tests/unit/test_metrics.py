"""Hand-calculated metric fixtures and boundary/metamorphic checks."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from eval_harness.domain.metrics import (
    Confusion,
    context_evidence_recall,
    dedupe_earliest,
    f1,
    mrr,
    ndcg_at_k,
    p95,
    pass_rate,
    percentile,
    precision,
    precision_at_k,
    recall,
    recall_at_k,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "metrics"
RANKING = json.loads((FIXTURES / "ranking_cases.json").read_text(encoding="utf-8"))
HAND = json.loads((FIXTURES / "hand_calculated.json").read_text(encoding="utf-8"))


def _close(actual: float | None, expected: float | None) -> bool:
    if actual is None or expected is None:
        return actual is expected
    return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)


@pytest.mark.parametrize("case", RANKING, ids=[case["name"] for case in RANKING])
def test_ranking_metrics_match_hand_calculation(case: dict) -> None:
    retrieved = case["retrieved"]
    relevant = case["relevant"]
    grades = case["grades"]
    k = case["k"]
    assert _close(recall_at_k(retrieved, relevant, k), case["recall_at_k"])
    assert _close(precision_at_k(retrieved, relevant, k), case["precision_at_k"])
    assert _close(mrr(retrieved, relevant), case["mrr"])
    assert _close(ndcg_at_k(retrieved, grades, k), case["ndcg_at_k"])


@pytest.mark.parametrize("case", HAND["pass_rate"], ids=["0.9", "1.0", "empty"])
def test_pass_rate_matches_fixture(case: dict) -> None:
    assert _close(pass_rate(case["passed"], case["total"]), case["rate"])


def test_confusion_metrics_match_fixture() -> None:
    expected = HAND["confusion"]
    assert _close(
        precision(expected["true_positive"], expected["false_positive"]),
        expected["precision"],
    )
    assert _close(recall(expected["true_positive"], expected["false_negative"]), expected["recall"])
    assert _close(
        f1(expected["precision"], expected["recall"]),
        expected["f1"],
    )
    assert Confusion(3, 1, 2, 0).total == 6


@pytest.mark.parametrize("case", HAND["percentiles"], ids=["default", "twenty", "empty"])
def test_percentiles_match_fixture(case: dict) -> None:
    assert _close(percentile(case["values"], 50), case["p50"])
    assert _close(p95(case["values"]), case.get("p95"))


def test_percentile_boundary_and_error() -> None:
    assert percentile([1, 2, 3], 100) == 3.0
    assert p95([]) is None
    with pytest.raises(ValueError, match="percent"):
        percentile([1], 0)
    with pytest.raises(ValueError, match="percent"):
        percentile([1], 101)


@pytest.mark.parametrize("case", HAND["context_recall"], ids=["full", "partial", "none"])
def test_context_recall_matches_fixture(case: dict) -> None:
    assert _close(
        context_evidence_recall(case["context"], case["required"]),
        case["recall"],
    )


def test_precision_at_k_divides_by_k_even_when_short() -> None:
    assert precision_at_k(["d1"], ["d1"], 3) == pytest.approx(1 / 3)
    assert precision_at_k([], ["d1"], 5) == 0.0


def test_no_relevant_labels_makes_recall_unavailable() -> None:
    assert recall_at_k(["d1"], [], 5) is None


def test_ndcg_unavailable_cases() -> None:
    assert ndcg_at_k(["d1"], {}, 5) is None
    assert ndcg_at_k(["d1"], {"d1": 0}, 5) is None


def test_invalid_k_and_passed_raise() -> None:
    with pytest.raises(ValueError, match="k must be positive"):
        recall_at_k(["d1"], ["d1"], 0)
    with pytest.raises(ValueError, match="k must be positive"):
        precision_at_k(["d1"], ["d1"], 0)
    with pytest.raises(ValueError, match="k must be positive"):
        ndcg_at_k(["d1"], {"d1": 1}, 0)
    with pytest.raises(ValueError, match="passed"):
        pass_rate(51, 50)


def test_duplicate_evidence_collapses_to_earliest_rank() -> None:
    assert dedupe_earliest(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]
    duplicated = ["d1", "d1", "d1"]
    assert recall_at_k(duplicated, ["d1"], 3) == recall_at_k(["d1"], ["d1"], 3)
    assert mrr(duplicated, ["d1"]) == mrr(["d1"], ["d1"])


def test_recall_at_k_is_monotonic_in_k() -> None:
    retrieved = ["x", "y", "d1", "d2"]
    relevant = ["d1", "d2"]
    values = [recall_at_k(retrieved, relevant, k) for k in range(1, 5)]
    assert values == sorted(values)
    assert values[-1] == 1.0


def test_case_order_does_not_change_aggregate_counts() -> None:
    first = [recall_at_k(["d1", "x"], ["d1"], 2), recall_at_k(["d2"], ["d2"], 2)]
    second = [recall_at_k(["d2"], ["d2"], 2), recall_at_k(["d1", "x"], ["d1"], 2)]
    assert sum(first) == sum(second)


def test_stricter_threshold_is_monotonic() -> None:
    scores = [0.1, 0.5, 0.9]
    thresholds = [0.9, 0.5, 0.1]
    passing = [sum(score >= threshold for score in scores) for threshold in thresholds]
    assert passing == sorted(passing)
    assert passing[0] <= passing[-1]
