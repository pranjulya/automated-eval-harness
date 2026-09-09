# Phase 07 — CI Quality Gates and Waivers

**Status:** NOT_STARTED

## Goal

Make the 50-case comparison a tamper-resistant deployment prerequisite, publish evidence for every outcome, and support narrow expiring non-hard waivers.

## Prerequisites and decisions

Phase 06 `COMPLETE`; ADR-008 accepted; base-branch/trusted artifact credentials, release budget, branch protections, and deployment job identified.

## References and concepts

Read evaluation strategy §11, HLD security boundaries, PRD FR-21/22. Learn trusted computing base, artifact provenance, base-versus-head attacks, protected environments, least privilege, CI dependency graphs, rerun semantics, waivers, and fail-closed release automation.

## Files

- Modify `.github/workflows/ci.yml`; create `.github/workflows/eval-release.yml` and documented reusable workflow if needed.
- Create `src/eval_harness/domain/waivers.py`, `application/waivers.py`, waiver schemas/storage.
- Create CI policy tests/scripts using package entry points, waiver unit/integration tests, and fixture workflow checks.
- Modify reports/docs, `docs/operations/failure-triage.md`, and `Learning/concepts/08-ci-gates.md`.

## Interfaces produced

- Verified `GateAttestation` binding commit, run hash, baseline hash, workflow identity, decision, timestamp, and reasons.
- `validate_waiver(waiver, comparison, now) -> WaiverDecision`.
- Release workflow whose deploy job requires a matching `PASS` attestation; unresolved `BLOCK`/`REVIEW_REQUIRED` prevents it.

## Tasks

- [ ] Test the workflow dependency and attestation verifier with pass, block, review, stale/wrong commit, wrong run hash, and missing artifact fixtures.
- [ ] Resolve baseline only from the protected base branch/trusted store and prove candidate changes cannot replace it.
- [ ] Run deterministic/unit/contract tests on every PR; run complete approved 50-case configuration on release-capable changes with explicit secrets/budget.
- [ ] Upload complete safe artifacts on pass/block/review/failure with retention and checksum verification.
- [ ] Implement waiver schema requiring owner, GitHub approver identity, exact scope/reasons, compensating control, and expiry `<=14 days`. V1 approval evidence is a protected GitHub review (required reviewers / CODEOWNERS on the waiver path), not an application cryptographic signature.
- [ ] Reject expired, mismatched, overbroad, missing GitHub approval evidence, or hard-invariant waivers; display accepted waivers in reports/attestations.
- [ ] Add protected promotion workflow separate from candidate execution credentials.
- [ ] Document rerun, flaky-provider, budget-exhaustion, artifact-retention, and emergency release procedures.

## Tests and failure scenarios

Candidate edits baseline/workflow, fork PR lacks secrets, replay artifact reused for wrong commit, job skipped, artifact upload fails, provider budget exhausted, rerun differs, waiver expires mid-run, wildcard case scope, hard failure waiver, waiver without protected GitHub approval, and deploy manually invoked without attestation.

## Verification

Run local workflow policy tests and exercise CI fixture branches for pass/block/review. Expected: only exact current-commit `PASS` attestation makes deploy eligible; other states preserve evidence and stop deployment. Verify candidate credentials cannot update baselines.

## Acceptance criteria and Definition of Done

Release depends on verified evaluation evidence, baseline trust is candidate-independent, all non-pass paths stop deploy, artifacts survive safely, waivers are narrow/visible/expiring/non-hard only, promotion uses separate authority, drills and docs/Learning/review complete, and phase reaches `COMPLETE`.
