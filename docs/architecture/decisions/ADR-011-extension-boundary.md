# ADR-011 — Extension boundary

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

The harness must support structured-output, RAG, and tool-use evaluation, and future profiles, without forking the run lifecycle. PRD FR-20 and HLD §7 require profile-specific data to extend typed points, not replace orchestration.

## Decision

A profile extends exactly three typed points: the discriminated case expectation, the normalized target evidence it consumes, and the evaluator it registers. It reuses one dataset loader, runner, artifact format, aggregation, gate engine, and report. Adding a profile means: a new `Literal` expectation model, an evaluator implementing `evaluate(case, outcome) -> tuple[Finding, ...]`, a registry entry, fixtures, a report projection, and compatibility tests. There is no dynamic plugin loader or per-profile runner in V1.

## Consequences

- Profile diagnostics appear inside the existing `CaseResult`/report; there is no second bundle format.
- A profile cannot change persistence, comparison, or gating semantics.
- Compile-time/test-time extension is deliberate; a plugin marketplace is a PRD non-goal.

## Alternatives considered

- Dynamic plugin marketplace: rejected — untrusted code execution and version sprawl.
- Per-profile runners: rejected — duplicated lifecycle and divergence risk.

## Compliance

`tests/e2e/test_extension_profiles.py` runs all 32 complex-profile goldens through the shared runner; `docs/architecture/extension-profiles.md` gives the worked authoring recipe; the report's profile-diagnostics section is tested.
