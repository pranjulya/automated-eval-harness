"""Unit tests for the CLI shell contract."""

from __future__ import annotations

import json

import pytest

from eval_harness import __version__
from eval_harness.cli import build_parser, main


def test_version_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "validate" in out
    assert "promote-baseline" in out


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out


def test_unknown_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["frobnicate"]) == 4
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == "CLI_USAGE"


def test_reserved_subcommands_exit_four(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--suite", "s", "--config", "c"]) == 4
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == "PHASE_UNAVAILABLE"
    assert payload["details"]["available_in"] == "Phase 04"


@pytest.mark.parametrize(
    ("command", "phase"),
    [
        ("run", "Phase 04"),
        ("replay", "Phase 04"),
        ("inspect", "Phase 04"),
        ("compare", "Phase 06"),
        ("promote-baseline", "Phase 06"),
    ],
)
def test_reserved_command_phase_mapping(
    command: str, phase: str, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = {
        "run": ["run", "--suite", "s", "--config", "c"],
        "replay": ["replay", "--run", "r"],
        "inspect": ["inspect", "--run", "r"],
        "compare": ["compare", "--candidate", "c", "--baseline", "b"],
        "promote-baseline": [
            "promote-baseline",
            "--run",
            "r",
            "--suite",
            "s",
            "--channel",
            "ch",
            "--reason",
            "why",
            "--approval-file",
            "f",
        ],
    }[command]
    assert main(argv) == 4
    payload = json.loads(capsys.readouterr().err)
    assert payload["details"]["available_in"] == phase


def test_missing_required_argument_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--suite", "s"]) == 4
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == "CLI_USAGE"


def test_invalid_config_exits_four(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EVAL_HARNESS_ENVIRONMENT", "staging")
    assert main(["--version"]) == 4
    payload = json.loads(capsys.readouterr().err)
    assert payload["code"] == "CONFIG_INVALID"


def test_keyboard_interrupt_exits_130(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("eval_harness.cli.load_config", _raise)
    assert main([]) == 130


def test_unexpected_error_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("raw internal detail")

    monkeypatch.setattr("eval_harness.cli._dispatch", _boom)
    assert main(["validate", "--suite", "s", "--config", "c"]) == 5
    payload = json.loads(capsys.readouterr().err)
    assert payload["message"] == "unexpected internal error"
    assert "raw internal detail" not in json.dumps(payload)


def test_build_parser_prog_name() -> None:
    parser = build_parser()
    assert parser.prog == "eval-harness"
