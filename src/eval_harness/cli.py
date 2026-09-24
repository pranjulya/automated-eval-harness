"""Authoritative command-line entry point.

The CLI is translation only: it parses arguments, loads strict configuration,
and dispatches to application services. In Phase 00 no application services
exist yet, so reserved subcommands fail closed with a documented
``PHASE_UNAVAILABLE`` error and exit code 4.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError

from . import __version__
from .config import AppConfig, load_config
from .datasets.models import ValidationConfig
from .datasets.validation import validate_suite
from .errors import (
    CliUsageError,
    ConfigError,
    ExitCode,
    HarnessError,
    InfrastructureError,
    InterruptedRunError,
    PhaseUnavailableError,
    envelope,
)

__all__ = ["build_parser", "main"]

# command -> owning phase, used for the not-yet-available message.
_RESERVED_COMMANDS: dict[str, str] = {
    "run": "Phase 04",
    "replay": "Phase 04",
    "inspect": "Phase 04",
    "compare": "Phase 06",
    "promote-baseline": "Phase 06",
}


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises instead of exiting 2 on usage errors."""

    def error(self, message: str) -> NoReturn:
        raise CliUsageError(message, details={"usage": self.format_usage().strip()})


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="eval-harness",
        description="Reproducible GenAI evaluation harness.",
    )
    parser.add_argument("--version", action="version", version=f"eval-harness {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    validate = subparsers.add_parser("validate", help="validate a golden suite")
    validate.add_argument("--suite", required=True)
    validate.add_argument("--config", required=True)
    validate.add_argument("--format", choices=["text", "json"], default="text")

    run = subparsers.add_parser("run", help="run an evaluation (Phase 04)")
    run.add_argument("--suite", required=True)
    run.add_argument("--config", required=True)
    run.add_argument("--case")
    run.add_argument("--profile")
    run.add_argument("--tag")
    run.add_argument("--baseline")

    replay = subparsers.add_parser("replay", help="replay a run (Phase 04)")
    replay.add_argument("--run", required=True)

    inspect = subparsers.add_parser("inspect", help="inspect a run (Phase 04)")
    inspect.add_argument("--run", required=True)
    inspect.add_argument("--failures-only", action="store_true")
    inspect.add_argument("--format", choices=["text", "json"], default="text")

    compare = subparsers.add_parser("compare", help="compare to a baseline (Phase 06)")
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--baseline", required=True)

    promote = subparsers.add_parser(
        "promote-baseline", help="promote a reviewed baseline (Phase 06)"
    )
    promote.add_argument("--run", required=True)
    promote.add_argument("--suite", required=True)
    promote.add_argument("--channel", required=True)
    promote.add_argument("--reason", required=True)
    promote.add_argument("--approval-file", required=True)

    return parser


def _cmd_validate(args: argparse.Namespace, config: AppConfig) -> int:
    del config  # validation limits come from the validation config file
    config_path = Path(args.config)
    try:
        raw = config_path.read_bytes()
    except OSError as error:
        raise ConfigError(
            "validation config cannot be read",
            details={"path": str(config_path), "reason": error.strerror or "error"},
        ) from error
    try:
        validation_config = ValidationConfig.model_validate_json(raw)
    except ValidationError as validation_error:
        raise ConfigError(
            "validation config is invalid",
            details={"path": str(config_path), "errors": validation_error.error_count()},
        ) from validation_error
    limits = validation_config.to_limits(config_path.resolve().parent)
    report = validate_suite(Path(args.suite), limits)
    if args.format == "json":
        stream = sys.stdout if report.ok else sys.stderr
        stream.write(json.dumps(report.to_dict(), sort_keys=True) + "\n")
    elif report.ok and report.identity is not None:
        identity = report.identity
        sys.stdout.write(
            f"OK {identity.name} {identity.suite_version} "
            f"cases={len(identity.case_ids)} hash={identity.content_hash}\n"
        )
    else:
        for message in report.errors:
            sys.stderr.write(message + "\n")
    return int(ExitCode.SUCCESS) if report.ok else int(ExitCode.INVALID)


def _dispatch(args: argparse.Namespace, config: AppConfig) -> int:
    command = args.command
    if command is None:
        build_parser().print_help()
        return int(ExitCode.SUCCESS)
    if command == "validate":
        return _cmd_validate(args, config)
    if command in _RESERVED_COMMANDS:
        phase = _RESERVED_COMMANDS[command]
        raise PhaseUnavailableError(
            f"'{command}' is not available until {phase}",
            details={"command": command, "available_in": phase},
        )
    raise CliUsageError("unknown command", details={"command": str(command)})


def _emit(error: HarnessError, secrets: tuple[str, ...]) -> None:
    payload = envelope(error, secrets)
    sys.stderr.write(json.dumps(payload, sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    secrets: tuple[str, ...] = ()
    try:
        config = load_config()
        secrets = config.resolved_secret_values()
        parser = build_parser()
        try:
            args = parser.parse_args(list(argv) if argv is not None else None)
        except SystemExit as exit_signal:  # --help / --version
            return int(exit_signal.code or 0)
        return _dispatch(args, config)
    except SystemExit as exit_signal:  # pragma: no cover - defensive
        return int(exit_signal.code or 0)
    except HarnessError as error:
        _emit(error, secrets)
        return int(error.exit_code)
    except KeyboardInterrupt:
        interrupted = InterruptedRunError("interrupted")
        _emit(interrupted, secrets)
        return int(interrupted.exit_code)
    except Exception as error:  # last-resort boundary
        internal = InfrastructureError(
            "unexpected internal error", details={"type": type(error).__name__}
        )
        _emit(internal, secrets)
        return int(internal.exit_code)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
