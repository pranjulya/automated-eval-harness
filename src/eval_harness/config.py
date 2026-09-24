"""Strict startup configuration for the evaluation harness.

Configuration is resolved once at the process boundary from environment
variables. Secrets are referenced by environment-variable name only; their
values are never stored on the resolved config, printed, or persisted.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from .errors import ConfigError

__all__ = [
    "AppConfig",
    "Environment",
    "LogLevel",
    "SecretRef",
    "load_config",
]

ENV_PREFIX: Final = "EVAL_HARNESS_"
_SECRET_NAME_PATTERN: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")

_KEYS: Final[dict[str, str]] = {
    "ENVIRONMENT": f"{ENV_PREFIX}ENVIRONMENT",
    "LOG_LEVEL": f"{ENV_PREFIX}LOG_LEVEL",
    "ARTIFACT_ROOT": f"{ENV_PREFIX}ARTIFACT_ROOT",
    "SECRET_REFS": f"{ENV_PREFIX}SECRET_REFS",
}


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SecretRef(BaseModel):
    """A named reference to a secret, never the secret value itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    env_var: str

    @field_validator("env_var")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not _SECRET_NAME_PATTERN.match(value):
            raise ValueError("secret reference must be an uppercase environment variable name")
        return value


class AppConfig(BaseModel):
    """Immutable, strictly parsed process configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    environment: Environment = Environment.DEVELOPMENT
    artifact_root: Path
    log_level: LogLevel = LogLevel.INFO
    secret_refs: tuple[SecretRef, ...] = ()

    def secret_names(self) -> tuple[str, ...]:
        return tuple(ref.env_var for ref in self.secret_refs)

    def resolved_secret_values(self, environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
        """Return secret values for redaction only. Never log the result."""

        source = environ if environ is not None else os.environ
        return tuple(source[name] for name in self.secret_names() if source.get(name))

    def ensure_artifact_root(self) -> Path:
        """Create the artifact root if needed and verify it is writable."""

        root = self.artifact_root
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ConfigError(
                "artifact root cannot be created",
                details={"path": str(root), "reason": error.strerror or error.__class__.__name__},
            ) from error
        if not root.is_dir():
            raise ConfigError("artifact root is not a directory", details={"path": str(root)})
        probe = root / ".write-probe"
        try:
            probe.write_text("", encoding="utf-8")
            probe.unlink()
        except OSError as error:
            raise ConfigError(
                "artifact root is not writable",
                details={"path": str(root), "reason": error.strerror or error.__class__.__name__},
            ) from error
        return root


def _parse_secret_refs(raw: str) -> tuple[SecretRef, ...]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    refs: list[SecretRef] = []
    seen: set[str] = set()
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        try:
            refs.append(SecretRef(env_var=name))
        except ValidationError as error:
            raise ConfigError(
                "invalid secret reference name",
                details={"detail": name},
            ) from error
    return tuple(refs)


def _reject_unknown_keys(environ: Mapping[str, str]) -> None:
    known = set(_KEYS.values())
    unknown = sorted(key for key in environ if key.startswith(ENV_PREFIX) and key not in known)
    if unknown:
        raise ConfigError(
            "unknown harness environment variable",
            details={"keys": unknown},
        )


def load_config(
    environ: Mapping[str, str] | None = None,
    *,
    base_dir: Path | None = None,
) -> AppConfig:
    """Resolve :class:`AppConfig` from environment variables, failing closed."""

    source: Mapping[str, str] = environ if environ is not None else os.environ
    _reject_unknown_keys(source)

    raw_environment = source.get(_KEYS["ENVIRONMENT"], Environment.DEVELOPMENT.value)
    raw_log_level = source.get(_KEYS["LOG_LEVEL"], LogLevel.INFO.value)
    raw_root = source.get(_KEYS["ARTIFACT_ROOT"], "artifacts")
    raw_secrets = source.get(_KEYS["SECRET_REFS"], "")

    try:
        environment = Environment(raw_environment)
    except ValueError as error:
        raise ConfigError(
            "invalid environment",
            details={"allowed": [member.value for member in Environment]},
        ) from error
    try:
        log_level = LogLevel(raw_log_level.upper())
    except ValueError as error:
        raise ConfigError(
            "invalid log level",
            details={"allowed": [member.value for member in LogLevel]},
        ) from error

    if environment is Environment.PRODUCTION and log_level is LogLevel.DEBUG:
        raise ConfigError("debug logging is forbidden in production")

    if not raw_root.strip():
        raise ConfigError("artifact root must not be empty")
    artifact_root = Path(raw_root)
    if base_dir is not None and not artifact_root.is_absolute():
        artifact_root = base_dir / artifact_root

    secret_refs = _parse_secret_refs(raw_secrets)
    for ref in secret_refs:
        if not source.get(ref.env_var):
            raise ConfigError(
                "referenced secret environment variable is not set",
                details={"env_var": ref.env_var},
            )

    return AppConfig(
        environment=environment,
        artifact_root=artifact_root,
        log_level=log_level,
        secret_refs=secret_refs,
    )
