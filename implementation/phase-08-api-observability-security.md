# Phase 08 — API, Observability, Security/Privacy, and Online Signals

**Status:** NOT_STARTED

## Goal

Expose the existing services through a thin authenticated HTTP API, operate them with safe telemetry, support object-store artifacts, and ingest only consented/redacted online samples into quarantine.

## Prerequisites and decisions

Phase 07 `COMPLETE`; ADR-009/010 accepted; deployment identity provider, object store, retention classes, sampling/consent policy, redaction rules, and approved platform job runner selected.

## References and concepts

Read PRD §§8–10, HLD §§6/9/10, LLD §§12–15, failure playbook. Learn thin APIs, authentication/authorization, idempotency, telemetry cardinality, trace correlation, redaction versus encryption, consent/retention/deletion, quarantine, drift, and least-privilege object storage.

## Files

- Create `src/eval_harness/api.py`, API route/auth/error modules, `observability.py`.
- Create object-store artifact adapter and online sample/redaction/quarantine services.
- Create API unit/contract tests, auth/tenant/access tests, filesystem/object-store parity tests, telemetry/redaction tests, and online sample lifecycle tests.
- Create service container/deployment example and runbook; modify docs and `Learning/concepts/09-online-evals-and-privacy.md`.

## Interfaces produced

- LLD HTTP endpoints and common error envelope.
- Idempotent `RunRequest` application call shared by CLI/API.
- Filesystem/object-store repository contract parity.
- `OnlineSampleCandidate` with consent, classification, redaction, retention, deletion, quarantine, and human-review state.

## Tasks

- [ ] Write route tests proving pure translation and identical application results with CLI for run/read/compare/baseline operations.
- [ ] Implement OIDC/JWT validation and server-derived actor/role; protect raw artifacts, promotions, waivers, and quarantined samples separately.
- [ ] Add object-store contract tests for immutable objects, manifest-last publication, integrity/versioning, denial, timeout, and retention metadata.
- [ ] Implement object-store adapter and readiness without making telemetry/storage outages corrupt evaluation decisions.
- [ ] Define bounded structured logs/metrics/traces and test absence of secrets/raw prompts/high-cardinality metric labels.
- [ ] Implement opt-in sampling, pre-persistence redaction, quarantine, reviewer workflow, retention expiry, and deletion evidence.
- [ ] Ensure online signals can alert and propose a draft sanitized case but cannot publish datasets, rubrics, thresholds, or baselines.
- [ ] Add dashboards/alerts for non-pass rates, failure classes, target/judge errors, latency/cost, integrity failure, baseline age, waiver use, and quarantine backlog.
- [ ] Run threat-model/failure tests and document incident/recovery procedures.

## Tests and failure scenarios

Forged/expired token, cross-role/tenant access, duplicate API idempotency key, object-store outage/corruption, log injection, huge payload, prompt injection, secret/PII in every field, redaction failure, retention/deletion race, telemetry collector outage, high-cardinality input, and online sample attempting auto-promotion.

## Verification

Run API/security/privacy/object-store/telemetry suites plus all earlier tests. Exercise local authenticated API flows and synthetic online samples. Expected: CLI/API parity, denied unauthorized mutation/read, no sensitive telemetry, valid lifecycle/deletion, and no online-to-golden automatic path.

## Acceptance criteria and Definition of Done

API stays thin, service storage preserves artifact semantics, auth and roles protect sensitive/mutating actions, telemetry is actionable/safe, online collection is opt-in/redacted/quarantined/retention-bounded, threat/failure tests and runbooks pass, docs/Learning/review complete, and phase reaches `COMPLETE`.
