"""Paired bootstrap, majority, and median tests."""

from __future__ import annotations

import pytest

from eval_harness.domain.statistics import majority, median_value, paired_bootstrap_lcb


def test_bootstrap_is_reproducible_for_a_seed() -> None:
    candidate = [0.9, 0.8, 0.7, 0.6, 0.95, 0.85, 0.75, 0.65, 0.9, 0.8]
    baseline = [0.8, 0.8, 0.7, 0.7, 0.9, 0.8, 0.7, 0.7, 0.8, 0.8]
    first = paired_bootstrap_lcb(candidate, baseline, seed=42, resamples=2000)
    second = paired_bootstrap_lcb(candidate, baseline, seed=42, resamples=2000)
    assert first.available is True
    assert first.lower_bound == second.lower_bound
    assert first.point_estimate == second.point_estimate
    assert first.resamples == 2000
    assert first.seed == 42


def test_bootstrap_point_estimate_matches_mean_difference() -> None:
    result = paired_bootstrap_lcb([1.0, 1.0], [0.5, 0.5], seed=1, resamples=1000)
    assert result.available is False  # zero variance
    assert result.point_estimate == 0.5
    assert result.reason == "zero-variance differences"


def test_bootstrap_empty_sample_is_unavailable() -> None:
    result = paired_bootstrap_lcb([], [], seed=1, resamples=1000)
    assert result.available is False
    assert result.reason == "no paired cases"


def test_bootstrap_mismatched_lengths_is_unavailable() -> None:
    result = paired_bootstrap_lcb([1.0], [0.5, 0.4], seed=1, resamples=1000)
    assert result.available is False


def test_bootstrap_positive_effect_has_positive_lower_bound() -> None:
    candidate = [0.9, 0.9, 0.8, 0.85, 0.95, 0.9, 0.88, 0.92, 0.91, 0.87]
    baseline = [0.5, 0.5, 0.45, 0.5, 0.55, 0.48, 0.5, 0.52, 0.49, 0.5]
    result = paired_bootstrap_lcb(candidate, baseline, seed=7, resamples=2000)
    assert result.available is True
    assert result.lower_bound is not None
    assert result.lower_bound > 0.0


def test_bootstrap_negative_effect_has_negative_lower_bound() -> None:
    candidate = [0.3, 0.3, 0.35, 0.3, 0.25, 0.3, 0.32, 0.28, 0.31, 0.33]
    baseline = [0.9, 0.9, 0.85, 0.9, 0.95, 0.88, 0.9, 0.92, 0.91, 0.89]
    result = paired_bootstrap_lcb(candidate, baseline, seed=7, resamples=2000)
    assert result.available is True
    assert result.lower_bound is not None
    assert result.lower_bound < -0.05


def test_bootstrap_rejects_zero_resamples() -> None:
    with pytest.raises(ValueError, match="resamples"):
        paired_bootstrap_lcb([1.0], [0.5], resamples=0)


def test_majority_and_median() -> None:
    assert majority([True, True, False]) is True
    assert majority([True, False, False]) is False
    assert majority([True, False]) is False  # tie fails safe
    assert majority([]) is None
    assert median_value([1.0, 3.0, 2.0]) == 2.0
    assert median_value([]) is None
