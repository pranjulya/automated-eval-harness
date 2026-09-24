"""Validation entry point that returns a report instead of raising."""

from __future__ import annotations

from pathlib import Path

from .loader import inspect_suite
from .models import DatasetLimits, ValidationReport

__all__ = ["validate_suite"]


def validate_suite(path: Path, limits: DatasetLimits | None = None) -> ValidationReport:
    identity, _cases, errors = inspect_suite(path, limits)
    return ValidationReport(
        ok=not errors,
        root=Path(path),
        identity=identity,
        errors=errors,
    )
