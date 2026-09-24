# ADR-002 — User entry point

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

The product needs a stable, scriptable, CI-friendly entry point whose exit codes and output are testable. `docs/architecture/LLD.md` §11 fixes the CLI contract and exit codes; PRD FR-13/FR-16 require stable mapping. A later read-mostly HTTP API must reuse the same application services.

## Decision

The standard-library `argparse` CLI is the authoritative entry point. It translates arguments into application-service calls and owns process exit codes (`0/2/3/4/5/130`); it contains no evaluation policy. FastAPI is added in Phase 08 as a thin authenticated wrapper over the same services, never a second evaluator. No Typer/Click dependency is added.

## Consequences

- Exit codes and help text are first-class tested contracts.
- CLI and HTTP stay in parity because both call application services.
- We hand-write help/parsing behavior; tests must cover unknown commands, missing arguments, and interruptions.
- A future richer CLI framework would be a new ADR, not a silent swap.

## Alternatives considered

- Typer/Click: rejected — extra dependency and different error semantics for little V1 gain.
- API-first with the CLI as a client: rejected — offline/CI use must not require a running service.
- Notebook authority: rejected — not reproducible or gateable.

## Compliance

`src/eval_harness/cli.py` uses only `argparse`; tests assert help/version, unknown-command, and exit-code mapping; `api.py` imports the same application services with no duplicated scoring.
