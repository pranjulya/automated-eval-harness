# Implementation phases

**Status:** APPROVED_FOR_IMPLEMENTATION (2026-09-10); phases execute one at a time from Phase 00.

Each phase is a specification for one independently reviewable capability. Follow numeric order and do not combine phases to save time.

## Required phase workflow

1. Read `Implementation.md`, PRD, evaluation strategy, accepted ADRs, and the phase file.
2. Confirm dependencies are `COMPLETE` and state the exact planned files/tests.
3. Move only the current phase to `IN_PROGRESS`.
4. For every non-trivial rule: failing test → confirm failure → minimum implementation → confirm pass.
5. Run the phase suite, full regression suite, lint, and type checks named in the phase.
6. Review the diff against architecture/security/privacy invariants.
7. Update the paired docs/Learning material and record verification evidence.
8. Move status through `IMPLEMENTED`, `TESTED`, `REVIEWED`, then `COMPLETE` only when its DoD holds.

## Phase index

| Phase | File | Focus |
|---:|---|---|
| 00 | `phase-00-foundation.md` | package, strict config, CLI shell, tooling |
| 01 | `phase-01-golden-dataset.md` | case schemas, immutable suite, exactly 50 goldens |
| 02 | `phase-02-deterministic-evaluators.md` | hard invariants and profile metrics |
| 03 | `phase-03-target-adapters.md` | fake/HTTP targets, normalized outcomes, retries |
| 04 | `phase-04-runner-artifacts.md` | orchestration, atomic bundles, replay, reports |
| 05 | `phase-05-judge-calibration.md` | semantic rubrics, judge adapter, calibration |
| 06 | `phase-06-baselines-regression.md` | promotion, thresholds, paired statistics |
| 07 | `phase-07-ci-quality-gates.md` | deploy blocking, trusted baselines, waivers |
| 08 | `phase-08-api-observability-security.md` | service surface, telemetry, privacy, online samples |
| 09 | `phase-09-extension-profiles.md` | structured-output, RAG, tool-use E2E proof |
| 10 | `phase-10-production-release-learning.md` | drills, packaging, docs, learning, final review |

## Shared completion rule

No phase is complete on generated code alone. Tests, exact verification output, diff review, documentation, Learning content, and accurate status are required.
