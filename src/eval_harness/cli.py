"""Authoritative command-line entry point.

The CLI is translation only: it parses arguments, loads strict configuration,
and dispatches to application services. Scoring, thresholds, and gate decisions
live in domain/application code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from pydantic import ValidationError

from . import __version__
from .adapters.artifacts.filesystem import FilesystemArtifactStore
from .adapters.targets import FakeTargetAdapter, HttpTargetAdapter, load_fake_responses
from .application.replay import ReplayService
from .application.run import RunConfig, RunRequest, RunService
from .config import AppConfig, load_config
from .datasets.models import ValidationConfig
from .datasets.validation import validate_suite
from .domain.cases import Profile
from .domain.runs import CodeIdentity, Summary
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
from .evaluators import build_registry, load_schema_resolver

__all__ = ["build_parser", "main"]

_RESERVED_COMMANDS: dict[str, str] = {
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

    run = subparsers.add_parser("run", help="run an evaluation")
    run.add_argument("--suite", required=True)
    run.add_argument("--config", required=True)
    run.add_argument("--case", action="append")
    run.add_argument("--profile", choices=[profile.value for profile in Profile])
    run.add_argument("--tag")
    run.add_argument("--run-id")
    run.add_argument("--format", choices=["text", "json"], default="text")

    replay = subparsers.add_parser("replay", help="replay a run")
    replay.add_argument("--run", required=True)

    inspect = subparsers.add_parser("inspect", help="inspect a run")
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


def _load_run_config(path: Path) -> RunConfig:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ConfigError(
            "run config cannot be read",
            details={"path": str(path), "reason": error.strerror or "error"},
        ) from error
    try:
        return RunConfig.model_validate_json(raw)
    except ValidationError as validation_error:
        raise ConfigError(
            "run config is invalid",
            details={"path": str(path), "errors": validation_error.error_count()},
        ) from validation_error


def _schema_resolver(repo_root: Path) -> Any:
    return load_schema_resolver(repo_root)


def _build_adapter(run_config: RunConfig) -> Any:
    if run_config.target.adapter == "fake":
        if not run_config.fake_responses:
            raise ConfigError("fake adapter requires 'fake_responses'")
        return FakeTargetAdapter(load_fake_responses(Path(run_config.fake_responses)))
    if run_config.target.adapter == "http":
        return HttpTargetAdapter()
    raise ConfigError("unknown adapter", details={"adapter": run_config.target.adapter})


def _code_identity() -> CodeIdentity:
    commit = "unknown"
    dirty = True
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        )
        if rev.returncode == 0:
            commit = rev.stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=False
        )
        if status.returncode == 0:
            dirty = bool(status.stdout.strip())
    except OSError:
        pass
    return CodeIdentity(commit=commit, dirty=dirty, package_version=__version__)


def _close_adapter(adapter: Any) -> None:
    close = getattr(adapter, "close", None)
    if callable(close):
        close()


def _cmd_validate(args: argparse.Namespace, config: AppConfig) -> int:
    del config
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


def _cmd_run(args: argparse.Namespace, config: AppConfig) -> int:
    run_config = _load_run_config(Path(args.config))
    run_config = run_config.model_copy(update={"artifact_root": str(config.artifact_root)})
    repo_root = Path.cwd()
    adapter = _build_adapter(run_config)
    try:
        service = RunService(
            adapter=adapter,
            registry=build_registry(_schema_resolver(repo_root)),
            code=_code_identity(),
            environment=config.environment.value,
        )
        request = RunRequest(
            suite_path=Path(args.suite),
            config=run_config,
            case_ids=tuple(args.case or ()),
            profile=Profile(args.profile) if args.profile else None,
            tag=args.tag,
            run_id=args.run_id,
        )
        outcome = service.run(request)
    finally:
        _close_adapter(adapter)
    if args.format == "json":
        sys.stdout.write(json.dumps(outcome.model_dump(mode="json"), sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            f"RUN {outcome.run_id} status={outcome.status} "
            f"expected={outcome.summary.expected} completed={outcome.summary.completed} "
            f"pass_rate={outcome.summary.pass_rate} report={outcome.report_path}\n"
        )
    return int(outcome.exit_code)


def _cmd_replay(args: argparse.Namespace, config: AppConfig) -> int:
    store = FilesystemArtifactStore(config.artifact_root)
    service = ReplayService(build_registry(_schema_resolver(Path.cwd())))
    outcome = service.replay(store, args.run)
    sys.stdout.write(
        f"REPLAY {outcome.run_id} pass_rate={outcome.summary.pass_rate} "
        f"completed={outcome.summary.completed}\n"
    )
    return int(outcome.exit_code)


def _cmd_inspect(args: argparse.Namespace, config: AppConfig) -> int:
    store = FilesystemArtifactStore(config.artifact_root)
    store.read_bundle(args.run)
    bundle = store.run_dir(args.run)
    summary = Summary.model_validate_json((bundle / "summary.json").read_text(encoding="utf-8"))
    cases = [
        json.loads(line)
        for line in (bundle / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.failures_only:
        cases = [case for case in cases if case["state"] != "PASS"]
    if args.format == "json":
        sys.stdout.write(
            json.dumps({"summary": summary.model_dump(mode="json"), "cases": cases}, sort_keys=True)
            + "\n"
        )
    else:
        sys.stdout.write(
            f"RUN {args.run} completed={summary.completed} pass_rate={summary.pass_rate}\n"
        )
        for case in cases:
            code = next(
                (finding["code"] for finding in case["findings"] if not finding["passed"]),
                "",
            )
            sys.stdout.write(
                f"  {case['case_id']} {case['primary_profile']} {case['state']} {code}\n"
            )
    return int(ExitCode.SUCCESS)


def _dispatch(args: argparse.Namespace, config: AppConfig) -> int:
    command = args.command
    if command is None:
        build_parser().print_help()
        return int(ExitCode.SUCCESS)
    if command == "validate":
        return _cmd_validate(args, config)
    if command == "run":
        return _cmd_run(args, config)
    if command == "replay":
        return _cmd_replay(args, config)
    if command == "inspect":
        return _cmd_inspect(args, config)
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
