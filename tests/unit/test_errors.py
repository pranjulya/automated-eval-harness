"""Unit tests for the stable error envelope and redaction."""

from __future__ import annotations

import pytest

from eval_harness.errors import (
    ConfigError,
    ExitCode,
    HarnessError,
    InfrastructureError,
    InterruptedRunError,
    envelope,
    redact_text,
)


def test_exit_codes_are_locked() -> None:
    assert ExitCode.SUCCESS == 0
    assert ExitCode.BLOCK == 2
    assert ExitCode.REVIEW_REQUIRED == 3
    assert ExitCode.INVALID == 4
    assert ExitCode.INFRASTRUCTURE == 5
    assert ExitCode.INTERRUPTED == 130


def test_envelope_shape() -> None:
    error = ConfigError("bad config", details={"field": "environment"})
    assert error.envelope() == {
        "code": "CONFIG_INVALID",
        "message": "bad config",
        "retryable": False,
        "details": {"field": "environment"},
    }


def test_default_exit_codes_by_type() -> None:
    assert ConfigError("x").exit_code is ExitCode.INVALID
    assert InfrastructureError("x").exit_code is ExitCode.INFRASTRUCTURE
    assert InterruptedRunError("x").exit_code is ExitCode.INTERRUPTED


def test_redact_text_replaces_secret_and_ignores_blank() -> None:
    text = "token=abc123 and empty=''"
    assert redact_text(text, ["abc123", "", "   "]) == "token=[REDACTED] and empty=''"


def test_envelope_redacts_nested_details_and_lists() -> None:
    secret = "s3cr3t-value"
    error = HarnessError(
        f"leak {secret}",
        details={"outer": {"inner": f"value {secret}"}, "list": [f"a {secret}"]},
    )
    payload = envelope(error, [secret])
    assert secret not in str(payload)
    assert payload["message"] == "leak [REDACTED]"
    assert payload["details"]["outer"]["inner"] == "value [REDACTED]"  # type: ignore[index]
    assert payload["details"]["list"] == ["a [REDACTED]"]  # type: ignore[index]


def test_envelope_for_unexpected_error_is_generic() -> None:
    payload = envelope(ValueError("raw internal detail"))
    assert payload == {
        "code": "INTERNAL_ERROR",
        "message": "unexpected internal error",
        "retryable": False,
        "details": "ValueError",
    }


@pytest.mark.parametrize("details", [None, {}, {"a": 1}])
def test_details_never_shared_between_instances(details: dict[str, int] | None) -> None:
    error = HarnessError("x", details=details)
    error.details["mutated"] = True
    assert HarnessError("y").details == {}
