# Phase 00 — Repository and CLI Foundation

**Status:** NOT_STARTED — specification only; awaiting user approval.

## Goal

Create the smallest installable, typed Python package with strict configuration, stable CLI/error/exit contracts, test tooling, container baseline, and CI checks. It contains no evaluation behavior.

## Prerequisites and decisions

- User approves the complete planning package.
- ADR-001 and ADR-002 accepted.
- Verify and lock supported dependency patch versions at implementation time.

## References and concepts

Read PRD §§8–9, HLD §§1–2/6, LLD §§1/11/13, and `AGENTS.md`. Learn package boundaries, composition roots, strict startup configuration, stable exit codes, liveness/readiness, reproducible dependency locks, and why foundation excludes speculative domain abstractions.

## Files

- Create `pyproject.toml`, lock file, `.dockerignore`, `.env.example`. Keep existing `LICENSE` and `.gitignore`; do not replace the license without review.
- Create `src/eval_harness/__init__.py`, `config.py`, `errors.py`, `cli.py`, `__main__.py`.
- Create `tests/unit/test_config.py`, `tests/unit/test_cli.py`, `tests/unit/test_errors.py`.
- Create `Dockerfile`, `.github/workflows/ci.yml`.
- Modify `README.md`, `Implementation.md`, this phase, and `Learning/concepts/01-reproducible-evaluation.md`.

## Interfaces produced

- `main(argv: Sequence[str] | None = None) -> int` with help/version and reserved subcommands.
- Strict `AppConfig` containing artifact root, environment, logging level, and secret references without resolving provider behavior.
- Stable exception envelope `{code, message, retryable, details}` and exit mapping `0/2/3/4/5/130`.

## Tasks

- [ ] Add package metadata and only approved direct dependencies; justify each in the PR description.
- [ ] Test invalid environment/config, secret redaction, CLI help/version, unknown command, and exception-to-exit mapping first.
- [ ] Implement immutable strict config and errors; CLI subcommands return a documented “not available until phase” usage error without domain behavior.
- [ ] Add Ruff, strict mypy for the package, pytest configuration, coverage reporting, and build checks.
- [ ] Add a non-root container that can run help/version and has no embedded credential.
- [ ] Add CI for locked install, formatting/lint, typing, unit tests, package build, and container build.
- [ ] Document exact local commands and update the paired learning note.

## Tests and failure scenarios

Missing/unknown config, invalid paths, production debug mode, secret-shaped values in errors, unknown arguments, interrupted command, non-writable artifact root, import without environment, and clean wheel installation. Tests must not need network, credentials, Docker services, or provider calls.

## Verification

Run `python -m pytest tests/unit -q`, `ruff format --check .`, `ruff check .`, `mypy src/eval_harness`, `python -m build`, and the documented container build/help command. Expected result: all pass; only CLI help/version/foundation behavior exists.

## Acceptance criteria and Definition of Done

A clean checkout installs from the lock, help/version are stable, config errors are sanitized, package/container builds pass, CI enforces the same checks, no evaluation/provider/database/queue behavior appears, documentation matches commands, learning note explains boundaries, diff review passes, and phase status reaches `COMPLETE` through the allowed sequence.
