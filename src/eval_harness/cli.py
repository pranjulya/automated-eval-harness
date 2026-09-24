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
from .application.compare import CompareService, load_policy, load_waiver
from .application.promote import PromotionService
from .application.replay import ReplayService
from .application.run import RunConfig, RunRequest, RunService
from .config import AppConfig, load_config
from .datasets.models import ValidationConfig
from .datasets.validation import validate_suite
from .domain.attestations import GateAttestation, compute_attestation_hash, verify_attestation
from .domain.baselines import PromotionAuthorization
from .domain.cases import Profile
from .domain.gates import Comparison, GateDecision
from .domain.runs import CodeIdentity, Summary
from .domain.waivers import apply_waivers
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

_RESERVED_COMMANDS: dict[str, str] = {}


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

    compare = subparsers.add_parser("compare", help="compare a candidate run to a baseline")
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--baseline", required=True, help="baseline channel")
    compare.add_argument("--suite", required=True)
    compare.add_argument("--policy", default="evaluation/configs/gate-policy-v1.json")
    compare.add_argument("--waiver", action="append", help="waiver JSON file (repeatable)")
    compare.add_argument("--format", choices=["text", "json"], default="text")

    verify = subparsers.add_parser(
        "verify-attestation", help="verify a gate attestation before deploy"
    )
    verify.add_argument("--file", required=True)
    verify.add_argument("--commit")
    verify.add_argument("--run-manifest-hash")
    verify.add_argument("--baseline-hash")
    verify.add_argument("--allow-expired", action="store_true")

    promote = subparsers.add_parser(
        "promote-baseline", help="promote a reviewed run to a baseline channel"
    )
    promote.add_argument("--run", required=True)
    promote.add_argument("--suite", required=True)
    promote.add_argument("--channel", required=True)
    promote.add_argument("--reason", required=True)
    promote.add_argument("--approval-file", required=True)
    promote.add_argument("--policy", default="evaluation/configs/gate-policy-v1.json")

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


_DECISION_EXIT: dict[GateDecision, ExitCode] = {
    GateDecision.PASS: ExitCode.SUCCESS,
    GateDecision.BLOCK: ExitCode.BLOCK,
    GateDecision.REVIEW_REQUIRED: ExitCode.REVIEW_REQUIRED,
}


def _cmd_compare(args: argparse.Namespace, config: AppConfig) -> int:
    store = FilesystemArtifactStore(config.artifact_root)
    policy = load_policy(Path(args.policy))
    comparison: Comparison = CompareService(store).compare(
        args.candidate, args.suite, args.baseline, policy
    )
    suppressed: tuple[str, ...] = ()
    if args.waiver:
        waivers = tuple(load_waiver(Path(path)) for path in args.waiver)
        comparison, decisions = apply_waivers(comparison, waivers)
        for decision in decisions:
            if decision.accepted:
                suppressed = suppressed + decision.suppressed_reasons
            else:
                sys.stderr.write(
                    f"waiver {decision.waiver_id} rejected: {','.join(decision.failures)}\n"
                )
    if args.format == "json":
        sys.stdout.write(json.dumps(comparison.model_dump(mode="json"), sort_keys=True) + "\n")
    else:
        reason_codes = ",".join(reason.code for reason in comparison.reasons) or "none"
        sys.stdout.write(
            f"COMPARE candidate={comparison.candidate_run_id} "
            f"baseline={comparison.baseline_run_id} comparable={comparison.comparable} "
            f"decision={comparison.decision} reasons={reason_codes}\n"
        )
        if comparison.accepted_waivers:
            sys.stdout.write(
                f"WAIVERS accepted={','.join(comparison.accepted_waivers)} "
                f"suppressed={','.join(sorted(set(suppressed))) or 'none'}\n"
            )
    if not comparison.comparable:
        return int(ExitCode.INVALID)
    return int(_DECISION_EXIT[comparison.decision])


def _cmd_verify_attestation(args: argparse.Namespace, config: AppConfig) -> int:
    del config
    path = Path(args.file)
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ConfigError("attestation file cannot be read", details={"path": str(path)}) from error
    try:
        attestation = GateAttestation.model_validate_json(payload)
    except ValidationError as validation_error:
        raise ConfigError(
            "attestation file is invalid",
            details={"path": str(path), "errors": validation_error.error_count()},
        ) from validation_error
    result = verify_attestation(
        attestation,
        expected_commit=args.commit,
        expected_run_manifest_hash=args.run_manifest_hash,
        expected_baseline_hash=args.baseline_hash,
        allow_expired=args.allow_expired,
    )
    payload_out = {
        "ok": result.ok,
        "failures": list(result.failures),
        "decision": str(attestation.decision),
        "commit": attestation.commit,
        "attestation_hash": compute_attestation_hash(attestation),
    }
    sys.stdout.write(json.dumps(payload_out, sort_keys=True) + "\n")
    return int(ExitCode.SUCCESS) if result.ok else int(ExitCode.BLOCK)


def _load_authorization(path: Path) -> PromotionAuthorization:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ConfigError("approval file cannot be read", details={"path": str(path)}) from error
    try:
        payload = json.loads(raw)
    except ValueError as error:
        raise ConfigError("approval file is not valid JSON", details={"path": str(path)}) from error
    if not isinstance(payload, dict):
        raise ConfigError("approval file must be a JSON object", details={"path": str(path)})
    try:
        return PromotionAuthorization.model_validate(payload)
    except ValidationError as validation_error:
        raise ConfigError(
            "approval file is invalid",
            details={"path": str(path), "errors": validation_error.error_count()},
        ) from validation_error


def _cmd_promote(args: argparse.Namespace, config: AppConfig) -> int:
    store = FilesystemArtifactStore(config.artifact_root)
    policy = load_policy(Path(args.policy))
    authorization = _load_authorization(Path(args.approval_file)).model_copy(
        update={"reason": args.reason}
    )
    record = PromotionService(store).promote(
        args.run, args.suite, args.channel, authorization, policy.policy_hash()
    )
    sys.stdout.write(
        f"BASELINE suite={record.suite_name} channel={record.channel} "
        f"run={record.run_id} hash={record.record_hash}\n"
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
    if command == "compare":
        return _cmd_compare(args, config)
    if command == "promote-baseline":
        return _cmd_promote(args, config)
    if command == "verify-attestation":
        return _cmd_verify_attestation(args, config)
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
