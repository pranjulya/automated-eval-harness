# ADR-013 — V1 scope: deterministic core accepted, deployment enablement deferred

**Status:** ACCEPTED  
**Date:** 2026-09-10  
**Owner:** Project owner (user decision recorded 2026-09-10)  
**Supersedes:** none

## Context

Three phases cannot reach their Definition of Done without inputs only the owner can supply:
Phase 05 needs human judge-calibration labels and an approved paid provider; Phase 07 needs
repository branch protection, required reviewers, and trusted-store credentials; Phase 08 needs
a real identity provider, object store, and retention/consent policy.

Their code is complete and fail-closed, and the offline deterministic core (dataset, evaluators,
adapters, runner, bundles, replay, gate engine, baselines, extension profiles, API/telemetry
code, and drills) is finished and verified. The owner chose to accept that core as **V1** and
defer the deployment-enablement work to a post-V1 milestone rather than block the release.

## Decision

V1 ships the **offline deterministic evaluation core**. The following are moved to a post-V1
milestone ("deployment enablement") and are **not** deleted:

- **Phase 05** — semantic judge gating (rubrics, calibration math, judge adapters, fail-closed
  handling remain shipped; only the human-calibrated gating authority is deferred).
- **Phase 07** — repository protections, protected environments, and CI trusted-store credentials
  (attestation verifier, waiver engine, and release/promotion workflows remain shipped and
  fail-closed).
- **Phase 08** — real OIDC issuer/JWKS, production object store, retention/consent values, and
  dashboards (thin API, roles, bounded telemetry, online quarantine, and local object store
  remain shipped).

Phases 00–04, 06, 09, and 10 are `COMPLETE`, with Phase 10 accepted by the owner. Phases 05, 07,
and 08 are marked **`DEFERRED_POST_V1`**. This is a deliberate, user-approved extension of the
phase-status vocabulary; the standard `NOT_STARTED → … → COMPLETE` sequence still applies to
work that is not deferred.

Because V1 does not gate on calibrated semantic scores, the harness reports `REVIEW_REQUIRED`
for any case that requires a semantic dimension, and CI cannot deploy without a trusted baseline.
Both behaviours are intentional and fail-closed.

## Consequences

- V1 is a reproducible, provider-neutral deterministic evaluation harness; semantic gating and
  hardened deployment are explicitly out of V1 scope.
- No code is removed; enabling the deferred phases later is configuration and evidence work, not
  a rewrite.
- PRD §13, the roadmap, phase statuses, the architecture review, and the release-evidence index
  must all state the same scope (this ADR is the source of truth).

## Alternatives considered

- Block V1 until all external inputs exist: rejected — the deterministic core is independently
  useful and fully verified.
- Mark the blocked phases `COMPLETE`: rejected — dishonest; their DoD is unmet.
- Delete the deferred code: rejected — it is finished and fail-closed.

## Compliance

Phase statuses agree across `Implementation.md`, `implementation/phase-*.md`, the architecture
review, and `docs/operations/release-evidence.md`; the release evidence records V1-core
acceptance and the deferred items.
