"""Paired statistics and nondeterminism aggregation (pure, seeded)."""

from __future__ import annotations

import random
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from .metrics import percentile

__all__ = [
    "BootstrapResult",
    "majority",
    "median_value",
    "paired_bootstrap_lcb",
]

DEFAULT_RESAMPLES = 10_000
DEFAULT_SEED = 20260910
LOWER_PERCENTILE = 5.0


class BootstrapResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    available: bool
    lower_bound: float | None = None
    point_estimate: float | None = None
    paired_count: int = 0
    resamples: int = 0
    seed: int = 0
    reason: str = ""


def paired_bootstrap_lcb(
    candidate: Sequence[float],
    baseline: Sequence[float],
    *,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
    lower_percentile: float = LOWER_PERCENTILE,
) -> BootstrapResult:
    """Paired bootstrap lower confidence bound on mean(candidate - baseline).

    Resamples cases (not metric observations) with a recorded seed. Returns
    ``available=False`` when there are no paired cases or when the sample is
    constant and therefore carries no interval information.
    """

    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if len(candidate) != len(baseline) or not candidate:
        return BootstrapResult(
            available=False,
            resamples=resamples,
            seed=seed,
            reason="no paired cases",
        )
    differences = [c - b for c, b in zip(candidate, baseline, strict=True)]
    point = sum(differences) / len(differences)
    if all(value == differences[0] for value in differences):
        return BootstrapResult(
            available=False,
            lower_bound=point,
            point_estimate=point,
            paired_count=len(differences),
            resamples=resamples,
            seed=seed,
            reason="zero-variance differences",
        )
    rng = random.Random(seed)
    size = len(differences)
    means: list[float] = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(size):
            total += differences[rng.randrange(size)]
        means.append(total / size)
    return BootstrapResult(
        available=True,
        lower_bound=percentile(means, lower_percentile),
        point_estimate=point,
        paired_count=size,
        resamples=resamples,
        seed=seed,
    )


def majority(passes: Sequence[bool]) -> bool | None:
    """Majority vote across replicates. ``None`` for an empty sample; ties fail safe."""

    if not passes:
        return None
    return sum(1 for value in passes if value) * 2 > len(passes)


def median_value(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return percentile(values, 50.0)
