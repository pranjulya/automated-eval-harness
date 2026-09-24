"""Stable error envelope and exit-code mapping.

This module is deliberately free of evaluation behavior. It defines the only
exception surface the CLI and (later) the HTTP API translate into process or
HTTP responses, so error codes stay stable across entry points.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import IntEnum
from typing import Any, Final

__all__ = [
    "CliUsageError",
    "ConfigError",
    "ExitCode",
    "HarnessError",
    "InfrastructureError",
    "InterruptedRunError",
    "PhaseUnavailableError",
    "envelope",
    "redact_text",
]

REDACTED: Final = "[REDACTED]"


class ExitCode(IntEnum):
    """Stable CLI exit codes locked by PRD FR-13."""

    SUCCESS = 0
    BLOCK = 2
    REVIEW_REQUIRED = 3
    INVALID = 4
    INFRASTRUCTURE = 5
    INTERRUPTED = 130


class HarnessError(Exception):
    """Base class for every expected harness failure.

    Never place raw secrets in ``message`` or ``details``; the CLI redacts
    against configured secret names before printing, but callers should still
    avoid embedding values.
    """

    code: str = "HARNESS_ERROR"
    exit_code: ExitCode = ExitCode.INFRASTRUCTURE
    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retryable: bool | None = None,
        details: Mapping[str, Any] | None = None,
        exit_code: ExitCode | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable
        if exit_code is not None:
            self.exit_code = exit_code
        self.details: dict[str, Any] = dict(details or {})

    def envelope(self) -> dict[str, Any]:
        """Return the stable ``{code, message, retryable, details}`` envelope."""

        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message}"


class ConfigError(HarnessError):
    """Invalid, missing, or unsafe configuration. Maps to exit 4."""

    code = "CONFIG_INVALID"
    exit_code = ExitCode.INVALID


class CliUsageError(HarnessError):
    """Unknown command or invalid CLI arguments. Maps to exit 4."""

    code = "CLI_USAGE"
    exit_code = ExitCode.INVALID


class PhaseUnavailableError(HarnessError):
    """A reserved command whose owning phase is not implemented yet."""

    code = "PHASE_UNAVAILABLE"
    exit_code = ExitCode.INVALID


class InfrastructureError(HarnessError):
    """Unexpected internal/infrastructure failure. Maps to exit 5."""

    code = "INTERNAL_ERROR"
    exit_code = ExitCode.INFRASTRUCTURE


class InterruptedRunError(HarnessError):
    """SIGINT or user cancellation. Maps to exit 130."""

    code = "INTERRUPTED"
    exit_code = ExitCode.INTERRUPTED


def redact_text(value: str, secrets: Iterable[str]) -> str:
    """Replace every configured secret value found in ``value``.

    Empty and whitespace-only secrets are ignored so that an unset variable
    cannot turn the whole string into a redaction marker.
    """

    redacted = value
    for secret in secrets:
        if secret and secret.strip():
            redacted = redacted.replace(secret, REDACTED)
    return redacted


def envelope(error: BaseException, secrets: Iterable[str] = ()) -> dict[str, Any]:
    """Build a redacted envelope for any exception."""

    if isinstance(error, HarnessError):
        payload = error.envelope()
    else:
        payload = {
            "code": "INTERNAL_ERROR",
            "message": "unexpected internal error",
            "retryable": False,
            "details": type(error).__name__,
        }
    return _redact_payload(payload, list(secrets))


def _redact_payload(payload: dict[str, Any], secrets: list[str]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in payload.items():
        if isinstance(item, str):
            redacted[key] = redact_text(item, secrets)
        elif isinstance(item, Mapping):
            redacted[key] = _redact_payload(dict(item), secrets)
        elif isinstance(item, list):
            redacted[key] = [redact_text(v, secrets) if isinstance(v, str) else v for v in item]
        else:
            redacted[key] = item
    return redacted
