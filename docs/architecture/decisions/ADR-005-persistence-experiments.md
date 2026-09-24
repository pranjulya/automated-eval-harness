# ADR-005 — Persistence and experiments

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Phase 04 must persist a complete, tamper-evident run and reproduce scoring without calling the target. The PRD forbids a mandatory database or hosted tracker in V1; the HLD §4 fixes an atomic staging/finalize lifecycle.

## Decision

Persist each run as an immutable filesystem bundle: a random staging directory is written, hashed, and atomically renamed to `<run-id>`; `COMPLETE` is written last and contains the index hash. Readers reject bundles without a valid marker. The run is the experiment record; there is no SQL catalog, queue, or hosted tracker in V1. An object-store adapter (Phase 08) implements the same "content-addressed objects, manifest last" contract.

## Consequences

- Local and CI execution need no external service; bundles are portable and auditable.
- Cross-run querying is limited until a catalog is justified by measured need.
- Interrupted writes never appear complete, so they cannot be compared or promoted.
- Replay can recompute scoring from stored normalized outcomes with no provider call.

## Alternatives considered

- PostgreSQL/MLflow from day one: rejected — infrastructure before measured need.
- Mutable single JSON file: rejected — no atomicity or tamper evidence.
- Database-only results: rejected — breaks offline and CI portability.

## Compliance

`tests/integration/test_runner_artifacts.py` interrupts at file boundaries, asserts an existing run ID fails, corrupts files, and verifies replay reproduces the summary hash.
