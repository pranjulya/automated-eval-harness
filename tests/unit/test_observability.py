"""Observability: bounded metrics and redaction."""

from __future__ import annotations

import pytest

from eval_harness.observability import MetricRegistry, redact_event, safe_event


def test_metric_labels_are_allowlisted() -> None:
    registry = MetricRegistry()
    registry.increment("runs_total", {"decision": "PASS", "profile": "rag"})
    registry.observe("latency_ms", 12.0, {"adapter": "http"})
    snapshot = registry.snapshot()
    assert snapshot["counters"]
    assert snapshot["histograms"]


@pytest.mark.parametrize("label", ["case_id", "run_id", "prompt", "tenant", "model", "user"])
def test_high_cardinality_labels_are_rejected(label: str) -> None:
    registry = MetricRegistry()
    with pytest.raises(ValueError, match="disallowed metric label"):
        registry.increment("runs_total", {label: "x"})


def test_safe_event_drops_disallowed_fields() -> None:
    event = safe_event(
        run_id="r1",
        case_id="c1",
        decision="PASS",
        prompt="secret prompt text",
        raw_output="leaked",
    )
    assert "prompt" not in event
    assert "raw_output" not in event
    assert event["run_id"] == "r1"


def test_redact_event_scrubs_nested_secrets() -> None:
    event = {"message": "token abc123 here", "nested": {"value": "abc123"}, "list": ["abc123"]}
    redacted = redact_event(event, ["abc123"])
    assert "abc123" not in str(redacted)
    assert redacted["nested"]["value"] == "[REDACTED]"  # type: ignore[index]
    assert redacted["list"] == ["[REDACTED]"]  # type: ignore[index]


def test_redact_event_ignores_blank_secrets() -> None:
    event = {"message": "keep me"}
    assert redact_event(event, ["", "   "]) == {"message": "keep me"}
