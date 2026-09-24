"""Pure, hand-checkable metric functions.

Every function is deterministic, free of I/O, and documents its denominator and
unavailable state. Edge behavior follows `docs/evaluation/evaluation-strategy.md`
§3 and LLD §7.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "Confusion",
    "context_evidence_recall",
    "dcg",
    "dedupe_earliest",
    "f1",
    "mrr",
    "ndcg_at_k",
    "p95",
    "pass_rate",
    "percentile",
    "precision",
    "precision_at_k",
    "recall",
    "recall_at_k",
]


def pass_rate(passed: int, total: int) -> float | None:
    """Passing cases divided by expected cases. ``None`` when ``total <= 0``."""

    if total <= 0:
        return None
    if passed < 0 or passed > total:
        raise ValueError("passed must be within [0, total]")
    return passed / total


@dataclass(frozen=True, slots=True)
class Confusion:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.true_negative + self.false_negative


def precision(true_positive: int, false_positive: int) -> float | None:
    denominator = true_positive + false_positive
    if denominator == 0:
        return None
    return true_positive / denominator


def recall(true_positive: int, false_negative: int) -> float | None:
    denominator = true_positive + false_negative
    if denominator == 0:
        return None
    return true_positive / denominator


def f1(precision_value: float | None, recall_value: float | None) -> float | None:
    if precision_value is None or recall_value is None:
        return None
    if precision_value + recall_value == 0:
        return 0.0
    return 2 * precision_value * recall_value / (precision_value + recall_value)


def dedupe_earliest(retrieved: Sequence[str]) -> list[str]:
    """Collapse duplicates, keeping the earliest rank of each identity."""

    seen: set[str] = set()
    ordered: list[str] = []
    for identity in retrieved:
        if identity not in seen:
            seen.add(identity)
            ordered.append(identity)
    return ordered


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float | None:
    """Relevant identities found in top K divided by total relevant identities.

    ``None`` when there are no relevant labels (invalid for answerable cases).
    """

    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = set(relevant)
    if not relevant_set:
        return None
    top = set(dedupe_earliest(retrieved)[:k])
    return len(top & relevant_set) / len(relevant_set)


def precision_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int) -> float:
    """Relevant identities in top K divided by **K**.

    Short lists are penalized: fewer than K results still divide by K. Zero
    returned for an answerable case yields ``0.0``.
    """

    if k <= 0:
        raise ValueError("k must be positive")
    relevant_set = set(relevant)
    top = set(dedupe_earliest(retrieved)[:k])
    return len(top & relevant_set) / k


def mrr(retrieved: Sequence[str], relevant: Iterable[str]) -> float:
    """Reciprocal rank of the first relevant identity, or ``0.0``."""

    relevant_set = set(relevant)
    for rank, identity in enumerate(dedupe_earliest(retrieved), start=1):
        if identity in relevant_set:
            return 1.0 / rank
    return 0.0


def _gain(grade: int) -> float:
    return float((2**grade) - 1)


def _discount(rank: int) -> float:
    return math.log2(rank + 1)


def dcg(gains: Sequence[int]) -> float:
    """Discounted cumulative gain with ``log2(rank + 1)`` discount."""

    return sum(_gain(grade) / _discount(rank) for rank, grade in enumerate(gains, start=1))


def ndcg_at_k(retrieved: Sequence[str], grades: Mapping[str, int], k: int) -> float | None:
    """nDCG@K for graded labels. ``None`` when labels are empty or ideal DCG is 0."""

    if k <= 0:
        raise ValueError("k must be positive")
    if not grades:
        return None
    ideal_grades = sorted(grades.values(), reverse=True)[:k]
    idcg = dcg(ideal_grades)
    if idcg == 0:
        return None
    observed = [grades.get(identity, 0) for identity in dedupe_earliest(retrieved)[:k]]
    return dcg(observed) / idcg


def context_evidence_recall(
    context_ids: Iterable[str], required_ids: Iterable[str]
) -> float | None:
    """Required evidence identities retained after truncation. ``None`` if no requirement."""

    required = set(required_ids)
    if not required:
        return None
    return len(set(context_ids) & required) / len(required)


def percentile(values: Sequence[float | int], percent: float) -> float | None:
    """Inclusive nearest-rank percentile on sorted values.

    ``None`` for an empty sample. ``percent`` must be in ``(0, 100]``.
    """

    if not values:
        return None
    if not 0 < percent <= 100:
        raise ValueError("percent must be in (0, 100]")
    ordered = sorted(values)
    index = math.ceil(percent / 100 * len(ordered)) - 1
    index = max(0, min(index, len(ordered) - 1))
    return float(ordered[index])


def p95(values: Sequence[float | int]) -> float | None:
    return percentile(values, 95)
