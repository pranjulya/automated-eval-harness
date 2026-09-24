"""Unit tests for strict startup configuration."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from pydantic import ValidationError

from eval_harness.config import Environment, LogLevel, SecretRef, load_config
from eval_harness.errors import ConfigError


def test_load_config_defaults(tmp_path: Path) -> None:
    config = load_config({}, base_dir=tmp_path)
    assert config.environment is Environment.DEVELOPMENT
    assert config.log_level is LogLevel.INFO
    assert config.artifact_root == tmp_path / "artifacts"
    assert config.secret_refs == ()


def test_load_config_reads_explicit_values(tmp_path: Path) -> None:
    env = {
        "EVAL_HARNESS_ENVIRONMENT": "test",
        "EVAL_HARNESS_LOG_LEVEL": "warning",
        "EVAL_HARNESS_ARTIFACT_ROOT": "/var/tmp/artifacts",
    }
    config = load_config(env, base_dir=tmp_path)
    assert config.environment is Environment.TEST
    assert config.log_level is LogLevel.WARNING
    assert config.artifact_root == Path("/var/tmp/artifacts")


def test_relative_artifact_root_resolves_under_base_dir(tmp_path: Path) -> None:
    config = load_config({"EVAL_HARNESS_ARTIFACT_ROOT": "runs"}, base_dir=tmp_path)
    assert config.artifact_root == tmp_path / "runs"


def test_unknown_harness_key_is_rejected() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config({"EVAL_HARNESS_MYSTERY": "1"})
    assert excinfo.value.code == "CONFIG_INVALID"
    assert excinfo.value.details["keys"] == ["EVAL_HARNESS_MYSTERY"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("EVAL_HARNESS_ENVIRONMENT", "staging"),
        ("EVAL_HARNESS_LOG_LEVEL", "verbose"),
    ],
)
def test_invalid_enums_are_rejected(key: str, value: str) -> None:
    with pytest.raises(ConfigError):
        load_config({key: value})


def test_production_debug_is_rejected() -> None:
    with pytest.raises(ConfigError, match="debug logging is forbidden"):
        load_config({"EVAL_HARNESS_ENVIRONMENT": "production", "EVAL_HARNESS_LOG_LEVEL": "DEBUG"})


def test_empty_artifact_root_is_rejected() -> None:
    with pytest.raises(ConfigError, match="artifact root must not be empty"):
        load_config({"EVAL_HARNESS_ARTIFACT_ROOT": "  "})


def test_secret_refs_are_names_only_and_must_exist() -> None:
    env = {"EVAL_HARNESS_SECRET_REFS": "TARGET_API_KEY,JUDGE_API_KEY", "TARGET_API_KEY": "t"}
    with pytest.raises(ConfigError) as excinfo:
        load_config(env)
    assert excinfo.value.details["env_var"] == "JUDGE_API_KEY"


def test_secret_refs_resolve_values_for_redaction_only() -> None:
    env = {
        "EVAL_HARNESS_SECRET_REFS": "TARGET_API_KEY, TARGET_API_KEY",
        "TARGET_API_KEY": "super-secret",
    }
    config = load_config(env)
    assert config.secret_names() == ("TARGET_API_KEY",)
    assert config.resolved_secret_values(env) == ("super-secret",)
    assert "super-secret" not in repr(config)


@pytest.mark.parametrize("name", ["lowercase", "1STARTS_WITH_DIGIT", "HAS-DASH"])
def test_invalid_secret_names_are_rejected(name: str) -> None:
    with pytest.raises(ConfigError):
        load_config({"EVAL_HARNESS_SECRET_REFS": name})


def test_empty_secret_refs_are_allowed() -> None:
    assert load_config({"EVAL_HARNESS_SECRET_REFS": " , "}).secret_refs == ()


def test_secret_ref_model_is_strict() -> None:
    with pytest.raises(ValidationError):
        SecretRef(env_var="OK_NAME", unexpected="x")  # type: ignore[call-arg]


def test_ensure_artifact_root_creates_directory(tmp_path: Path) -> None:
    config = load_config({"EVAL_HARNESS_ARTIFACT_ROOT": "artifacts"}, base_dir=tmp_path)
    root = config.ensure_artifact_root()
    assert root.is_dir()


def test_ensure_artifact_root_rejects_file(tmp_path: Path) -> None:
    target = tmp_path / "not-a-dir"
    target.write_text("x", encoding="utf-8")
    config = load_config({"EVAL_HARNESS_ARTIFACT_ROOT": str(target)})
    with pytest.raises(ConfigError, match="artifact root cannot be created"):
        config.ensure_artifact_root()


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses permission bits")
def test_ensure_artifact_root_rejects_unwritable(tmp_path: Path) -> None:
    target = tmp_path / "readonly"
    target.mkdir()
    target.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        config = load_config({"EVAL_HARNESS_ARTIFACT_ROOT": str(target)})
        with pytest.raises(ConfigError, match="artifact root is not writable"):
            config.ensure_artifact_root()
    finally:
        target.chmod(stat.S_IRWXU)
