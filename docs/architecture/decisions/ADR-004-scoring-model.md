# ADR-004 — Scoring model

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Phase 02 must decide how cases are scored. The PRD requires deterministic checks before any judge, hard invariants that judges cannot waive, and per-profile diagnostics that do not collapse into one opaque number. The evaluation strategy §3 fixes the metric formulas.

## Decision

Score with deterministic hard-invariant and profile evaluators first, driven by an explicit `Profile -> evaluators` registry. Every evaluator returns immutable `Finding` records with a stable failure code; no evaluator computes a composite score. Structured-output validation uses the `jsonschema` library (Draft 2020-12) confined to the structured evaluator; domain modules import neither `jsonschema` nor any provider. Judges, added in Phase 05, may only add semantic findings and may never override a deterministic failure.

## Consequences

- Failures stay attributable to a layer and a code, which the gate engine can order deterministically.
- A judge outage cannot change deterministic outcomes.
- An extra dependency (`jsonschema`) must be locked and kept inside one adapter-like evaluator.
- A composite "overall quality" number is deliberately not produced; the headline metric is case pass rate plus profile breakdowns.

## Alternatives considered

- One opaque composite score: rejected — hides layer-specific regressions.
- Judge-only evaluation: rejected — untrustworthy for safety/schema/tool invariants.
- Ad-hoc JSON parsing: rejected — does not implement the referenced Draft 2020-12 contract.

## Compliance

`tests/unit/test_metrics.py` matches hand calculations; hard-invariant tests assert that a failing invariant yields `FAIL`; `grep` of `domain/` shows no `jsonschema` import.
