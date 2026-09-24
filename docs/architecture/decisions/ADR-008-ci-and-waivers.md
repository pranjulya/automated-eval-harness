# ADR-008 — CI and waivers

**Status:** ACCEPTED (release wiring gated on deployment credentials/protections)  
**Date:** 2026-09-10  
**Owner:** Project owner (user approval recorded 2026-09-10)  
**Supersedes:** none

## Context

Phase 07 must make the 50-case comparison a tamper-resistant prerequisite for deployment, keep baseline trust independent of candidate code, and allow only narrow, expiring, non-hard waivers. Evaluation strategy §11 and PRD FR-21/22 fix the rules. No identity provider exists until Phase 08, so V1 approval evidence is a protected GitHub review.

## Decision

- CI returns stable exit codes; the deploy job depends on an exact current-commit `PASS` and a verified `GateAttestation` binding commit, run-manifest hash, baseline hash, workflow identity, decision, reasons, and timestamp.
- Baselines resolve only from a protected base branch or a configured trusted store, never from candidate-controlled content. Promotion runs in a separate workflow with separate authority.
- Waivers require owner, GitHub approver identity and approval evidence, exact reason/case/config scope, a compensating control, and expiry ≤ 14 days; wildcard scope and hard-invariant waivers are rejected. V1 does not require application cryptographic signatures (Phase 08 IdP).
- Artifacts upload on all decisions with retention and checksum verification.
- Defaults pending deployment choices: trusted baseline store = base-branch artifact/object store; attestation TTL = 24 h; release target/config = `evaluation/configs/fake.json` until a real approved target is configured.

## Consequences

- A candidate cannot approve, waive, or overwrite its own baseline.
- Uncertainty (`REVIEW_REQUIRED`) and failure (`BLOCK`) both stop deploy.
- Without branch protection / required reviewers configured, protection is advisory; enabling it is the remaining deployment gate.

## Alternatives considered

- Candidate-owned baseline: rejected — circular trust.
- Permanent ignore list: rejected — hides drift.
- App signatures before an IdP exists: rejected — over-engineering with no identity provider.

## Compliance

`tests/unit/test_waivers.py` and `tests/unit/test_attestations.py` cover acceptance/rejection; `tests/integration/test_release_gate.py` proves non-pass stops deploy; a structural test asserts the release workflow's deploy job depends on the gate result.
