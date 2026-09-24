# ADR-001 — Runtime and packaging

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

The harness must run reproducibly on developer machines, in CI, and in a clean container without a cloud dependency. Phase 00 needs a packaging and runtime baseline before any evaluation behavior exists. `docs/architecture/LLD.md` §1 fixes the package boundaries; `Implementation.md` fixes the tech stack.

## Decision

Use Python 3.12+ with a `src/`-layout package `eval_harness`, Pydantic v2 for strict stored/config contracts, and pytest, Ruff, mypy, and `python -m build` for quality and packaging. Direct dependencies are limited to what a phase justifies: Phase 00 adds only Pydantic and the test/lint/type tooling; `jsonschema` is added in Phase 02 and FastAPI/HTTPX in their owning phases. Exact patch versions are locked at Phase 00 implementation time.

## Consequences

- One language and one lockfile keep local, CI, and container execution identical.
- Strict Pydantic models with `extra="forbid"` make untrusted-input rejection explicit.
- Python 3.12 is required; the repository must not silently fall back to older interpreters.
- Adding a new direct dependency requires a phase justification and a lockfile update.

## Alternatives considered

- Polyglot runtime (TypeScript CLI plus Python core): rejected — doubles tooling and provenance.
- Framework-heavy scaffold (Django/FastAPI-only project): rejected — Phase 00 must stay a thin foundation.
- `dataclasses`/`attrs` instead of Pydantic: rejected for stored contracts — need strict parsing, JSON Schema export, and version errors.

## Compliance

`pyproject.toml` declares `requires-python = ">=3.12"`; mypy runs strict on `src/eval_harness`; only Phase-approved direct dependencies appear; a clean wheel install passes the Phase 00 tests.
