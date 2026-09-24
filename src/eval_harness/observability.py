"""Bounded structured logging, metrics, and redaction.

Metric labels are restricted to a small allowlist so no unbounded identifier
(case ID, prompt, user, tenant, raw model) can become a label. Free-form
correlation IDs stay in logs/traces.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, cast

__all__ = [
    "ALLOWED_EVENT_FIELDS",
    "ALLOWED_METRIC_LABELS",
    "MetricRegistry",
    "redact_event",
    "safe_event",
]

ALLOWED_METRIC_LABELS: frozenset[str] = frozenset(
    {
        "service",
        "environment",
        "profile",
        "state",
        "code",
        "decision",
        "adapter",
        "evaluator",
        "baseline",
        "retention_class",
    }
)

ALLOWED_EVENT_FIELDS: frozenset[str] = frozenset(
    {
        "service",
        "environment",
        "version",
        "run_id",
        "case_id",
        "attempt",
        "adapter",
        "evaluator",
        "state",
        "code",
        "decision",
        "reason",
        "trace_id",
        "latency_bucket",
        "cost_available",
        "redaction_status",
    }
)


class MetricRegistry:
    """In-process counter/histogram registry with an allowlisted label schema."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}

    @staticmethod
    def _key(name: str, labels: Mapping[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
        unknown = set(labels) - ALLOWED_METRIC_LABELS
        if unknown:
            raise ValueError(f"disallowed metric label(s): {sorted(unknown)}")
        return name, tuple(sorted((key, str(value)) for key, value in labels.items()))

    def increment(
        self, name: str, labels: Mapping[str, str] | None = None, amount: float = 1.0
    ) -> None:
        key = self._key(name, labels or {})
        self._counters[key] = self._counters.get(key, 0.0) + amount

    def observe(self, name: str, value: float, labels: Mapping[str, str] | None = None) -> None:
        key = self._key(name, labels or {})
        self._histograms.setdefault(key, []).append(float(value))

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": {
                f"{name}{dict(labels)}": value for (name, labels), value in self._counters.items()
            },
            "histograms": {
                f"{name}{dict(labels)}": {
                    "count": len(values),
                    "sum": sum(values),
                    "max": max(values) if values else None,
                }
                for (name, labels), values in self._histograms.items()
            },
        }


def safe_event(**fields: Any) -> dict[str, Any]:
    """Drop any field that is not on the structured-event allowlist."""

    return {key: value for key, value in fields.items() if key in ALLOWED_EVENT_FIELDS}


def redact_event(event: Mapping[str, Any], secrets: Iterable[str]) -> dict[str, Any]:
    """Replace configured secret values anywhere in an event payload."""

    secret_list = [secret for secret in secrets if secret and secret.strip()]

    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            for secret in secret_list:
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, Mapping):
            return {key: scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return cast(dict[str, Any], scrub(dict(event)))


def dumps(event: Mapping[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, default=str)
